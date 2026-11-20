from pathlib import Path
import pytest
from enable_tavily import configure


def test_local_tavily_setup_preserves_keys(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text('APP_ENV=development\nTAVILY_API_KEY=fake-test-key\nGEMINI_API_KEY=other-key\nGEMINI_ENABLE_SEARCH=1\nHITMAN_PUBLIC_RESEARCH=0\n')
    updates = configure(env)
    actual = env.read_text()
    assert updates['GEMINI_ENABLE_SEARCH'] == '0'
    assert 'GEMINI_API_KEY=other-key' in actual
    assert 'TAVILY_API_KEY=fake-test-key' in actual
    assert 'GEMINI_ENABLE_SEARCH=0' in actual
    assert 'HITMAN_PUBLIC_RESEARCH=1' in actual
    assert 'HITMAN_ENABLE_WEATHER=1' in actual
    configure(env)
    assert env.read_text().count('HITMAN_AUTO_WEB_SEARCH=') == 1


def test_tavily_setup_requires_key(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text('APP_ENV=development\nTAVILY_API_KEY=\n')
    with pytest.raises(ValueError, match='TAVILY_API_KEY'):
        configure(env)


def test_tavily_setup_refuses_production(tmp_path: Path):
    env = tmp_path / '.env'
    env.write_text('APP_ENV=production\nTAVILY_API_KEY=fake-test-key\n')
    with pytest.raises(ValueError, match='production'):
        configure(env)
