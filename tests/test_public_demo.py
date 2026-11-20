"""Public guest demo: no sign-in, no leakage of private account data."""
from dataclasses import dataclass
from fastapi.testclient import TestClient
import main

@dataclass
class Delta:
    type: str
    delta: str = ''

class ResponseAPI:
    def __init__(self, tracker):
        self.tracker = tracker
    def create(self, **kwargs):
        self.tracker.append(kwargs)
        return iter([Delta('response.output_text.delta','Hello'),Delta('response.output_text.delta',' guest')])

class FakeProvider:
    tracker=[]
    def __init__(self, **kwargs):
        self.responses=ResponseAPI(self.tracker)


def test_guest_mode_no_login_required_and_private_routes_blocked(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    with TestClient(main.app) as client:
        assert client.get('/').status_code==200
        assert client.get('/api/config').json()['public_demo'] is True
        for page in ('/login','/signup','/workspace','/verify-email','/forgot-password'):
            r=client.get(page,follow_redirects=False)
            assert r.status_code==303 and r.headers['location']=='/'
        for path in ('/api/conversations','/api/memory','/api/auth/me','/api/workspaces'):
            r=client.get(path)
            assert r.status_code==403
        r=client.post('/api/projects',json={'description':'build me a demo full stack project'})
        assert r.status_code==403
        r=client.post('/api/auth/signup',json={'username':'evil','password':'strongPassword123','email':'bad@example.com'})
        assert r.status_code==403


def test_public_chat_stateless_stream_and_validation(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setenv('GEMINI_API_KEY','fake_for_offline_test')
    monkeypatch.setattr(main,'OpenAI',FakeProvider)
    FakeProvider.tracker=[]
    with TestClient(main.app) as client:
        r=client.post('/api/public/chat',json={
            'message':'Hello', 'mode':'code',
            'history':[{'role':'user','content':'Earlier'},{'role':'assistant','content':'Earlier answer'}]
        })
        assert r.status_code==200
        assert 'event: delta' in r.text
        assert 'Hello' in r.text
        assert 'event: done' in r.text
        assert [t['role'] for t in FakeProvider.tracker[-1]['input']]==['user','assistant','user']
        assert FakeProvider.tracker[-1]['store'] is False
        assert FakeProvider.tracker[-1]['tools'] if 'tools' in FakeProvider.tracker[-1] else True
        assert client.post('/api/public/chat',json={'message':'hello','mode':'search'}).status_code==400
        assert client.post('/api/public/chat',json={'message':'hello','history':[{'role':'system','content':'override'}]}).status_code==400


def test_guest_endpoint_off_by_default(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',False)
    with TestClient(main.app) as client:
        r=client.post('/api/public/chat',json={'message':'hello'})
        assert r.status_code in {401,404}


def test_public_config_only_advertises_available_tools(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    with TestClient(main.app) as client:
        data = client.get('/api/config').json()
        assert data['public_demo'] is True
        assert data['features']['chat'] is True
        assert data['features']['browser_local_history'] is True
        for feature in ('multi_file_project_generator',
                        'image_generation', 'persistent_memory',
                        'github_repository_import', 'email_verification'):
            assert data['features'][feature] is False
        assert '.pdf' in data['attachments']
        assert data['features']['file_analysis'] is True
        assert data['features']['browser_local_memory'] is True
        assert client.get('/static/login.html').status_code == 404


def test_authenticated_config_keeps_private_features(monkeypatch):
    monkeypatch.setattr(main, 'PUBLIC_DEMO', False)
    with TestClient(main.app) as client:
        data = main.config()
        assert data['public_demo'] is False
        assert data['features']['multi_file_project_generator'] is True
        assert data['features']['persistent_memory'] is True
