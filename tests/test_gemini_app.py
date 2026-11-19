"""End-to-end FastAPI chat path with a mocked Gemini response; no API/network call."""
import uuid
from types import SimpleNamespace
from fastapi.testclient import TestClient


def test_chat_to_gemini_sse_and_conversation(monkeypatch):
    import main, account_security
    fake_user={'id':uuid.uuid4().hex, 'username':'gemini-tester','role':'member'}
    monkeypatch.setattr(main.hitman_workspace,'token_user',lambda token:fake_user)
    monkeypatch.setattr(account_security,'quota',lambda *args,**kwargs:None)
    monkeypatch.setenv('GEMINI_API_KEY','fake-test-key')
    arguments=[]
    class FakeResponses:
        def create(self,**kwargs):
            arguments.append(kwargs)
            assert kwargs['model'].startswith('gemini-')
            assert kwargs['stream'] is True
            return iter([
                SimpleNamespace(type='response.output_text.delta',delta='Hello'),
                SimpleNamespace(type='response.output_text.delta',delta=' from Gemini!'),
            ])
    class FakeClient:
        responses=FakeResponses()
    monkeypatch.setattr(main,'OpenAI',lambda **kwargs:FakeClient())
    client=TestClient(main.app)
    conversation_id=str(uuid.uuid4())
    result=client.post('/api/chat',json={'conversation_id':conversation_id,'message':'Hi from the test','mode':'standard'})
    assert result.status_code==200,result.text
    assert 'event: delta' in result.text
    assert 'Hello from Gemini!' not in result.text  # delivered as separate SSE deltas
    assert 'Hello' in result.text and ' from Gemini!' in result.text
    assert 'event: done' in result.text
    assert len(arguments)==1
    messages=client.get('/api/conversations/'+conversation_id)
    assert messages.status_code==200,messages.text
    assert messages.json()[-1]=={'role':'assistant','content':'Hello from Gemini!'}
