"""Offline end-to-end tests for verification, recovery, GitHub and dependency workflow."""
import base64
import io
import json
import os
import re
import tempfile
import types
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

import account_security
import github_integration
import workspace


def app_fixture(monkeypatch, root):
    workspace.configure(root/'app.sqlite', lambda _: {'main.py':'def answer():\n    return 1\n'},
                        lambda files: [], lambda files, install=False: ('Disabled',None),
                        lambda: types.SimpleNamespace(responses=types.SimpleNamespace(create=lambda **_: types.SimpleNamespace(output_text=json.dumps({
                            'summary':'Fix answer','changes':[{'path':'main.py','content':'def answer():\n    return 42\n'}]})))),
                        lambda:'gpt-6.2-astra',lambda:{'effort':'high'})
    github_integration.init()
    app=FastAPI()
    app.include_router(workspace.router)
    app.include_router(account_security.router)
    app.include_router(github_integration.router)
    emails=[]
    monkeypatch.setattr(account_security,'send_email',lambda to,subject,body:emails.append((to,subject,body)))
    return app,emails


def token_from_email(body):
    return body.split('token=')[1].split()[0]


def test_email_verification_and_recovery(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        app,emails=app_fixture(monkeypatch,Path(tmp))
        browser=TestClient(app); another=TestClient(app)
        pw='Long-safe-password-101'
        r=browser.post('/api/auth/signup',json={'username':'dev1','password':pw,'email':'Dev1@example.org'})
        assert r.status_code==201,r.text
        assert browser.get('/api/auth/me').status_code==401
        assert browser.post('/api/auth/login',json={'username':'dev1','password':pw}).status_code==403
        token=token_from_email(emails[-1][2])
        assert browser.post('/api/auth/verify-email',json={'token':token}).status_code==200
        assert browser.post('/api/auth/verify-email',json={'token':token}).status_code==400
        assert browser.post('/api/auth/login',json={'username':'dev1','password':pw}).status_code==200
        assert 'httponly' in browser.cookies.get('hitman_session') if False else 'hitman_session' in browser.cookies
        workspace_id=browser.post('/api/workspaces',json={'name':'Private code'}).json()['id']
        assert another.get('/api/workspaces/'+workspace_id).status_code==401
        assert browser.post('/api/auth/forgot-password',json={'email':'unknown@example.org'}).status_code==200
        assert browser.post('/api/auth/forgot-password',json={'email':'dev1@example.org'}).status_code==200
        reset=token_from_email(emails[-1][2])
        assert browser.post('/api/auth/reset-password',json={'token':reset,'new_password':'Different-password-202'}).status_code==200
        assert browser.get('/api/auth/me').status_code==401
        assert browser.post('/api/auth/reset-password',json={'token':reset,'new_password':'Different-password-202'}).status_code==400
        assert browser.post('/api/auth/login',json={'username':'dev1','password':pw}).status_code==401
        assert browser.post('/api/auth/login',json={'username':'dev1','password':'Different-password-202'}).status_code==200
        assert browser.get('/api/workspaces/'+workspace_id).status_code==200


def test_github_connect_import_review_publish(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        app,emails=app_fixture(monkeypatch,Path(tmp))
        monkeypatch.setenv('GITHUB_TOKEN_ENCRYPTION_KEY',Fernet.generate_key().decode())
        browser=TestClient(app)
        pw='Long-safe-password-104'
        browser.post('/api/auth/signup',json={'username':'repoowner','password':pw,'email':'repoowner@example.org'})
        browser.post('/api/auth/verify-email',json={'token':token_from_email(emails[-1][2])})
        assert browser.post('/api/auth/login',json={'username':'repoowner','password':pw}).status_code==200
        calls=[]
        def fake_api(token,method,endpoint,data=None):
            assert token=='github_pat_dummy_credential_12345'
            calls.append((method,endpoint,data))
            if endpoint=='/user':return {'login':'octocat'}
            if endpoint.startswith('/user/repos?'):return [{'name':'demo','full_name':'octocat/demo','private':True,'default_branch':'main','permissions':{'push':True}}]
            if endpoint=='/repos/octocat/demo':return {'default_branch':'main','full_name':'octocat/demo'}
            if endpoint.endswith('/branches/main'):return {'commit':{'sha':'a'*40}}
            if endpoint.endswith('/git/commits/'+'a'*40):return {'tree':{'sha':'b'*40}}
            if endpoint.endswith('/git/trees/'+'b'*40+'?recursive=1'):return {'tree':[{'type':'blob','path':'main.py','sha':'c'*40,'size':30}], 'truncated':False}
            if endpoint.endswith('/git/blobs/'+'c'*40):return {'encoding':'base64','content':base64.b64encode(b'def answer():\n    return 1\n').decode()}
            if endpoint.endswith('/git/trees') and method=='POST':return {'sha':'d'*40}
            if endpoint.endswith('/git/commits') and method=='POST':return {'sha':'e'*40}
            if endpoint.endswith('/git/refs') and method=='POST':return {'ref':data['ref']}
            if endpoint.endswith('/pulls') and method=='POST':return {'number':3,'html_url':'https://github.com/octocat/demo/pull/3'}
            raise AssertionError('Unexpected GitHub request '+method+' '+endpoint)
        monkeypatch.setattr(github_integration,'api',fake_api)
        r=browser.post('/api/github/connect',json={'token':'github_pat_dummy_credential_12345'})
        assert r.status_code==200,r.text
        with workspace.connection() as con:
            encrypted=con.execute('SELECT token_encrypted FROM github_tokens').fetchone()[0]
            assert b'github_pat_dummy_credential' not in encrypted
        assert browser.get('/api/github/repos').json()[0]['full_name']=='octocat/demo'
        r=browser.post('/api/github/import',json={'owner':'octocat','repo':'demo'})
        assert r.status_code==200,r.text
        wid=r.json()['id']
        assert browser.get('/api/workspaces/'+wid+'/github').json()['linked']
        assert browser.post('/api/workspaces/'+wid+'/github/pull-request',json={
            'confirmation':'CREATE_PULL_REQUEST','title':'Add answer fix'}).status_code==409
        change=browser.post('/api/workspaces/'+wid+'/proposals',json={'instruction':'Please fix this function correctly'})
        assert change.status_code==200,change.text
        assert browser.post('/api/workspaces/'+wid+'/proposals/'+change.json()['id']+'/apply').status_code==200
        assert browser.post('/api/workspaces/'+wid+'/github/pull-request',json={
            'confirmation':'NO','title':'Add answer fix'}).status_code==400
        pr=browser.post('/api/workspaces/'+wid+'/github/pull-request',json={
            'confirmation':'CREATE_PULL_REQUEST','title':'Add answer fix','description':'Tests reviewed'})
        assert pr.status_code==200,pr.text
        assert pr.json()['draft'] is True
        assert pr.json()['pull_request_url'].endswith('/3')
        assert any(method=='POST' and endpoint.endswith('/pulls') and data['draft'] is True for method,endpoint,data in calls)
        browser.delete('/api/github/disconnect')
        assert browser.get('/api/github/status').json()['connected'] is False


def test_dependency_runner_network_separation(monkeypatch):
    import dependency_runner
    monkeypatch.setenv('ENABLE_DOCKER_TESTS','1')
    monkeypatch.setenv('ENABLE_DEP_INSTALL','1')
    monkeypatch.setattr(dependency_runner.shutil,'which',lambda _: '/usr/bin/docker')
    commands=[]
    def fake_run(command,**kwargs):
        commands.append(command)
        return types.SimpleNamespace(returncode=0,stdout='pass',stderr='')
    monkeypatch.setattr(dependency_runner.subprocess,'run',fake_run)
    output,passed=dependency_runner.run({'requirements.txt':'pytest==8.3.2\n','tests/test_example.py':'def test_example():\n    assert True\n'},install=True)
    assert passed is True
    assert len(commands)==2
    assert commands[0][commands[0].index('--network')+1]=='bridge'
    assert commands[1][commands[1].index('--network')+1]=='none'
    assert '--cap-drop' in commands[0]
    assert '--read-only' in commands[1]
    out,result=dependency_runner.run({'requirements.txt':'-e git+https://bad.example/package\n',
                       'tests/test_example.py':'def test_example(): pass'},install=True)
    assert result is None
    assert 'pinned' in out


def test_autofix_requires_review_even_after_passing_tests(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        app,emails=app_fixture(monkeypatch,Path(tmp))
        # Fail first attempt, then pass once AI changes the code.
        workspace._sandbox_runner=lambda files,install=False: ('Assertion failed' if 'return 1' in files.get('main.py','') else '1 passed',
                                                                False if 'return 1' in files.get('main.py','') else True)
        browser=TestClient(app)
        pw='Strong-passphrase-908'
        assert browser.post('/api/auth/signup',json={'username':'autofix1','password':pw,'email':'autofix1@example.org'}).status_code==201
        browser.post('/api/auth/verify-email',json={'token':token_from_email(emails[-1][2])})
        browser.post('/api/auth/login',json={'username':'autofix1','password':pw})
        w=browser.post('/api/workspaces',json={'name':'Fix project','archive_base64':'ZHVtbXk='}).json()['id']
        r=browser.post('/api/workspaces/'+w+'/autofix',json={'goal':'Make the answer function return forty two'})
        assert r.status_code==200,r.text
        assert r.json()['tests_passed'] is True
        assert r.json()['status']=='pending'
        assert 'return 1' in browser.get('/api/workspaces/'+w+'/files?path=main.py').json()['content']
        pid=r.json()['id']
        assert browser.post('/api/workspaces/'+w+'/proposals/'+pid+'/apply').status_code==200
        assert 'return 42' in browser.get('/api/workspaces/'+w+'/files?path=main.py').json()['content']
