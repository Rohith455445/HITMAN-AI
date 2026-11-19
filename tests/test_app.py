import os
import tempfile
os.environ["ALLOW_FIRST_ADMIN_SETUP"] = "1"
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="hitman-test-"), "tests.db")
import base64
import io
import json
import uuid
import zipfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app, read_project_archive, static_validate

client = TestClient(app)
setup = client.post('/api/auth/setup',json={'username':'testadmin','password':'testing-passphrase-123'})
assert setup.status_code == 200, setup.text

def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name, content in files.items():
            z.writestr(name, content)
    return base64.b64encode(buf.getvalue()).decode()

def test_config_and_ui():
    assert client.get('/').status_code == 200
    result = client.get('/api/config').json()
    assert result['name'] == 'HITMAN AI'
    assert result['features']['persistent_memory'] is True
    assert result['provider'] == 'gemini'
    assert result['features']['image_editing'] is False  # opt-in: not available by default on free tier

def test_memory_crud():
    note = 'Temporary test memory ' + uuid.uuid4().hex
    saved = client.post('/api/memory', json={'note': note})
    assert saved.status_code == 200
    key = saved.json()['id']
    assert any(entry['id'] == key for entry in client.get('/api/memory').json())
    assert client.delete('/api/memory/' + key).json() == {'deleted': True}
    assert client.delete('/api/memory/' + key).status_code == 404

def test_archive_sanitization_and_validation():
    assert read_project_archive(make_zip({'src/main.py':'print(3)', 'README.md':'hi'}))['src/main.py'] == 'print(3)'
    assert static_validate({'bad.py':'x =','bad.json':'{oops'})
    bad = client.post('/api/agent/repair', json={
        'instruction':'Please fix the problem in this project',
        'archive_base64':make_zip({'../escape.py':'print(1)'}), 'archive_name':'project.zip'
    })
    assert bad.status_code in (400,503)

def test_image_missing_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    assert client.post('/api/images',json={'prompt':'Create a purple bot'}).status_code == 503

def test_repair_with_stub_model(monkeypatch):
    import main
    monkeypatch.setenv('GEMINI_API_KEY','fake-test-key')
    class FakeResponse:
        output_text = json.dumps({'summary':'fixed syntax','changes':[{'path':'main.py','content':'x=1\n'}]})
    class FakeResponses:
        def create(self, **kwargs):return FakeResponse()
    class FakeOpenAI:
        responses = FakeResponses()
    monkeypatch.setattr(main,'provider',lambda:FakeOpenAI())
    result = client.post('/api/agent/repair',json={
        'instruction':'Fix the Python syntax error in the source',
        'archive_base64':make_zip({'main.py':'x =\n'}),'archive_name':'project.zip','run_tests':False
    })
    assert result.status_code == 200, result.text
    data=result.json()
    assert data['changed']==['main.py']
    assert 'passed' in data['static_checks'][0]
    artifact=client.get(data['download_url'])
    assert artifact.status_code == 200
    with zipfile.ZipFile(io.BytesIO(artifact.content)) as z:
        assert z.read('main.py')==b'x=1\n'


def test_public_pages_and_cross_account_isolation(monkeypatch):
    import account_security
    from main import app
    from fastapi.testclient import TestClient
    account_security.send_email=lambda email,subject,body: captured.append(body)
    captured=[]
    member=TestClient(app)
    for url in ('/signup','/login','/forgot-password','/reset-password','/verify-email'):
        assert member.get(url).status_code==200
    username='member'+uuid.uuid4().hex[:10]
    email=username+'@example.org'
    password='Secure-member-password-111'
    r=member.post('/api/auth/signup',json={'username':username,'email':email,'password':password})
    assert r.status_code==201,r.text
    assert member.post('/api/auth/login',json={'username':username,'password':password}).status_code==403
    token=captured[-1].split('token=')[1].split()[0]
    assert member.post('/api/auth/verify-email',json={'token':token}).status_code==200
    assert member.post('/api/auth/login',json={'username':username,'password':password}).status_code==200
    # Existing admin's memory is private to admin, not globally shared.
    note='Admin-only memory '+uuid.uuid4().hex
    admin_memory=client.post('/api/memory',json={'note':note}).json()
    assert not any(x['id']==admin_memory['id'] for x in member.get('/api/memory').json())
    assert member.delete('/api/memory/'+admin_memory['id']).status_code==404
    # Reject cross-origin modifying requests even if the user has a valid session.
    assert member.post('/api/memory',json={'note':'attacker'},headers={'Origin':'https://evil.invalid'}).status_code==403
    assert member.get('/api/config').status_code==200
    assert 'x-content-type-options' in member.get('/').headers
