"""Regression checks for the grounded, source-backed v12 visitor experience."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
import pytest
import account_security
from fastapi.testclient import TestClient
import main
import research_sources as rs
from gemini_bridge import _get_grounding_sources, _GeminiResponses, GeminiClient

@pytest.fixture(autouse=True)
def isolate_external_search_tests_from_shared_usage_limits(monkeypatch):
    # These synthetic calls must not consume the production-like SQLite rate counters
    # used by the older end-to-end tests in this process.
    monkeypatch.setattr(account_security, 'rate_limit', lambda *a,**kw: None)
    monkeypatch.setattr(account_security, 'quota', lambda *a,**kw: None)


def test_google_grounding_metadata_produces_only_real_links():
    source = {'candidates':[{'groundingMetadata':{'groundingChunks':[
        {'web':{'uri':'https://www.icc-cricket.com/news/match','title':'ICC match report'}},
        {'web':{'uri':'javascript:alert(1)','title':'Injection'}},
        {'web':{'uri':'http://example.com','title':'Not secure'}},
        {'web':{'uri':'https://www.icc-cricket.com/news/match','title':'Duplicate'}}]}}]}
    sources = _get_grounding_sources(source)
    assert len(sources) == 1
    assert sources[0]['title'] == 'ICC match report'
    assert sources[0]['url'] == 'https://www.icc-cricket.com/news/match'
    assert not _get_grounding_sources({'candidates':[{'content':{'parts':[{'text':'I saw the internet'}]}}]})


def test_brave_search_sources_are_bounded_and_sanitized(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','test-not-secret')
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {'web':{'results':[
                {'title':'<b>Cricket</b>','url':'https://example.com/cricket','description':'<em>Match</em> details', 'thumbnail':{'src':'https://img.example.com/photo.jpg'}},
                {'title':'Forbidden','url':'http://localhost/admin','description':'No'},
                {'title':'Local IP','url':'https://192.168.1.1/admin','description':'No'}]}}
    class FakeClient:
        def __init__(self,*a,**kw): pass
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def get(self,url,**kw):
            assert url == rs.BRAVE_ENDPOINT
            assert kw['headers']['X-Subscription-Token'] == 'test-not-secret'
            assert kw['params']['freshness'] == 'pd'
            return FakeResponse()
    monkeypatch.setattr(rs.httpx,'Client',FakeClient)
    sources=rs.search_brave('today cricket updates',freshness='pd')
    assert len(sources)==1
    assert sources[0]['title']=='Cricket'
    assert sources[0]['snippet']=='Match details'
    assert sources[0]['thumbnail'].endswith('.jpg')
    body=rs.source_context('Cricket today',sources)
    assert '[1]' in body and 'https://example.com/cricket' in body


def test_weather_data_never_guessed(monkeypatch):
    class FakeResponse:
        def __init__(self,data): self.data=data
        def raise_for_status(self): pass
        def json(self): return self.data
    class FakeClient:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,url,**kw):
            if url==rs.GEOCODE_ENDPOINT:
                return FakeResponse({'results':[{'name':'Chennai','country':'India','admin1':'Tamil Nadu','latitude':13.08,'longitude':80.27}]})
            assert url==rs.FORECAST_ENDPOINT
            return FakeResponse({'timezone':'Asia/Kolkata','current':{'temperature_2m':27,'apparent_temperature':30,'relative_humidity_2m':69,'wind_speed_10m':8,'time':'2026-11-20T09:00'},
                'hourly':{'time':['2026-11-20T09:00','2026-11-20T10:00'], 'temperature_2m':[27,28],
                          'precipitation_probability':[10,20],'weather_code':[1,2]},
                'daily':{'time':['2026-11-20'],'temperature_2m_max':[32],
                         'temperature_2m_min':[23],'precipitation_probability_max':[30], 'weather_code':[1]}})
    monkeypatch.setattr(rs.httpx,'Client',FakeClient)
    monkeypatch.setenv('HITMAN_DEFAULT_WEATHER_CITY','Chennai, India')
    result=rs.weather_snapshot('today weather updates')
    assert result['used_default_city'] is True
    assert result['current']['temperature']==27
    assert result['days'][0]['high']==32
    assert result['hours'][0]['rain_probability']==10
    assert '27°C' in rs.weather_as_markdown(result)
    assert 'Source: [Open-Meteo' in rs.weather_as_markdown(result)


class FakeModel:
    calls=[]
    def __init__(self,*a,**kw): self.responses=self
    def create(self,**kw):
        self.calls.append(kw)
        return iter([SimpleNamespace(type='response.output_text.delta',delta='The reported score is source-dependent.'),
                     SimpleNamespace(type='response.sources',sources=[{'url':'https://www.icc-cricket.com/news','title':'ICC news'}])])


def test_guest_chat_with_brave_sources_no_google_tool(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_SEARCH',True)
    monkeypatch.setattr(main,'AUTO_WEB_SEARCH',True)
    monkeypatch.setattr(main,'BRAVE_SEARCH',True)
    monkeypatch.setattr(main,'GOOGLE_SEARCH',False)
    monkeypatch.setattr(main,'TEXT_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock')
    monkeypatch.setattr(main,'OpenAI',FakeModel)
    monkeypatch.setattr(main,'search_brave',lambda *a,**k:[{'url':'https://www.icc-cricket.com/news','title':'ICC news','snippet':'Latest news snippet'}])
    FakeModel.calls=[]
    with TestClient(main.app) as client:
        result=client.post('/api/public/chat',json={'message':'today cricket updates'})
        assert result.status_code==200
        assert 'event: sources' in result.text
        assert 'ICC news' in result.text
        assert not FakeModel.calls[0].get('tools')
        assert 'Latest news snippet' in str(FakeModel.calls[0]['input'])


def test_guest_weather_card_skips_ai_call(monkeypatch):
    monkeypatch.setattr(main,'PUBLIC_DEMO',True)
    monkeypatch.setattr(main,'PUBLIC_WEATHER',True)
    monkeypatch.setattr(main,'AUTO_WEB_SEARCH',False)
    monkeypatch.setattr(main,'TEXT_PROVIDER','gemini')
    monkeypatch.setenv('GEMINI_API_KEY','mock')
    monkeypatch.setattr(main,'OpenAI',FakeModel)
    monkeypatch.setattr(main,'weather_snapshot',lambda question:{
       'location':'Chennai, India','current':{'temperature':26,'feels_like':28,'humidity':50,'wind_kmh':9},
       'observed_time':'2026-11-20T09:00','timezone':'Asia/Kolkata','used_default_city':True,'days':[],'hours':[]})
    FakeModel.calls=[]
    with TestClient(main.app) as client:
        response=client.post('/api/public/chat',json={'message':'today wether updates'})
        assert response.status_code==200
        assert 'event: weather' in response.text
        assert '26°C' in response.text
        assert FakeModel.calls==[]


def test_browser_renders_cards_without_innerhtml():
    from pathlib import Path
    js=(Path(__file__).parents[1]/'static/app.js').read_text()
    assert 'showResearchDecorations(bubble' in js
    assert "type === 'weather'" in js
    assert "type === 'sources'" in js
    block=js.split('function showResearchDecorations',1)[1].split('/** Markdown display',1)[0]
    assert '.textContent' in block and '.innerHTML' not in block


def test_weather_production_guard_is_off_without_license(monkeypatch):
    from pathlib import Path
    s=(Path(__file__).parents[1]/'main.py').read_text()
    assert "os.getenv('HITMAN_WEATHER_PUBLIC','0') == '1'" in s


def test_research_enable_script_preserves_keys_and_refuses_production(tmp_path):
    from enable_research import configure
    env = tmp_path / '.env'
    env.write_text('APP_ENV=development\nGEMINI_API_KEY=dont-print-or-replace\nGEMINI_ENABLE_SEARCH=0\nHITMAN_AUTO_WEB_SEARCH=0\n')
    changed = configure(env)
    updated = env.read_text()
    assert 'GEMINI_API_KEY=dont-print-or-replace' in updated
    assert 'GEMINI_ENABLE_SEARCH=1' in updated
    assert 'HITMAN_PUBLIC_RESEARCH=1' in updated
    assert 'HITMAN_ENABLE_WEATHER=1' in updated
    env.write_text('APP_ENV=production\nGEMINI_API_KEY=keep\n')
    try:
        configure(env)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Research enabler must reject production changes')
    assert env.read_text() == 'APP_ENV=production\nGEMINI_API_KEY=keep\n'


def test_pro_review_passes_through_real_sources_only():
    from pro_review import run_pro_review
    class Provider:
        def __init__(self): self.responses=self;self.calls=0
        def create(self,**kwargs):
            self.calls+=1
            if self.calls==1:
                return SimpleNamespace(output_text='Fact from real results',sources=[{'url':'https://example.com/article','title':'Article'}])
            return iter([SimpleNamespace(type='response.output_text.delta',delta='Revised sourced answer')])
    provider=Provider()
    streamed=list(run_pro_review(provider,model='test',input_context=[{'role':'user','content':'updates'}],style='balanced',grounded=True))
    assert provider.calls==2
    assert streamed[0].delta=='Revised sourced answer'
    assert streamed[1].type=='response.sources'
    assert streamed[1].sources[0]['title']=='Article'
