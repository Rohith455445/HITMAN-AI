"""Builder Studio regression tests. All model responses are mocked."""
import base64
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from studio_engine import (
    PROJECT_TYPES, make_build_prompt, parse_json_object,
    build_archive, safe_path, static_inspection,
)


def encode_zip(files):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as archive:
        for name,contents in files.items():archive.writestr(name,contents)
    return base64.b64encode(buf.getvalue()).decode()


class StudioMock:
    requests=[]
    def __init__(self, **kwargs):self.responses=self
    def create(self, **kwargs):
        self.requests.append(kwargs)
        if kwargs.get('text'):
            return SimpleNamespace(output_text=json.dumps({
                'name':'Sample project','summary':'Useful starter',
                'setup':'python app.py','files':[
                    {'path':'app.py','content':'def add(a,b): return a+b\n'},
                    {'path':'test_app.py','content':'from app import add\ndef test_add(): assert add(1,2)==3\n'},
                    {'path':'README.md','content':'# Sample\nRun pytest\n'}]}))
        return SimpleNamespace(output_text='## Review\nThe code has no obvious syntax errors. Run unit tests yourself.')


def test_project_types_cover_requested_domains():
    assert {'web_app','ai_bot','ml_model','data_science','api','automation','general'} <= set(PROJECT_TYPES)
    for kind in PROJECT_TYPES:
        prompt=make_build_prompt(kind,'Build a reproducible system with tests','', ['login'])
        assert PROJECT_TYPES[kind]['name'] in prompt
        assert 'never claim' in prompt.lower() or 'not automatically executed' in prompt.lower()


def test_path_safety_and_no_credentials():
    for invalid in ['../evil.py','/tmp/tool.py','C:/private.py','.env','.git/config','node_modules/index.js','secrets.json','foo\\bar.py','script.exe','foo//bar.py']:
        assert not safe_path(invalid), invalid
    assert safe_path('backend/app.py')
    with pytest.raises(ValueError):
        build_archive({'files':[{'path':'main.py','content':'api_key="sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"'}]},'ai_bot')


def test_static_check_does_not_execute_source(tmp_path):
    sentinel=tmp_path/'must-not-exist'
    files={'app.py':f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("bad")\n', 'config.json':'{"enabled":true}'}
    report=static_inspection(files)
    assert report['syntax_failures']==0
    assert not sentinel.exists()
    assert all(x['status']=='PASS' for x in report['checks'])
    broken=static_inspection({'app.py':'def nope(:\n','data.json':'{not-json'})
    assert broken['syntax_failures']==2


def test_notebook_validation_and_manifest():
    notebook=json.dumps({'nbformat':4,'cells':[],'metadata':{},'nbformat_minor':5})
    raw,manifest=build_archive({'name':'ML','files':[{'path':'study.ipynb','content':notebook}]},'data_science')
    assert manifest['tested'] is False
    assert manifest['training_performed'] is False
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist()
        assert 'HITMAN_BUILD_REVIEW.md' in names
        assert 'HITMAN_BUILD_MANIFEST.json' in names
        assert b'No project code' in archive.read('HITMAN_BUILD_REVIEW.md')
    with pytest.raises(ValueError):build_archive({'files':[{'path':'bad.py','content':'def bad(:\n'}]},'api')


def test_json_parser_accepts_fenced_payload():
    assert parse_json_object('```json\n{"files":[]}\n```')['files']==[]
    with pytest.raises(ValueError):parse_json_object('[1]')


def test_new_paths_off_by_default(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'STUDIO_BUILD',False)
    monkeypatch.setattr(main,'STUDIO_AI_REVIEW',False)
    with TestClient(main.app) as client:
        assert client.get('/studio').status_code==200
        flags=client.get('/api/config').json()['features']
        assert flags['builder_studio_static_check'] is True
        assert not flags['builder_studio_generation']
        assert client.post('/api/public/studio/build', json={
            'description':'Build a student AI bot with FastAPI and tests'}).status_code==403
        assert client.post('/api/public/studio/review', json={
            'archive_base64':encode_zip({'app.py':'print(1)'})}).status_code==403


def test_guest_static_zip_check_and_source_block(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    with TestClient(main.app) as client:
        response=client.post('/api/public/studio/check', json={
            'archive_base64':encode_zip({'app.py':'print(1)\n','test.py':'def oops(:\n'})})
        assert response.status_code==200, response.text
        assert response.json()['syntax_failures']==1
        assert client.get('/api/memory').status_code==403
        assert client.post('/api/public/studio/check',json={'archive_base64':encode_zip({'../private.py':'print(1)'})}).status_code==400


def test_project_build_returns_zip_without_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'STUDIO_BUILD',True)
    monkeypatch.setenv('GEMINI_API_KEY','offline-test')
    monkeypatch.setattr(main,'OpenAI',StudioMock)
    StudioMock.requests=[]
    with TestClient(main.app) as client:
        assert client.get('/api/config').json()['features']['builder_studio_generation']
        response=client.post('/api/public/studio/build',json={
            'project_type':'ml_model','description':'Build a safe machine learning training and evaluation pipeline',
            'stack':'scikit-learn','features':['cross validation']})
        assert response.status_code==200,response.text[:150]
        assert response.headers['content-type']=='application/zip'
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.read('app.py').startswith(b'def add')
            assert 'HITMAN_BUILD_MANIFEST.json' in archive.namelist()
            assert json.loads(archive.read('HITMAN_BUILD_MANIFEST.json'))['tested'] is False
        assert StudioMock.requests[0]['model']==main.REASONING_MODEL
        assert 'training' in StudioMock.requests[0]['input'].lower()


def test_ai_review_does_not_send_possible_secrets(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'STUDIO_AI_REVIEW',True)
    monkeypatch.setenv('GEMINI_API_KEY','offline-test')
    monkeypatch.setattr(main,'OpenAI',StudioMock)
    StudioMock.requests=[]
    with TestClient(main.app) as client:
        reply=client.post('/api/public/studio/review',json={
            'archive_base64':encode_zip({'app.py':'print(1)\n'}),'question':'Explain any error'})
        assert reply.status_code==200,reply.text
        assert 'No tests' in reply.json()['notice']
        bad=client.post('/api/public/studio/review',json={
            'archive_base64':encode_zip({'app.py':'api_key="sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"\n'})})
        assert bad.status_code==422
        assert len(StudioMock.requests)==1


def test_offline_project_templates_available_without_api(monkeypatch):
    from offline_templates import STARTERS, offline_template
    assert set(STARTERS)=={'ai_bot','ml_model','data_science'}
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with TestClient(main.app) as client:
        for kind in STARTERS:
            response=client.get('/api/public/studio/template/'+kind)
            assert response.status_code==200, response.text[:130] if response.status_code!=200 else ''
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                assert 'README.md' in archive.namelist()
                assert 'HITMAN_BUILD_MANIFEST.json' in archive.namelist()
        assert client.get('/api/public/studio/template/not-an-option').status_code==404
