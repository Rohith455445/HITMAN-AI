"""Regression tests for broken current-info and attachment experiences in v10."""
import base64
import io
import zipfile
from types import SimpleNamespace

from fastapi.testclient import TestClient
from pypdf import PdfWriter
import main
from current_intent import needs_fresh_search
from gemini_bridge import _messages
from public_tools import guest_attachment


class RecordedModel:
    calls = []
    def __init__(self, **kwargs):
        self.responses = self
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter([SimpleNamespace(type='response.output_text.delta', delta='Grounded response')])


def test_cricket_news_followups_are_detected():
    assert needs_fresh_search('today cricket updates')
    assert needs_fresh_search('give updates', [{'role':'user','content':'today cricket updates'}])
    assert not needs_fresh_search('write a Python linked list program')
    assert not needs_fresh_search('give updates', [{'role':'user','content':'sorting algorithms'}])


def test_guest_standard_chat_automatically_grounds_current_queries(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    monkeypatch.setattr(main, 'PUBLIC_SEARCH', True)
    monkeypatch.setattr(main, 'AUTO_WEB_SEARCH', True)
    monkeypatch.setattr(main, 'TEXT_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-only')
    monkeypatch.setattr(main, 'OpenAI', RecordedModel)
    RecordedModel.calls = []
    with TestClient(main.app) as client:
        response = client.post('/api/public/chat', json={'message':'today cricket updates'})
        assert response.status_code == 200
        assert 'Searching current sources' in response.text
        assert RecordedModel.calls[-1]['tools'] == [{'type':'web_search'}]
        response = client.post('/api/public/chat', json={
            'message':'give updates', 'history':[{'role':'user','content':'today cricket updates'}]
        })
        assert response.status_code == 200
        assert RecordedModel.calls[-1]['tools'] == [{'type':'web_search'}]
        response = client.post('/api/public/chat', json={'message':'Explain Python classes'})
        assert response.status_code == 200
        assert 'tools' not in RecordedModel.calls[-1]
        config = client.get('/api/config').json()
        assert config['features']['auto_web_search'] is True


def test_no_automatic_grounding_when_disabled(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    monkeypatch.setattr(main, 'PUBLIC_SEARCH', True)
    monkeypatch.setattr(main, 'AUTO_WEB_SEARCH', False)
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-only')
    monkeypatch.setattr(main, 'OpenAI', RecordedModel)
    RecordedModel.calls = []
    with TestClient(main.app) as client:
        response = client.post('/api/public/chat', json={'message':'today cricket updates'})
        assert response.status_code == 200
        assert 'tools' not in RecordedModel.calls[-1]


def test_scanned_pdf_uses_native_gemini_inline_document(monkeypatch):
    writer=PdfWriter(); writer.add_blank_page(width=100, height=100)
    result=io.BytesIO();writer.write(result)
    blob=base64.b64encode(result.getvalue()).decode()
    files=guest_attachment('scanned.pdf', blob)
    assert files[0]['type'] == 'input_pdf'
    messages=_messages([{'role':'user','content':[{'type':'input_text','text':'What does this say?'},*files]}])
    inline=messages[0]['parts'][1]['inlineData']
    assert inline['mimeType'] == 'application/pdf' and inline['data'] == blob


def test_zip_attachment_is_static_context_not_executable():
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        z.writestr('app.py','print(5)\n')
    result=guest_attachment('app.zip',base64.b64encode(data.getvalue()).decode())
    assert result[0]['type'] == 'input_text'
    assert 'app.py' in result[0]['text'] and 'print(5)' in result[0]['text']


def test_local_larger_file_is_explicit_opt_in(monkeypatch):
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('HITMAN_LOCAL_ATTACHMENT_BYTES', '4000000')
    sample=base64.b64encode(b'a'*1_300_000).decode()
    assert guest_attachment('report.txt',sample)[0]['type'] == 'input_text'
    monkeypatch.setenv('APP_ENV','production')
    from fastapi import HTTPException
    try:
        guest_attachment('report.txt',sample)
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError('Render production cap was not enforced')


def test_js_accepts_attachment_only_and_zip():
    from pathlib import Path
    js=(Path(__file__).parents[1]/'static/app.js').read_text()
    assert "input.value.trim() || (selectedFile ?" in js
    assert '.webp,.zip' in js
    assert 'Searching current sources' in js


def test_large_local_zip_inspection_respects_boundaries(monkeypatch):
    import os
    from fastapi import HTTPException
    from public_tools import preview_zip_context
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('HITMAN_LOCAL_ZIP_BYTES', '2000000')
    stream=io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('README.md', '# About this application\n')
        archive.writestr('main.py', 'print("hello")\n')
        archive.writestr('assets/noise.bin', os.urandom(270_000))
    assert len(stream.getvalue()) > 250_000
    context=preview_zip_context(stream.getvalue())
    assert 'main.py' in context and 'README.md' in context
    assert 'noise.bin' not in context
    monkeypatch.setenv('APP_ENV', 'production')
    try:
        preview_zip_context(stream.getvalue())
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError('Large ZIP should be rejected on public hosting')


def test_zip_source_with_apikey_is_rejected():
    from fastapi import HTTPException
    from public_tools import preview_zip_context
    stream=io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('app.py', 'api_key = "AIza' + 'x'*30 + '"\n')
    try:
        preview_zip_context(stream.getvalue())
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError('Possible secrets should prevent ZIP upload')


def test_gemini_payload_uses_real_search_tool(monkeypatch):
    from gemini_bridge import _payload
    monkeypatch.setenv('GEMINI_ENABLE_SEARCH', '1')
    body=_payload(model='gemini-example', input='Today cricket updates',
                  tools=[{'type':'web_search'}])
    assert body['tools'] == [{'googleSearch':{}}]
    assert body['contents'][0]['parts'][0]['text'] == 'Today cricket updates'
