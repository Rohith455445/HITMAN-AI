"""Offline config diagnostic. Does not reveal API keys or call external services."""
from pathlib import Path
import os
from dotenv import load_dotenv

folder=Path(__file__).resolve().parent
load_dotenv(folder/'.env')
checks={
    'main.py present': (folder/'main.py').is_file(),
    'requirements.txt present': (folder/'requirements.txt').is_file(),
    'Gemini key configured': bool(os.getenv('GEMINI_API_KEY')) and os.getenv('GEMINI_API_KEY') not in {'YOUR_PRIVATE_API_KEY','replace_with_your_gemini_api_key'},
    'Guest chat enabled': os.getenv('HITMAN_PUBLIC_DEMO')=='1',
    'Gemini text provider selected': os.getenv('HITMAN_TEXT_PROVIDER','gemini').lower()=='gemini',
    'Search grounding enabled': os.getenv('GEMINI_ENABLE_SEARCH')=='1',
    'Automatic fresh-question research': os.getenv('GEMINI_ENABLE_SEARCH')=='1' and os.getenv('HITMAN_AUTO_WEB_SEARCH')=='1',
    'Two-pass research enabled': os.getenv('HITMAN_PUBLIC_RESEARCH')=='1' and os.getenv('GEMINI_ENABLE_SEARCH')=='1',
    'Builder generation enabled': os.getenv('HITMAN_PUBLIC_STUDIO_BUILD')=='1',
}
print('HITMAN AI v11 — local setup checks (no API requests)')
for label,ok in checks.items():
    print(f"{'OK' if ok else 'OFF'}  {label}")
print('Environment:', os.getenv('APP_ENV','development'))
print('Model:', os.getenv('GEMINI_MODEL','(not set)'))
print('Do not share .env or API keys. See V11_READ_THIS_FIRST.md.')
