r"""Configure HITMAN AI v12 for local Tavily-assisted research without exposing keys.

Run after filling TAVILY_API_KEY in .env:
    .\.venv\Scripts\python.exe enable_tavily.py

No API calls are made by this script. It does not edit GEMINI_API_KEY or
TAVILY_API_KEY. Never run it on a production environment.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
SWITCHES = {
    'APP_ENV': 'development',
    'HITMAN_PUBLIC_DEMO': '1',
    'HITMAN_TEXT_PROVIDER': 'gemini',
    'GEMINI_ENABLE_SEARCH': '0',
    'HITMAN_AUTO_WEB_SEARCH': '1',
    'HITMAN_PUBLIC_RESEARCH': '1',
    'COOKIE_SECURE': '0',
}


def configure(path: Path, weather: bool = True) -> dict[str, str]:
    sample = path.with_name('.env.example')
    if not path.exists():
        if not sample.exists():
            raise FileNotFoundError('Missing .env.example in the HITMAN AI project folder')
        shutil.copy2(sample, path)
    current = dotenv_values(path)
    if current.get('APP_ENV', '').strip().lower() == 'production':
        raise ValueError('Refusing to modify a production .env file')
    api_key = (current.get('TAVILY_API_KEY') or '').strip()
    if not api_key or api_key.lower().startswith(('your_', 'replace_', 'paste_')):
        raise ValueError('Add your private TAVILY_API_KEY to .env, then rerun this script')
    changes = dict(SWITCHES)
    if weather:
        changes['HITMAN_ENABLE_WEATHER'] = '1'
    content = path.read_text(encoding='utf-8-sig')
    for name, value in changes.items():
        pattern = re.compile(r'^\s*' + re.escape(name) + r'\s*=.*$', re.M)
        new_line = name + '=' + value
        if pattern.search(content):
            content = pattern.sub(lambda match, line=new_line: line, content)
        else:
            content += '\n' + new_line + '\n'
    path.write_text(content, encoding='utf-8')
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description='Configure local Tavily search for HITMAN AI v12')
    parser.add_argument('--no-weather', action='store_true', help='Do not enable local Open-Meteo weather')
    args = parser.parse_args()
    try:
        changes = configure(ROOT / '.env', weather=not args.no_weather)
    except (ValueError, FileNotFoundError) as exc:
        print('Setup not completed:', exc)
        return 1
    print('HITMAN AI Tavily research enabled locally (no API keys displayed).')
    for name, value in changes.items():
        print(f'  {name}={value}')
    print('Restart Uvicorn if it is running. Then run check_v12_setup.py.')
    print('Search and AI usage may be subject to your providers\' free quotas or charges.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
