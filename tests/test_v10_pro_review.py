"""Pro Review tests: all model calls simulated, no Gemini charges."""
from dataclasses import dataclass
from fastapi.testclient import TestClient
import pytest
import main
from pro_review import run_pro_review, style_instruction

@dataclass
class Delta:
    type: str
    delta: str = ''

class FakeAPI:
    def __init__(self): self.calls=[]
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get('stream'):
            return iter([Delta('response.output_text.delta','Corrected '),
                         Delta('response.output_text.delta','answer')])
        return type('Draft', (), {'output_text':'Initial answer with room for improvement.'})()

class FakeProvider:
    def __init__(self):self.responses=FakeAPI()


def test_pro_review_two_passes_with_style_and_no_tools_by_default():
    api=FakeProvider().responses
    out=run_pro_review(type('P',(),{'responses':api})(),model='gemini-example',
        input_context=[{'role':'user','content':'Explain a Python bug.'}],style='detailed')
    assert ''.join(x.delta for x in out)=='Corrected answer'
    assert len(api.calls)==2
    assert not api.calls[0].get('stream', False)
    assert api.calls[1]['stream'] is True
    assert 'Detailed' not in api.calls[0]['instructions']  # styles use natural instructions
    assert 'dependencies' in api.calls[0]['instructions']
    assert api.calls[1]['input'][-1]['role']=='user'
    assert api.calls[1]['max_output_tokens']>2000
    assert 'tools' not in api.calls[0]
    assert api.calls[0]['store'] is False and api.calls[1]['store'] is False


def test_optional_grounding_only_in_first_pass():
    api=FakeProvider().responses
    list(run_pro_review(type('P',(),{'responses':api})(),model='x',
                        input_context=[{'role':'user','content':'News'}],style='concise',grounded=True))
    assert api.calls[0]['tools']==[{'type':'web_search'}]
    assert 'tools' not in api.calls[1]


def test_style_validation_and_empty_draft_error():
    with pytest.raises(ValueError):style_instruction('ignore rules')
    class Empty(FakeProvider):
        def __init__(self):
            super().__init__()
            class E(FakeAPI):
                def create(self, **kwargs):return type('Draft',(),{'output_text':' '})()
            self.responses=E()
    with pytest.raises(ValueError):run_pro_review(Empty(),model='x',input_context=[],style='balanced')


def test_endpoint_rejects_pro_when_not_enabled(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PRO_REVIEW_ENABLED',False)
    monkeypatch.setenv('GEMINI_API_KEY','fake')
    with TestClient(main.app) as c:
        assert c.post('/api/public/chat',json={'message':'Hello','mode':'pro'}).status_code==400
        config=c.get('/api/config').json()
        assert 'pro' not in config['modes']
        assert config['features']['pro_review_two_pass'] is False
        assert config['features']['answer_styles']==['concise','balanced','detailed']


def test_endpoint_pro_streams_final_only(monkeypatch):
    provider=FakeProvider()
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PRO_REVIEW_ENABLED',True)
    monkeypatch.setattr(main,'PRO_REVIEW_GROUNDED',False)
    monkeypatch.setattr(main,'public_text_client',lambda: provider)
    monkeypatch.setenv('GEMINI_API_KEY','fake')
    with TestClient(main.app) as c:
        r=c.post('/api/public/chat',json={'message':'Write a Python solution','mode':'pro','response_style':'detailed'})
        assert r.status_code==200
        assert 'Corrected ' in r.text and 'answer' in r.text
        assert 'Initial answer' not in r.text
        assert 'event: done' in r.text
        assert len(provider.responses.calls)==2
        assert c.get('/api/config').json()['features']['pro_review_two_pass'] is True
        assert c.post('/api/public/chat',json={'message':'hi','response_style':'many'}).status_code==422


def test_ui_exposes_pro_mode_and_stop_safely():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    html=(root/'static/index.html').read_text()
    js=(root/'static/app.js').read_text()
    assert 'value="pro"' in html and 'answerStyleSelect' in html and 'stopResponse' in html
    assert "['search','analyze','research','pro']" in js
    assert 'activeRequest.abort()' in js
    assert 'response_style:detailControl.value' in js
