"""HITMAN AI Gemini provider adapter.

Provides the narrow responses.create and images methods used by HITMAN AI v4,
using Google's native Gemini Developer API via httpx. Not an OpenAI proxy and
not a claim of feature equivalence. API keys remain server-side.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import httpx

API_ROOT = 'https://generativelanguage.googleapis.com/v1beta'


class GeminiAPIError(RuntimeError):
    """A sanitized provider failure that never includes the API key."""


def _provider_error(response: httpx.Response) -> GeminiAPIError:
    try:
        error = response.json().get('error', {})
        detail = str(error.get('message') or '')[:350]
        code = error.get('status') or f'HTTP {response.status_code}'
    except (ValueError, TypeError, AttributeError):
        code, detail = f'HTTP {response.status_code}', ''
    # Do not log echoed credentials or full URLs from error text.
    detail = re.sub(r'AIza[\w-]{15,}', '[redacted]', detail)
    detail = re.sub(r'sk-[\w-]{12,}', '[redacted]', detail)
    detail = detail.replace('x-goog-api-key', '[credential-header]')
    return GeminiAPIError(f'{code}: {detail or "Gemini request failed"}')


def _get_text(doc: dict) -> str:
    chunks = []
    for candidate in doc.get('candidates') or []:
        for part in (candidate.get('content') or {}).get('parts') or []:
            if isinstance(part.get('text'), str):
                chunks.append(part['text'])
        if chunks:
            break
    return ''.join(chunks)


def _get_grounding_links(doc: dict) -> list[str]:
    result = []
    for candidate in doc.get('candidates') or []:
        metadata = candidate.get('groundingMetadata') or {}
        for chunk in metadata.get('groundingChunks') or []:
            uri = (chunk.get('web') or {}).get('uri')
            if uri and uri.startswith('https://') and uri not in result:
                result.append(uri)
    return result[:5]


def _messages(input_data) -> list[dict]:
    if isinstance(input_data, str):
        return [{'role': 'user', 'parts': [{'text': input_data}]}]
    if not isinstance(input_data, list):
        raise ValueError('Invalid chat input')
    contents = []
    for message in input_data:
        role = 'model' if message.get('role') in {'assistant','model'} else 'user'
        source = message.get('content', '')
        parts = []
        if isinstance(source, str):
            parts.append({'text': source})
        elif isinstance(source, list):
            for entry in source:
                if entry.get('type') in {'text','input_text'}:
                    parts.append({'text': entry.get('text','')})
                elif entry.get('type') == 'input_image':
                    value = entry.get('image_url','')
                    match = re.fullmatch(r'data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)', value)
                    if not match:
                        raise ValueError('Only embedded PNG/JPEG/WEBP image attachments are supported')
                    parts.append({'inlineData': {'mimeType': match.group(1), 'data': match.group(2)}})
        if not parts:
            parts.append({'text':' '})
        # Consecutive same-role turns are valid Gemini input; retain full conversation order.
        contents.append({'role': role, 'parts': parts})
    return contents


def _payload(*, model, instructions=None, input=None, max_output_tokens=None, text=None,
             tools=None, reasoning=None, **ignored) -> dict:
    generation = {}
    if max_output_tokens:
        generation['maxOutputTokens'] = max(1, min(int(max_output_tokens), int(os.getenv('GEMINI_OUTPUT_LIMIT','16000'))))
    if text and text.get('format', {}).get('type') == 'json_object':
        generation['responseMimeType'] = 'application/json'
    if reasoning and os.getenv('GEMINI_THINKING_LEVEL','').strip():
        generation['thinkingConfig'] = {'thinkingLevel':os.environ['GEMINI_THINKING_LEVEL'].strip()}
    body = {'contents': _messages(input)}
    if instructions:
        body['systemInstruction'] = {'parts': [{'text': instructions}]}
    if generation:
        body['generationConfig'] = generation
    tools_out = []
    for tool in tools or []:
        kind = tool.get('type','')
        if kind == 'web_search':
            if os.getenv('GEMINI_ENABLE_SEARCH','0') != '1':
                raise GeminiAPIError('Web grounding is disabled for the free-tier configuration. Set GEMINI_ENABLE_SEARCH=1 only when your model and quota support it.')
            tools_out.append({'googleSearch':{}})
        elif kind == 'code_interpreter':
            if os.getenv('GEMINI_ENABLE_CODE_EXECUTION','0') != '1':
                raise GeminiAPIError('Gemini code execution is disabled. Set GEMINI_ENABLE_CODE_EXECUTION=1 if your model supports it.')
            tools_out.append({'codeExecution':{}})
        else:
            raise ValueError(f'Unsupported tool type: {kind}')
    if tools_out:
        body['tools'] = tools_out
    return body


class _GeminiResponses:
    def __init__(self, client: 'GeminiClient'):
        self.client = client

    def create(self, *, model, instructions=None, input=None, max_output_tokens=None,
               text=None, tools=None, stream=False, reasoning=None, **kwargs):
        body = _payload(model=model, instructions=instructions, input=input,
                        max_output_tokens=max_output_tokens, text=text, tools=tools, reasoning=reasoning)
        if stream:
            return self._stream(model, body)
        response = self.client.request(model, 'generateContent', body)
        output = _get_text(response)
        if not output:
            raise GeminiAPIError('Gemini returned no text. The request may have been blocked or reached its output limit.')
        if tools and tools[0].get('type') == 'web_search':
            urls = _get_grounding_links(response)
            if urls:
                output += '\n\nSources:\n' + '\n'.join('- ' + url for url in urls)
        return SimpleNamespace(status='completed', output_text=output)

    def _stream(self, model, body):
        path = self.client.model_path(model, 'streamGenerateContent') + '?alt=sse'
        seen_sources = []
        with httpx.Client(timeout=self.client.timeout) as requester:
            with requester.stream('POST', API_ROOT+path, headers=self.client.headers, json=body) as response:
                if response.status_code >= 400:
                    response.read()
                    raise _provider_error(response)
                for line in response.iter_lines():
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if not data or data == '[DONE]':
                        continue
                    try:
                        packet = json.loads(data)
                    except ValueError:
                        continue
                    if packet.get('error'):
                        raise GeminiAPIError('Gemini streaming request failed')
                    delta = _get_text(packet)
                    if delta:
                        yield SimpleNamespace(type='response.output_text.delta',delta=delta)
                    for url in _get_grounding_links(packet):
                        if url not in seen_sources: seen_sources.append(url)
        if seen_sources:
            yield SimpleNamespace(type='response.output_text.delta',delta='\n\nSources:\n'+'\n'.join('- '+url for url in seen_sources))


class _GeminiImages:
    def __init__(self, client: 'GeminiClient'):
        self.client = client

    def generate(self, *, model, prompt):
        return self._create(model, prompt, None)

    def edit(self, *, model, prompt, image):
        blob=image.read()
        name=getattr(image,'name','input.png')
        mime=mimetypes.guess_type(name)[0] or 'image/png'
        if mime not in {'image/png','image/jpeg','image/webp'}:
            raise ValueError('Only PNG, JPEG and WEBP inputs are allowed')
        return self._create(model, prompt, {'inlineData': {'mimeType':mime,'data':base64.b64encode(blob).decode()}})

    def _create(self, model, prompt, attachment):
        if os.getenv('GEMINI_ENABLE_IMAGES','0') != '1':
            raise GeminiAPIError('Image generation is disabled for this free-tier build. Gemini image-model access may require billing. Set GEMINI_ENABLE_IMAGES=1 only if your API account supports the selected image model.')
        parts=[{'text':prompt}]
        if attachment: parts.append(attachment)
        body={'contents':[{'role':'user','parts':parts}], 'generationConfig':{'responseModalities':['TEXT','IMAGE']}}
        result=self.client.request(model,'generateContent',body)
        for candidate in result.get('candidates',[]):
            for part in (candidate.get('content') or {}).get('parts') or []:
                inline=part.get('inlineData') or {}
                if inline.get('data') and inline.get('mimeType','').startswith('image/'):
                    return SimpleNamespace(data=[SimpleNamespace(b64_json=inline['data'])])
        raise GeminiAPIError('Image model did not return an image')


class GeminiClient:
    """Compatibility surface for HITMAN AI's existing text-oriented endpoints."""
    def __init__(self, api_key=None, timeout=180.0, **kwargs):
        self.key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.key:
            raise GeminiAPIError('GEMINI_API_KEY is missing from .env')
        self.timeout = float(timeout)
        self.headers = {'x-goog-api-key':self.key, 'Content-Type':'application/json'}
        self.responses = _GeminiResponses(self)
        self.images = _GeminiImages(self)

    @staticmethod
    def model_path(model, action):
        if not re.fullmatch(r'[a-zA-Z0-9._-]{2,90}',model):
            raise ValueError('Invalid Gemini model identifier')
        return f'/models/{quote(model)}:{action}'

    def request(self, model, action, payload):
        with httpx.Client(timeout=self.timeout) as client:
            response=client.post(API_ROOT+self.model_path(model, action),headers=self.headers,json=payload)
            if response.status_code>=400:
                raise _provider_error(response)
            result=response.json()
            if not isinstance(result,dict):
                raise GeminiAPIError('Malformed Gemini API response')
            return result
