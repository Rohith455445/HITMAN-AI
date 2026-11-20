from unittest.mock import patch
import pytest
from tools.local_browser_inspect import validate_url

@patch('tools.local_browser_inspect.socket.getaddrinfo')
def test_read_only_browser_restricts_hosts_and_private_addresses(mock_dns):
    mock_dns.return_value=[(None,None,None,None,('203.0.113.1',443))]
    # Documentation/test networks are intentionally not globally routable.
    with pytest.raises(ValueError):validate_url('https://example.com',['example.com'])
    mock_dns.return_value=[(None,None,None,None,('8.8.8.8',443))]
    assert validate_url('https://example.com/docs',['example.com']).endswith('/docs')
    for url in ['http://example.com','https://127.0.0.1','https://example.com.evil.com',
                'https://user:pass@example.com','https://example.com:8080','file:///etc/passwd']:
        with pytest.raises(ValueError):validate_url(url,['example.com'])
