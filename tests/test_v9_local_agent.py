"""No Docker daemon or model credentials needed: all external tools are mocked."""
import ast
import base64
import io
import json
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from local_agent import (AgentError, apply_changes, docker_run,
                         get_test_plan, read_agent_zip, run_agent, validate_files)


def make_zip(files):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for key,val in files.items():z.writestr(key,val)
    return base64.b64encode(buf.getvalue()).decode()


def fake_executor(source, plan, command):
    """Mock an executor that reports a real bug based on text, without executing it."""
    text=(source/'app.py').read_text()
    if 'return a - b' in text and '-m' in command and 'pytest' in command:
        return {'status':'FAIL','exit_code':1,'output':'AssertionError: expected add(2,3)==5',
                'recipe':'pytest -q','timeout':False}
    return {'status':'PASS','exit_code':0,
            'output':'1 passed in 0.01s' if '-m' in command and 'pytest' in command else 'Python syntax OK: 2 files',
            'recipe':'compile or pytest','timeout':False}


def test_agent_selects_bounded_recipes():
    assert get_test_plan({'app.py':'def add(a,b):return a+b'})['recipe']=='python_syntax'
    assert get_test_plan({'app.py':'def add(a,b):return a+b',
                          'test_app.py':'def test_add():assert 1==1'})['recipe']=='pytest'
    assert get_test_plan({'app.py':'print(1)','test_app.py':'import unittest\nclass T(unittest.TestCase):pass'})['recipe']=='unittest'
    assert get_test_plan({'index.js':'console.log(1)'})['recipe']=='node_syntax'
    assert get_test_plan({'index.html':'<p>ok</p>'})['recipe']=='static_only'


def test_agent_rejects_secrets_and_new_files():
    with pytest.raises(AgentError):validate_files({'../escape.py':'print(1)'})
    with pytest.raises(AgentError):validate_files({'app.py':'api_key="sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"'})
    with pytest.raises(AgentError):apply_changes({'app.py':'x=1'}, {'changes':[{'path':'new.py','content':'x=2'}]})
    with pytest.raises(AgentError):apply_changes({'app.py':'x=1'}, {'changes':[{'path':'app.py','content':'password="sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ12345"'}]})


def test_agent_repairs_broken_test_and_retests():
    original={'app.py':'def add(a, b):\n    return a - b\n',
              'test_app.py':'from app import add\ndef test_add(): assert add(2, 3) == 5\n'}
    calls=[]
    def fixer(files, report, goal):
        calls.append(report['status'])
        return {'summary':'Correct addition', 'changes':[{'path':'app.py',
                'content':'def add(a, b):\n    return a + b\n'}]}
    archive, manifest=run_agent(original, rounds=2, fixer=fixer, executor=fake_executor, goal='Fix add')
    assert calls==['FAIL']
    assert manifest['status']=='PASS'
    assert manifest['tests_executed'] is True
    assert manifest['tests_passed'] is True
    assert manifest['rounds']==1
    assert manifest['changed_files']==['app.py']
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        assert 'return a + b' in z.read('app.py').decode()
        assert 'return a - b' not in z.read('app.py').decode()
        assert 'HITMAN_AGENT_MANIFEST.json' in z.namelist()
        assert 'HITMAN_AGENT_REPORT.md' in z.namelist()
        assert 'before/app.py' in z.read('HITMAN_AGENT_REPORT.md').decode()
    assert original['app.py'].endswith('a - b\n')


def test_no_tests_is_labeled_syntax_only():
    archive, manifest=run_agent({'app.py':'print(1)'}, executor=fake_executor)
    assert manifest['status']=='PASS'
    assert manifest['tests_executed'] is False
    assert manifest['tests_passed'] is False
    assert any('No verified test count' in note for note in manifest['notes'])


def test_missing_docker_is_reported_not_success():
    def missing(source, plan, args):
        return {'status':'UNAVAILABLE','exit_code':None,'output':'Docker missing',
                'recipe':'syntax','timeout':False}
    zipped,manifest=run_agent({'app.py':'print(1)'},executor=missing,rounds=0)
    assert manifest['status']=='UNAVAILABLE'
    assert not manifest['tests_executed']
    assert any('No Docker' in note for note in manifest['notes'])


def test_docker_args_restrict_host_access(monkeypatch, tmp_path):
    source=tmp_path/'src';source.mkdir()
    seen={}
    class FakePopen:
        def __init__(self, command, **kwargs):
            seen['command']=command
            self.stdout=io.BytesIO(b'ok')
        def wait(self, timeout=None):
            return 0
    monkeypatch.setattr(subprocess,'Popen',FakePopen)
    result=docker_run(source,{'language':'python'},['python','-B','-c','print(1)'])
    cmd=seen['command']
    assert result['status']=='PASS'
    assert cmd[:2]==['docker','run']
    for flag in ['--network=none','--read-only','--cap-drop=ALL',
                 '--security-opt=no-new-privileges:true','--pull=never','--user=65534:65534']:
        assert flag in cmd
    assert any(x.endswith('dst=/work,readonly') for x in cmd)
    assert '--privileged' not in cmd
    assert '--env=GEMINI_API_KEY' not in cmd


