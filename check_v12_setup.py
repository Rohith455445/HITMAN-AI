"""Print safe effective-feature diagnostics without using the network or showing keys."""
from pathlib import Path
from dotenv import load_dotenv
import os

root=Path(__file__).resolve().parent
load_dotenv(root/'.env')
provider=os.getenv('HITMAN_TEXT_PROVIDER','gemini')
google=os.getenv('GEMINI_ENABLE_SEARCH','0')=='1'
brave=bool(os.getenv('BRAVE_SEARCH_API_KEY','').strip())
tavily=bool(os.getenv('TAVILY_API_KEY','').strip())
keys={'Gemini API key set':bool(os.getenv('GEMINI_API_KEY')) and os.getenv('GEMINI_API_KEY') not in {'replace_with_your_gemini_api_key','YOUR_PRIVATE_GEMINI_KEY'},
      'Guest mode':os.getenv('HITMAN_PUBLIC_DEMO')=='1',
      'Web retrieval provider configured':google or brave or tavily,
      'Automatic current-question research':os.getenv('HITMAN_AUTO_WEB_SEARCH')=='1' and (google or brave or tavily),
      'Two-pass research mode':os.getenv('HITMAN_PUBLIC_RESEARCH')=='1' and (google or brave or tavily),
      'Real weather provider':os.getenv('HITMAN_ENABLE_WEATHER')=='1',
      'Builder Studio code generation':os.getenv('HITMAN_PUBLIC_STUDIO_BUILD')=='1',
      'Local Docker agent':os.getenv('HITMAN_LOCAL_DOCKER_AGENT')=='1'}
print('HITMAN AI v12 local feature check (no network calls, no credentials displayed)')
print('Provider:',provider)
print('Research source:', 'Tavily Search' if tavily else 'Brave Search' if brave else 'Google Search grounding' if google else 'NOT CONFIGURED')
for name,enabled in keys.items():
    print(f"{'ON ' if enabled else 'OFF'} {name}")
if not google and not brave and not tavily:
    print('To enable actual research: run python enable_research.py (or configure Brave Search first).')
if os.getenv('APP_ENV','development')=='production':
    print('PRODUCTION: keep paid tools restricted; Open-Meteo free data is not licensed for commercial use.')
print('Please do not paste API secrets into screenshots or GitHub.')
