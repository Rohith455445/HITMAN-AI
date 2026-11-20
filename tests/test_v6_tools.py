"""Security boundaries and feature tests for the v6 public Gemini workflow."""
import base64
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from public_tools import create_guest_project_archive, guest_attachment


class FakeProvider:
    calls = []
    def __init__(self, **kwargs):
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get('stream'):
            return iter([SimpleNamespace(type='response.output_text.delta', delta='File understood')])
        return SimpleNamespace(output_text=json.dumps({
            'name': 'Starter', 'summary': 'Test', 'setup': 'python app.py',
            'files': [{'path': 'app.py', 'content': "print('hello')\n"},
                      {'path': 'README.md', 'content': 'Run app.py'}]
        }))


def test_guest_attachment_text_and_images():
    value = base64.b64encode(b'print(1+1)\n').decode()
    attachment = guest_attachment('sample.py', value)
    assert attachment[0]['type'] == 'input_text'
    assert 'print(1+1)' in attachment[0]['text']
    png = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'abc').decode()
    image = guest_attachment('photo.png', png)
    assert image[0]['type'] == 'input_image'
    with pytest.raises(HTTPException):
        guest_attachment('photo.jpg', png)
    with pytest.raises(HTTPException):
        guest_attachment('secrets.exe', base64.b64encode(b'bad').decode())
    with pytest.raises(HTTPException):
        guest_attachment('big.md', base64.b64encode(b'a'*1_200_001).decode())
    with pytest.raises(HTTPException):
        guest_attachment('file.txt', '@@@notbase64@@@')


def test_pdf_text_extraction_and_pdf_page_limit():
    from pypdf import PdfWriter
    output = io.BytesIO()
    writer = PdfWriter()
    for _ in range(13): writer.add_blank_page(width=100, height=100)
    writer.write(output)
    value = base64.b64encode(output.getvalue()).decode()
    with pytest.raises(HTTPException) as info:
        guest_attachment('document.pdf', value)
    assert info.value.status_code == 413


def test_guest_ai_receives_one_time_attachment_and_notes(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy-for-test')
    monkeypatch.setattr(main, 'OpenAI', FakeProvider)
    FakeProvider.calls = []
    with TestClient(main.app) as client:
        r = client.post('/api/public/chat', json={
            'message':'Describe this file', 'mode':'code',
            'attachment_name':'example.py',
            'attachment_data':base64.b64encode(b'print(2)').decode(),
            'memory_notes':['I prefer concise explanations'],
        })
        assert r.status_code == 200
        assert 'File understood' in r.text
        call = FakeProvider.calls[-1]
        assert len(call['input']) == 2
        assert call['input'][-1]['content'][1]['type'] == 'input_text'
        assert call['store'] is False
        assert client.post('/api/public/chat', json={
            'message':'hello', 'memory_notes':['A'*351]
        }).status_code == 413


def test_zip_generator_safety():
    good = {'files':[{'path':'main.py', 'content':'print(123)\n'}]}
    zipped, metadata = create_guest_project_archive(good, main.valid_project_path)
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        assert archive.namelist() == ['main.py','README.md','HITMAN_VALIDATION.txt']
        assert 'PASS Python syntax' in archive.read('HITMAN_VALIDATION.txt').decode()
    for path in ('../escape.py', '/etc/passwd', '.env', 'bad\\name.py'):
        with pytest.raises(ValueError):
            create_guest_project_archive({'files':[{'path':path,'content':'secret'}]},main.valid_project_path)


def test_project_builder_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    monkeypatch.setattr(main, 'PUBLIC_PROJECTS', False)
    with TestClient(main.app) as client:
        assert client.post('/api/public/project',json={'description':'Build a small calculator app'}).status_code == 403
        assert client.get('/api/config').json()['features']['multi_file_project_generator'] is False
    monkeypatch.setattr(main, 'PUBLIC_PROJECTS', True)
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy-for-test')
    monkeypatch.setattr(main, 'OpenAI', FakeProvider)
    with TestClient(main.app) as client:
        result = client.post('/api/public/project', json={'description':'Build a small calculator app'})
        assert result.status_code == 200
        assert result.headers['content-type'] == 'application/zip'
        with zipfile.ZipFile(io.BytesIO(result.content)) as archive:
            assert 'app.py' in archive.namelist()
        assert client.get('/api/config').json()['features']['multi_file_project_generator'] is True
        # Still cannot open the private account and workspace APIs.
        assert client.get('/api/conversations').status_code == 403
        assert client.get('/workspace', follow_redirects=False).status_code == 303


def test_frontend_ids_referenced_in_javascript_exist():
    from pathlib import Path
    import re
    static = Path(main.__file__).parent/'static'
    html = (static/'index.html').read_text('utf-8')
    js = (static/'app.js').read_text('utf-8')
    ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    selectors = set(re.findall(r"\$\('#([\w-]+)'\)", js))
    assert not (selectors - ids), f'Missing UI elements: {selectors - ids}'
