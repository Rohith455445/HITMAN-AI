r"""HITMAN AI v12: safe, optional live Gemini API diagnostics.

Run in the HITMAN AI project directory with its existing .venv:
  .\.venv\Scripts\python.exe diagnose_hitman_gemini_v12.py
  .\.venv\Scripts\python.exe diagnose_hitman_gemini_v12.py --search

Each --search test is a separate Google Search grounding API request and may incur charges.
No API key is printed or placed in URL query parameters.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import httpx
    from dotenv import load_dotenv
except ImportError:
    print('Missing dependencies. Install requirements.txt in your existing virtual environment.')
    raise SystemExit(1)

BASE = 'https://generativelanguage.googleapis.com/v1beta'

def safe_message(response: httpx.Response) -> str:
    """Display only provider error class/status; never echo raw request or secrets."""
    try:
        body = response.json()
        error = body.get('error', {}) if isinstance(body, dict) else {}
        provider_status = str(error.get('status', 'UNKNOWN'))[:45]
        # Distinguish quota/model/tools with safe heuristics; don't print raw response.
        low = str(error.get('message', '')).lower()
        if 'quota' in low or 'resource exhausted' in low or 'rate limit' in low:
            reason = 'quota, rate limit, or billing restriction'
        elif ('google search' in low or 'grounding' in low or 'tool' in low or
              'not supported' in low or 'unsupported' in low):
            reason = 'tool/grounding unsupported or restricted'
        elif 'not found' in low or 'model' in low:
            reason = 'model not available for this key/API'
        elif 'api key' in low or 'permission' in low or 'authentication' in low:
            reason = 'API key or permission problem'
        else:
            reason = 'provider rejected the request (see status)'
        return f'HTTP {response.status_code}, {provider_status}: {reason}'
    except (ValueError, TypeError, AttributeError):
        return f'HTTP {response.status_code}: non-JSON response'


def check(client: httpx.Client, model: str, search: bool) -> bool:
    url = f'{BASE}/models/{model}:generateContent'
    body = {'contents': [{'role': 'user', 'parts': [
        {'text': 'Say OK only.' if not search else 'Find current news about international cricket today. Give one sourced headline.'}
    ]}], 'generationConfig': {'maxOutputTokens': 256}}
    if search:
        body['tools'] = [{'googleSearch': {}}]
    name = 'GOOGLE SEARCH GROUNDING' if search else 'PLAIN GEMINI CHAT'
    print(f'\n{name} [{model}]')
    try:
        response = client.post(url, json=body)
        if response.status_code >= 400:
            print('  FAIL:', safe_message(response))
            return False
        data = response.json()
        output = ''.join(
            part.get('text', '')
            for cand in data.get('candidates', [])
            for part in (cand.get('content', {}) or {}).get('parts', [])
            if isinstance(part, dict)
        )
        if output:
            print('  PASS: Gemini returned text. (Response text omitted.)')
            if search:
                grounded = any((c.get('groundingMetadata') or {}).get('groundingChunks')
                               for c in data.get('candidates', []))
                print('  Source metadata:', 'present' if grounded else 'NOT returned; cannot claim verified research')
            return True
        print('  NO TEXT: request was accepted, but no text was generated.')
        return False
    except httpx.RequestError as exc:
        print('  NETWORK FAIL:', type(exc).__name__)
        return False
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        print('  RESPONSE FAIL:', type(exc).__name__)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Check HITMAN AI Gemini access without exposing keys.')
    parser.add_argument('--search', action='store_true', help='also send one potentially billable Google Search grounding request')
    args = parser.parse_args()
    load_dotenv(Path.cwd() / '.env')
    key = os.getenv('GEMINI_API_KEY', '').strip()
    model = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite').strip()
    if not key or key.startswith('YOUR_') or key.startswith('replace_'):
        print('ERROR: GEMINI_API_KEY is not configured. Keep your key private.')
        return 1
    if not re.fullmatch(r'[A-Za-z0-9._-]{2,90}', model):
        print('ERROR: Invalid GEMINI_MODEL value in .env.')
        return 1
    print('HITMAN AI v12 — Gemini API live diagnostic')
    print('Configured model:', model)
    print('Google grounding switch:', os.getenv('GEMINI_ENABLE_SEARCH', '0'))
    print('No credentials or model-generated text will be printed.')
    with httpx.Client(headers={'x-goog-api-key': key, 'Content-Type': 'application/json'}, timeout=35) as client:
        try:
            response = client.get(f'{BASE}/models', params={'pageSize': 100})
            if response.status_code == 200:
                names = [m.get('name', '').removeprefix('models/')
                         for m in response.json().get('models', [])
                         if 'generateContent' in m.get('supportedGenerationMethods', [])]
                if names:
                    print('Models advertised for generateContent (up to 15):', ', '.join(names[:15]))
                    print('Configured model in returned page:', 'YES' if model in names else 'NO / not in first page')
                else:
                    print('List models returned no generateContent entries in the first page.')
            else:
                print('Model listing failed:', safe_message(response))
        except (httpx.RequestError, ValueError, TypeError, AttributeError) as exc:
            print('Model listing unavailable:', type(exc).__name__)
        plain_ok = check(client, model, False)
        search_ok = check(client, model, True) if args.search else None
    print('\nNEXT ACTION:')
    if not plain_ok:
        print('Basic Gemini generation failed. Check key, model, per-model quota, and AI Studio billing/rate limits before testing web search.')
    elif search_ok is False:
        print('Basic chat works, but Google Search grounding failed. Disable Gemini grounding and configure an authorized external search provider (e.g. Brave Search) or obtain supported paid grounding access.')
    elif search_ok is True:
        print('Both API calls worked. Restart Uvicorn, retry a new chat, then inspect frontend stream handling if needed.')
    else:
        print('Basic chat works. Run again with --search ONLY if your API plan permits potentially billable search requests.')
    return 0 if plain_ok else 2

if __name__ == '__main__':
    sys.exit(main())
