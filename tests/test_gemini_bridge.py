"""Offline Gemini conversion/provider tests; never call Google's live service."""
import base64
import json
from types import SimpleNamespace

import pytest
from gemini_bridge import (_payload, _messages, _get_text, GeminiClient,
                           GeminiAPIError, _get_grounding_links)


def test_model_and_input_conversion():
    image = base64.b64encode(b'\x89PNG').decode()
    inp = [
        {'role':'user','content':'Hello'},
        {'role':'assistant','content':'Hi!'},
        {'role':'user','content':[{'type':'input_text','text':'Describe it'},
                  {'type':'input_image','image_url':f'data:image/png;base64,{image}'}]},
    ]
    result = _messages(inp)
    assert [item['role'] for item in result] == ['user','model','user']
    assert result[-1]['parts'][1]['inlineData']['mimeType'] == 'image/png'
    assert result[-1]['parts'][1]['inlineData']['data'] == image
    with pytest.raises(ValueError):
        _messages([{'role':'user','content':[{'type':'input_image','image_url':'https://example.com/x.png'}]}])


def test_json_generation_config():
    req = _payload(model='gemini-3.5-flash-lite',input='Build a project',
                   instructions='Return code',text={'format':{'type':'json_object'}},
                   max_output_tokens=9000,store=False)
    assert req['generationConfig']['responseMimeType'] == 'application/json'
    assert req['systemInstruction']['parts'][0]['text'] == 'Return code'
    assert req['contents'][0]['role'] == 'user'


def test_tools_are_off_by_default(monkeypatch):
    monkeypatch.delenv('GEMINI_ENABLE_SEARCH', raising=False)
    with pytest.raises(GeminiAPIError,match='disabled'):
        _payload(model='gemini-3.5-flash-lite',input='Who?',tools=[{'type':'web_search'}])
    monkeypatch.setenv('GEMINI_ENABLE_SEARCH','1')
    req=_payload(model='gemini-3.5-flash-lite',input='Who?',tools=[{'type':'web_search'}])
    assert req['tools'] == [{'googleSearch':{}}]
    monkeypatch.setenv('GEMINI_ENABLE_CODE_EXECUTION','1')
    req=_payload(model='gemini-3.5-flash-lite',input='2+2', tools=[{'type':'code_interpreter','container':{'type':'auto'}}])
    assert req['tools'] == [{'codeExecution':{}}]


def test_response_from_fake_gemini_api():
    client = GeminiClient(api_key='fake-test-key')
    observed=[]
    def fake(model, action, payload):
        observed.append((model,action,payload))
        return {'candidates':[{'content':{'parts':[{'text':'Fixed the bug.'}]}}]}
    client.request=fake
    result=client.responses.create(model='gemini-3.5-flash-lite',input='Fix bug',stream=False)
    assert result.status=='completed'
    assert result.output_text=='Fixed the bug.'
    assert observed[0][0]=='gemini-3.5-flash-lite'
    assert observed[0][1]=='generateContent'
    assert observed[0][2]['contents'][0]['parts'][0]['text']=='Fix bug'


def test_streaming_server_sent_event(monkeypatch):
    import gemini_bridge
    packet1={'candidates':[{'content':{'parts':[{'text':'Hello'}]}}]}
    packet2={'candidates':[{'content':{'parts':[{'text':' world!'}]}}]}
    class FakeResponse:
        status_code=200
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def iter_lines(self):
            return iter(['data: '+json.dumps(packet1),'','data: '+json.dumps(packet2),''])
    class FakeHttpx:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def stream(self,*args,**kwargs): return FakeResponse()
    monkeypatch.setattr(gemini_bridge.httpx,'Client',FakeHttpx)
    client=GeminiClient(api_key='fake-test-key')
    changes=list(client.responses.create(model='gemini-3.5-flash-lite',input='Hi',stream=True))
    assert ''.join(x.delta for x in changes)=='Hello world!'
    assert all(x.type=='response.output_text.delta' for x in changes)


def test_image_requires_opt_in(monkeypatch):
    monkeypatch.delenv('GEMINI_ENABLE_IMAGES',raising=False)
    client=GeminiClient(api_key='fake-test-key')
    with pytest.raises(GeminiAPIError,match='disabled'):
        client.images.generate(model='gemini-3.1-flash-lite-image',prompt='Tree')