def test_agent_api_never_public_and_requires_loopback(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'LOCAL_AGENT_ENABLED',False)
    payload={'archive_base64':make_zip({'app.py':'print(1)'}),'rounds':0}
    with TestClient(main.app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',54321)) as client:
        r=client.post('/api/local/studio/agent',json=payload,
          headers={'Origin':'http://127.0.0.1:8000','X-HITMAN-Local-Agent':'1'})
        assert r.status_code==403
        monkeypatch.setattr(main,'LOCAL_AGENT_ENABLED',True)
        r=client.post('/api/local/studio/agent',json=payload,headers={'Origin':'https://evil.example','X-HITMAN-Local-Agent':'1'})
        assert r.status_code==403
        r=client.post('/api/local/studio/agent',json=payload,headers={'Origin':'http://127.0.0.1:8000'})
        assert r.status_code==403


def test_local_endpoint_report_with_mocked_docker(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'LOCAL_AGENT_ENABLED',True)
    def fake_agent(files, **kwargs):
        return b'PK-test', {'status':'PASS','tests_executed':False,'tests_passed':False,'rounds':0,
                           'changed_files':[], 'history':[], 'notes':[]}
    monkeypatch.setattr(main,'run_agent',fake_agent)
    with TestClient(main.app,base_url='http://127.0.0.1:8000',client=('127.0.0.1',54321)) as client:
        response=client.post('/api/local/studio/agent',json={'archive_base64':make_zip({'app.py':'print(1)'})},
                             headers={'Origin':'http://127.0.0.1:8000','X-HITMAN-Local-Agent':'1'})
        assert response.status_code==200,response.text
        assert base64.b64decode(response.json()['archive_base64'])==b'PK-test'
        assert client.get('/api/config').json()['features']['autonomous_local_code_execution']


def test_failed_json_not_reported_as_project_pass():
    original={'app.py':'print(1)','config.json':'{invalid'}
    zipped, manifest=run_agent(original, executor=fake_executor)
    assert manifest['status']=='FAIL'
    assert manifest['tests_passed'] is False


def test_zero_unittest_count_must_not_claim_tests_passed():
    def no_tests(source, plan, command):
        return {'status':'PASS','exit_code':0,
                'output':'Ran 0 tests in 0.000s\nOK' if '-m' in command else 'Python syntax OK',
                'recipe':'unittest','timeout':False}
    files={'app.py':'x=1', 'test_app.py':'import unittest\nclass Demo(unittest.TestCase): pass'}
    zipped, manifest=run_agent(files, executor=no_tests)
    assert manifest['status']=='NOT_VERIFIED'
    assert manifest['tests_executed'] is False
    assert manifest['tests_passed'] is False


def test_agent_accepts_complete_generated_builder_zip():
    from studio_engine import build_archive
    files = [{'path':f'package/file_{i}.py','content':f'X={i}\n'} for i in range(14)]
    raw,manifest=build_archive({'name':'Small Full App','files':files},'api')
    unwrapped=read_agent_zip(base64.b64encode(raw).decode())
    assert len(unwrapped)==15  # 14 files + auto README.md, but not manifests
    assert 'HITMAN_BUILD_MANIFEST.json' not in unwrapped
    assert 'HITMAN_BUILD_REVIEW.md' not in unwrapped


def test_agent_rejects_symlinks_and_zip_slip():
    import stat
    info=zipfile.ZipInfo('linked.py')
    info.create_system=3
    info.external_attr=(stat.S_IFLNK | 0o777)<<16
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as archive:archive.writestr(info,'real.py')
    with pytest.raises(AgentError):read_agent_zip(base64.b64encode(buf.getvalue()).decode())
    with pytest.raises(AgentError):read_agent_zip(make_zip({'../outside.py':'print(1)'}))


def test_json_only_archive_reports_static_failure_and_can_repair():
    before={'settings.json':'{not-json'}
    attempts=[]
    def fix(files, failed, goal):
        attempts.append(failed['static_report']['syntax_failures'])
        return {'summary':'Fix JSON syntax', 'changes':[{'path':'settings.json',
                'content':'{"enabled": true}'}]}
    zipped,report=run_agent(before,rounds=1,fixer=fix)
    assert report['rounds']==1
    assert report['status']=='NOT_RUN'  # corrected JSON; still no executed test suite
    assert report['tests_passed'] is False
    assert attempts==[1]
