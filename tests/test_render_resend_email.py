"""Offline smoke tests for Resend HTTPS email transport."""
import json
import urllib.error
from unittest.mock import patch
import pytest
import account_security
from account_security import send_email as original_send_email

class StubResponse:
    status=200
    def __enter__(self): return self
    def __exit__(self, *_): return False

def test_resend_sends_https_not_smtp(monkeypatch):
    monkeypatch.setenv('EMAIL_TRANSPORT','resend')
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('RESEND_API_KEY','re_fake_test')
    monkeypatch.setenv('RESEND_FROM','verify@example.com')
    with patch('account_security.urllib.request.urlopen', return_value=StubResponse()) as urlopen:
        original_send_email('test@example.com','Verify','Verification link')
    req=urlopen.call_args.args[0]
    assert req.full_url=='https://api.resend.com/emails'
    assert req.get_header('Authorization')=='Bearer re_fake_test'
    body=json.loads(req.data.decode())
    assert body['to']==['test@example.com']
    assert body['text']=='Verification link'

def test_resend_rejects_missing_credentials(monkeypatch):
    monkeypatch.setenv('EMAIL_TRANSPORT','resend')
    monkeypatch.delenv('RESEND_API_KEY',raising=False)
    monkeypatch.delenv('RESEND_FROM',raising=False)
    with pytest.raises(RuntimeError,match='RESEND_API_KEY'):
        original_send_email('test@example.com','Verify','text')

def test_provider_errors_do_not_leak_email_tokens(monkeypatch):
    monkeypatch.setenv('EMAIL_TRANSPORT','resend')
    monkeypatch.setenv('RESEND_API_KEY','re_fake_test')
    monkeypatch.setenv('RESEND_FROM','verify@example.com')
    with patch('account_security.urllib.request.urlopen',side_effect=urllib.error.URLError('offline')):
        with pytest.raises(RuntimeError,match='HTTPS email delivery failed') as err:
            original_send_email('test@example.com','Verify','SECRET_TOKEN')
    assert 'SECRET_TOKEN' not in str(err.value)
