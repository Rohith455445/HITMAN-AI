# HITMAN AI v12 — Complete Project with Tavily Search

This is the **full HITMAN AI v12 source** with the Tavily integration merged. It is **not** a patch. No previous HITMAN AI installation is required.

## Included

- Login-free Gemini chat, code assistance and ChatGPT-style Markdown display
- Automatic time-sensitive web research using Tavily (once keys and credits are configured), with cited provider URLs
- Optional Brave Search and Gemini Google Search grounding, subject to their separate terms/quotas
- PDF, image, source file and source ZIP understanding within configured size limits
- Weather from Open-Meteo (optional; free endpoint is restricted to noncommercial use)
- Builder Studio for AI/ML, API, web app, bots, and data projects; optional AI review
- Local browser notes and conversation history, Pro Review, optional local-only Docker repair and other earlier v12 features

**Limits:** This isn't ChatGPT Pro and does not grant access to proprietary ChatGPT tools. Tavily retrieves search evidence, while Gemini generates the answer; both provider requests can fail independently. Search snippets should not be treated as guaranteed verified full-article facts. No real Tavily/Gemini requests were made in offline testing.

## 1. Install on Windows with Python 3.14

Extract the ZIP, then **open the inner `HITMAN-AI-v12-Tavily-Complete` folder** in VS Code — the folder that contains `main.py` and `requirements.txt`. In that folder's PowerShell terminal:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Set your **own private** keys in `.env`:

```dotenv
GEMINI_API_KEY=PASTE_YOUR_GEMINI_KEY_HERE
TAVILY_API_KEY=PASTE_YOUR_TAVILY_KEY_HERE
GEMINI_MODEL=your_supported_gemini_model
```

Obtain a Tavily key at https://app.tavily.com and a Gemini key at https://aistudio.google.com/apikey. The `GEMINI_MODEL` value must be an actual model your Gemini API account can use. Keep the other settings in `.env.example` unchanged until setup is successful. Never upload `.env` to GitHub.

## 2. Enable Tavily instead of potentially paid Google Search grounding

**After saving the real Tavily key** in `.env`, run:

```powershell
.\.venv\Scripts\python.exe enable_tavily.py
.\.venv\Scripts\python.exe check_v12_setup.py
```

`enable_tavily.py` sets `GEMINI_ENABLE_SEARCH=0`, `HITMAN_AUTO_WEB_SEARCH=1`, `HITMAN_PUBLIC_RESEARCH=1`, guest mode, and local development settings, **without changing or displaying either API key**. It also enables personal/noncommercial weather by default. Use `--no-weather` to leave weather off. **Do not run the old `enable_research.py` after this**, because that script enables Gemini Google Search grounding by default.

Expected configuration includes:

```text
Research source: Tavily Search
ON  Gemini API key set
ON  Automatic current-question research
ON  Two-pass research mode
```

This configuration checker makes **no network calls**. It does not verify that Tavily or Gemini accepts your key.

## 3. Start HITMAN AI

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for chat and http://127.0.0.1:8000/studio for Builder Studio. Start a new chat and ask `today cricket updates with sources`, then `give updates`. Try attaching a PDF or source ZIP.

To enable local AI-assisted project builds in `.env`:

```dotenv
HITMAN_PUBLIC_STUDIO_BUILD=1
HITMAN_PUBLIC_STUDIO_REVIEW=1
```

Restart the server after editing `.env`. These switches may consume additional Gemini quota. Never enable local Docker test execution on an internet-facing server.

## 4. If chat fails while search appears enabled

The Tavily API and Gemini API are **two independent services**. Tavily can return website links even if Gemini refuses to generate an answer. Run the bundled Gemini diagnostic:

```powershell
.\.venv\Scripts\python.exe diagnose_hitman_gemini_v12.py
```

The diagnostic does not print keys, and by default does **not** call Google Search grounding. It distinguishes basic Gemini success from model, permission, or quota errors. If basic Gemini requests fail, check the configured model and Google AI Studio usage limits. **Do not post your API key or full `.env` file.**

If Tavily fails, verify your key/credits and internet connection at https://app.tavily.com. Check the terminal for the error and send only redacted logs.

## 5. Existing GitHub / Render Free service

You can deploy this complete project using the existing `requirements.txt`, `render.yaml` and Render start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

For public deployment, keep `APP_ENV=production`, `COOKIE_SECURE=1`, `HITMAN_LOCAL_DOCKER_AGENT=0`. Put keys in Render **Environment** (not GitHub). Leave anonymous expensive tools off until you have strong authentication and rate/cost controls. Browser-local chat history is not cross-device synced; Render Free storage isn't a durable database. If you enable web research in production, check Tavily usage terms and enforce strict quotas.

## Verification

The merged v12 project and Tavily integration were tested using mocked network/model responses. This **does not verify live searches, AI answer quality, an end-user Windows install, or a Render deployment**.
