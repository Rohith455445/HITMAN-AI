"""Small test suite: Tavily retrieval and anonymous chat use real source URLs safely."""
from types import SimpleNamespace
from fastapi.testclient import TestClient
import main
import account_security
import research_sources as rs


def test_tavily_parses_sources_filters_unsafe_links(monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY', 'test-key')
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {'results': [
                {'title': '<b>Match report</b>', 'url': 'https://www.icc-cricket.com/news/123', 'content': '<i>Cricket update</i>'},
                {'title': 'Unsafe', 'url': 'http://localhost/admin', 'content': 'Ignore'},
                {'title': 'Duplicate', 'url': 'https://www.icc-cricket.com/news/123', 'content': 'Ignore'}]}
    class FakeClient:
        def __init__(self, *a, **kw):
            assert kw['follow_redirects'] is False
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, *, json, headers):
            assert url == rs.TAVILY_ENDPOINT
            assert headers['Authorization'] == 'Bearer test-key'
            assert json['search_depth'] == 'basic'
            assert json['time_range'] == 'day'
            assert json['include_raw_content'] is False
            return FakeResponse()
    monkeypatch.setattr(rs.httpx, 'Client', FakeClient)
    result = rs.search_tavily('today cricket updates', freshness='pd')
    assert len(result) == 1
    assert result[0]['title'] == 'Match report'
    assert result[0]['snippet'] == 'Cricket update'
    assert result[0]['url'].startswith('https://www.icc-cricket.com')


def test_chat_tavily_adds_sources_and_does_not_call_google_grounding(monkeypatch):
    # Prevent mock calls from spending shared SQLite demo rate-limit quota.
    monkeypatch.setattr(account_security, 'rate_limit', lambda *a, **kw: None)
    monkeypatch.setattr(account_security, 'quota', lambda *a, **kw: None)
    monkeypatch.setattr(main, 'PUBLIC_DEMO', True)
    monkeypatch.setattr(main, 'PUBLIC_SEARCH', True)
    monkeypatch.setattr(main, 'AUTO_WEB_SEARCH', True)
    monkeypatch.setattr(main, 'TAVILY_SEARCH', True)
    monkeypatch.setattr(main, 'BRAVE_SEARCH', False)
    monkeypatch.setattr(main, 'GOOGLE_SEARCH', False)
    monkeypatch.setattr(main, 'TEXT_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'mock')
    monkeypatch.setattr(main, 'search_tavily', lambda *a, **kw: [{
        'url': 'https://www.icc-cricket.com/news/123',
        'title': 'ICC match report', 'snippet': 'Score as reported',
        'publisher': 'icc-cricket.com', 'thumbnail': ''}])
    calls = []
    class FakeModel:
        def __init__(self, *a, **kw): self.responses = self
        def create(self, **kw):
            calls.append(kw)
            return iter([SimpleNamespace(type='response.output_text.delta', delta='According to [1], the report says ...')])
    monkeypatch.setattr(main, 'public_text_client', lambda: FakeModel())
    with TestClient(main.app) as client:
        response = client.post('/api/public/chat', json={'message': 'today cricket updates'})
        assert response.status_code == 200
        assert 'event: sources' in response.text
        assert 'ICC match report' in response.text
        assert 'According to [1]' in response.text
        assert calls and not calls[0].get('tools')
        assert 'Score as reported' in str(calls[0]['input'])
