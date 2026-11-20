"""Explicit local-only opt-in for research settings; never prints or changes API keys."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent


def configure(path: Path, *, use_brave=False, weather=True) -> dict:
    if not path.exists():
        sample = path.with_name('.env.example')
        if not sample.exists():
            raise FileNotFoundError('Missing .env and .env.example; run from the project folder')
        shutil.copy2(sample, path)
    text = path.read_text(encoding='utf-8-sig')
    if re.search(r'^\s*APP_ENV\s*=\s*production\s*$',text,re.M):
        raise RuntimeError('Refusing to modify a production environment; change settings manually with cost controls')
    changes = {'HITMAN_AUTO_WEB_SEARCH':'1', 'HITMAN_PUBLIC_RESEARCH':'1'}
    if not use_brave:
        changes['GEMINI_ENABLE_SEARCH']='1'
    if weather:
        changes['HITMAN_ENABLE_WEATHER']='1'
        changes['HITMAN_DEFAULT_WEATHER_CITY']='Chennai, India'
    for key,val in changes.items():
        pattern = re.compile(r'^'+re.escape(key)+r'\s*=.*$',re.M)
        if pattern.search(text):
            text = pattern.sub(lambda match, key=key, val=val:key+'='+val, text)
        else:
            text += '\n'+key+'='+val+'\n'
    path.write_text(text,encoding='utf-8')
    return changes


def main():
    parser=argparse.ArgumentParser(description='Enable local live research in HITMAN AI v12 (may use paid API quota).')
    parser.add_argument('--brave',action='store_true',help='Use a pre-configured BRAVE_SEARCH_API_KEY instead of enabling Gemini Search')
    parser.add_argument('--no-weather',action='store_true',help='Do not turn on Open-Meteo personal/non-commercial weather')
    args=parser.parse_args()
    env=ROOT/'.env'
    if args.brave:
        from dotenv import dotenv_values
        if not (os.getenv('BRAVE_SEARCH_API_KEY') or dotenv_values(env).get('BRAVE_SEARCH_API_KEY')):
            raise SystemExit('BRAVE_SEARCH_API_KEY must be set in .env before using --brave')
    changed=configure(env,use_brave=args.brave,weather=not args.no_weather)
    print('Updated .env for local development (no API key printed):')
    for key,val in changed.items(): print(' ',key,'=',val)
    print('RESTART the local Uvicorn server after changing .env.')
    print('Google grounding / Brave Search may consume paid API quota.')
    print('Open-Meteo free access is for non-commercial use; production needs an appropriate licence.')

if __name__=='__main__': main()
