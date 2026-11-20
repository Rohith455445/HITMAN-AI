"""Offline v7 tool tests. Provider calls are mocked; no live API usage."""
import base64
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import main
from advanced_public import read_guest_zip, build_reviewed_patch, detect_image
from live_voice_v7 import allowed_origin


def compressed(files):
    target=io.BytesIO()
    with zipfile.ZipFile(target, 'w') as z:
        for name,value in files.items():
            z.writestr(name, value)
    return base64.b64encode(target.getvalue()).decode()


class MockGemini:
    calls=[]
    def __init__(self, **kwargs):
        self.responses=self
        self.images=self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get('text'):
            return SimpleNamespace(output_text=json.dumps({'summary':'fixed issue','changes':[
                {'path':'app.py','content':'print(3)\n'}]}))
        if kwargs.get('tools'):
            return SimpleNamespace(output_text='## Findings\n\nSupported answer.\n\nSources:\nhttps://example.org/study')
        return SimpleNamespace(output_text='1. Review evidence\n2. Compare sources\n3. Explain limitations')

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        data=base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'abc').decode()
        return SimpleNamespace(data=[SimpleNamespace(b64_json=data,mime_type='image/png')])

    def edit(self, **kwargs):
        return self.generate(**kwargs)


def test_zip_patch_is_reviewable_and_not_executed():
    orig={'app.py':'print(1)\n','README.md':'Project'}
    result={'summary':'changed expression','changes':[{'path':'app.py','content':'print(2)\n'}]}
    data,meta=build_reviewed_patch(orig,result)
    assert orig['app.py']=='print(1)\n'
    assert meta['changed']==['app.py']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.read('app.py') == b'print(2)\n'
        report=z.read('HITMAN_REVIEW_PATCH.txt').decode()
        assert 'UNEXECUTED' in report and 'before/app.py' in report
    for bad in ('new.py','../app.py','secrets.json'):
        with pytest.raises(ValueError):
            build_reviewed_patch(orig,{'changes':[{'path':bad,'content':'x'}]})


def test_zip_rejects_traversal_encryption_and_limits():
    assert read_guest_zip(compressed({'app.py':'print(1)'})) == {'app.py':'print(1)'}
    for filename in ('../evil.py','/tmp/x.py','C:/windows/file.py','.env','node_modules/index.js','image.jpg'):
        with pytest.raises(HTTPException): read_guest_zip(compressed({filename:'x'}))
    with pytest.raises(HTTPException): read_guest_zip(compressed({'app.py':'A'*25001}))


def test_public_tools_default_closed(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_IMAGE',False)
    monkeypatch.setattr(main,'PUBLIC_RESEARCH',False)
    monkeypatch.setattr(main,'PUBLIC_REPAIR',False)
    monkeypatch.setattr(main,'PUBLIC_LIVE_VOICE',False)
    with TestClient(main.app) as app:
        capabilities=app.get('/api/config').json()['features']
        assert not any(capabilities[k] for k in ('image_generation','image_editing','deep_research','zip_code_repair','realtime_voice'))
        assert app.post('/api/public/image',json={'prompt':'A blue bird'}).status_code==403
        assert app.post('/api/public/research',json={'question':'What are the best evidence sources?'}).status_code==403
        assert app.post('/api/public/repair',json={'instruction':'Fix syntax safely','archive_base64':compressed({'app.py':'print(1)'})}).status_code==403


def test_research_two_passes_and_grounding_flag(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_RESEARCH',True)
    monkeypatch.setenv('GEMINI_API_KEY','offline')
    monkeypatch.setattr(main,'OpenAI',MockGemini)
    MockGemini.calls=[]
    with TestClient(main.app) as app:
        response=app.post('/api/public/research',json={'question':'What current evidence supports the hypothesis?'})
        assert response.status_code == 200, response.text
        assert 'https://example.org/study' in response.json()['report']
        assert len(MockGemini.calls) == 2
        assert MockGemini.calls[-1]['tools'] == [{'type':'web_search'}]
        assert 'research' in app.get('/api/config').json()['modes']


def test_image_generation_and_editing_gated(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_IMAGE',True)
    monkeypatch.setenv('GEMINI_API_KEY','offline')
    monkeypatch.setattr(main,'OpenAI',MockGemini)
    with TestClient(main.app) as app:
        img=app.post('/api/public/image',json={'prompt':'A blue bird'});
        assert img.status_code==200 and img.content.startswith(b'\x89PNG')
        assert img.headers['content-type']=='image/png'
    with pytest.raises(HTTPException): detect_image(base64.b64encode(b'not a png').decode(),'image.png')


def test_repair_guest_only_returns_a_review_zip(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_REPAIR',True)
    monkeypatch.setenv('GEMINI_API_KEY','offline')
    monkeypatch.setattr(main,'OpenAI',MockGemini)
    with TestClient(main.app) as app:
        response=app.post('/api/public/repair',json={
            'instruction':'Fix the result of my calculation',
            'archive_name':'project.zip',
            'archive_base64':compressed({'app.py':'print(2)\n'})
        })
        assert response.status_code==200, response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            assert z.read('app.py')==b'print(3)\n'
            assert 'UNEXECUTED' in z.read('HITMAN_REVIEW_PATCH.txt').decode()
        assert app.get('/api/conversations').status_code == 403


def test_live_voice_websocket_origin_and_disabled(monkeypatch):
    assert allowed_origin('https://hitman-ai.onrender.com','https://hitman-ai.onrender.com')
    assert not allowed_origin('http://hitman-ai.onrender.com','https://hitman-ai.onrender.com')
    assert not allowed_origin('https://hitman-ai.onrender.com.evil.com','https://hitman-ai.onrender.com')
    assert not allowed_origin(None,'https://hitman-ai.onrender.com')
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_LIVE_VOICE',False)
    with TestClient(main.app) as app:
        with pytest.raises(WebSocketDisconnect):
            with app.websocket_connect('/api/public/live',headers={'origin':'http://testserver'}): pass


def test_openai_api_provider_not_bundled_with_subscriptions(monkeypatch):
    monkeypatch.setattr(main,'TEXT_PROVIDER','openai')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(HTTPException) as err: main.public_text_client()
    assert err.value.status_code == 503
    assert main.public_text_model('reason')
