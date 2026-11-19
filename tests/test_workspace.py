"""Offline workspace API integration tests; no OpenAI credentials required."""
import base64
import io
import json
import os
import re
import sys
import tempfile
import types
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import workspace


def makezip(content):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for k,v in content.items(): z.writestr(k,v)
    return base64.b64encode(out.getvalue()).decode()


def fake_archive(b64):
    results={}
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(b64))) as z:
        for item in z.namelist():
            if '..' in Path(item).parts: raise ValueError('Unsafe archive')
            results[item]=z.read(item).decode()
    return results


def checker(files):
    import ast
    errors=[]
    for path,source in files.items():
        if path.endswith('.py'):
            try: ast.parse(source)
            except SyntaxError: errors.append(path+' syntax')
    return errors


class MockResponses:
    def create(self,**kwargs):
        return types.SimpleNamespace(output_text=json.dumps({'summary':'Fixed bug with tests','changes':[{'path':'src/app.py','content':'def answer():\n    return 42\n'}]}))


class MockClient:
    responses=MockResponses()


def test_workspace_multiuser_and_review(monkeypatch):
    monkeypatch.setenv('ALLOW_FIRST_ADMIN_SETUP', '1')
    with tempfile.TemporaryDirectory() as d:
        # Validate changes imports this simple project's path rules from main.
        fake=types.ModuleType('main')
        fake.valid_project_path=lambda s: bool(re.fullmatch('[a-zA-Z0-9_./-]+',s)) and '..' not in Path(s).parts
        fake.ALLOWED_EDIT_EXTENSIONS={'.py','.md','.json'}
        monkeypatch.setitem(sys.modules,'main',fake)
        workspace.configure(Path(d)/'db.sqlite',fake_archive,checker,lambda files:('Docker disabled',None),lambda:MockClient(),lambda:'test-model',lambda:{'effort':'high'})
        app=FastAPI()
        app.include_router(workspace.router)
        a,b=TestClient(app),TestClient(app)
        r=a.post('/api/auth/setup',json={'username':'owner','password':'very-long-passphrase'});assert r.status_code==200,r.text
        assert a.post('/api/auth/setup',json={'username':'other','password':'very-long-passphrase'}).status_code==409
        r=a.post('/api/auth/users',json={'username':'member','password':'member-passphrase-123'});assert r.status_code==200
        assert b.post('/api/auth/login',json={'username':'member','password':'member-passphrase-123'}).status_code==200
        assert b.post('/api/auth/users',json={'username':'third','password':'very-long-passphrase'}).status_code==403
        assert a.post('/api/workspaces',json={'name':'Repo A','archive_base64':makezip({'src/app.py':'def answer():\n return 1\n'})}).status_code==200
        w=a.get('/api/workspaces').json()[0]['id']
        assert b.get('/api/workspaces/'+w).status_code==404
        assert b.get('/api/workspaces/'+w+'/download').status_code==404
        assert b.post('/api/workspaces/'+w+'/proposals',json={'instruction':'Please fix the answer function'}).status_code==404
        p=a.post('/api/workspaces/'+w+'/proposals',json={'instruction':'Please fix the answer function'});assert p.status_code==200,p.text
        proposal=p.json(); assert '- return 1' in proposal['diff'] or '- return 1' in proposal['diff'].replace('  ',' ')
        current=a.get('/api/workspaces/'+w+'/files?path=src%2Fapp.py').json();assert 'return 1' in current['content']
        assert a.post('/api/workspaces/'+w+'/proposals/'+proposal['id']+'/apply').status_code==200
        updated=a.get('/api/workspaces/'+w+'/files?path=src%2Fapp.py').json();assert 'return 42' in updated['content']
        assert a.post('/api/workspaces/'+w+'/proposals/'+proposal['id']+'/apply').status_code==409
        z=a.get('/api/workspaces/'+w+'/download');assert z.status_code==200
        with zipfile.ZipFile(io.BytesIO(z.content)) as out:assert 'return 42' in out.read('src/app.py').decode()
        tests=a.post('/api/workspaces/'+w+'/tests').json();assert tests['tests_executed'] is False
        assert a.post('/api/auth/logout').status_code==200
        assert a.get('/api/workspaces').status_code==401
