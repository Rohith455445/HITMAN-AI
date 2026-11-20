# HITMAN AI v12 — Researched Answers & Source Cards

This is an **additive update of the full HITMAN AI v11 project**. Existing account routes, guest chat, Builder Studio, PDF/image/source attachments, optional project builder, code review, Docker local repair, live-voice integrations, Pro Review and existing configuration switches are retained. No unrelated features were intentionally removed.

## Problems fixed

- Time-sensitive questions such as `today cricket updates`, `latest cricket news`, and follow-ups like `give updates` can automatically use a **real search provider**, instead of relying on Gemini's offline knowledge.
- Gemini Search grounding links are surfaced as source cards, with titles from the provider. If Google does not return source metadata, the answer explicitly warns that it is not independently verified.
- Optional **Brave Search API** retrieval can supply cited web snippets when Gemini Search grounding is not supported by the chosen model/account. Brave needs a separate API key and may have costs.
- Real Open-Meteo forecasts can be displayed as an hourly and daily **weather card**, with time, city and attribution. Weather numbers come from the provider response, not model guesses. The free Open-Meteo API is non-commercial only, so use a properly licensed plan for commercial/public use.
- Research source cards can display a returned thumbnail, source title, snippet and linked publisher. **No fake score, news event, image or link is inserted.** Some providers return no thumbnails.
- Browser-local history preserves the source cards and weather results when opening an existing chat.
- All earlier v11 attachment fixes are included: bounded source ZIPs, PDFs including scanned PDFs with Gemini document input, images, and send-a-file-without-typing.

**Important:** This doesn't grant a ChatGPT Pro subscription or proprietary ChatGPT tools. Actual web results need internet connectivity and a supported, quota-enabled provider. A backend with no search API access cannot truthfully return live match scores.

## Windows setup (Python 3.14)

1. Extract `HITMAN-AI-v12-Research-Workspace-Full.zip`.
2. In VS Code open the **inner folder containing `main.py` and `requirements.txt`**. Don't run commands in the outer downloaded folder.
3. Open PowerShell in that inner folder and run:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Set `GEMINI_API_KEY` to your newly issued private key, and configure `APP_ENV=development`, `COOKIE_SECURE=0`, `HITMAN_PUBLIC_DEMO=1`, and `HITMAN_TEXT_PROVIDER=gemini`.

**Enable research explicitly.** The following command changes only local `.env` feature switches; it never prints or replaces API keys:

```powershell
.\.venv\Scripts\python.exe enable_research.py
```

This turns on Gemini Search grounding, automatic current-question routing, multi-pass research, and personal/noncommercial Open-Meteo weather. **Some Gemini Search calls may be billed**. It doesn't unlock a provider feature your key/model doesn't support. If your Gemini account rejects Google grounding, configure your own `BRAVE_SEARCH_API_KEY` in `.env`, then run:

```powershell
.\.venv\Scripts\python.exe enable_research.py --brave
```

For local AI project generation, you can additionally set `HITMAN_PUBLIC_STUDIO_BUILD=1` and `HITMAN_PUBLIC_STUDIO_REVIEW=1`. Only enable local Docker repair if you have Docker Desktop and accept the isolation limitations.

**Check settings, then run**:

```powershell
.\.venv\Scripts\python.exe check_v12_setup.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 . Start a *new chat* and test:

- `today cricket updates` — the app should either give web-source-backed updates or report an API/provider issue, not fabricate live scores.
- `give updates` — continues a current-information chat using earlier context.
- `today weather updates` — uses the explicitly configured city, currently `Chennai, India`; or ask `weather in Mumbai` to choose a city.
- `Research recent AI agent tool-use architectures and cite sources` — uses Google Search grounding or Brave search results.
- Attach a small PDF, JPG/PNG, `.py` or source ZIP. Ask for an explanation or code review.

After changing `.env`, **stop and restart Uvicorn**. `--reload` may not restart automatically on `.env` edits.

## Render Free

Do not enable code execution, untrusted uploads for autonomous execution, or the local Docker agent on a public Render server. The existing `render.yaml` keeps high-cost integrations **OFF**. For a private/controlled web research demo, set `GEMINI_ENABLE_SEARCH=1`, `HITMAN_AUTO_WEB_SEARCH=1` and (if desired) `HITMAN_PUBLIC_RESEARCH=1`, or add a private `BRAVE_SEARCH_API_KEY` and set the auto-search flag. Configure quotas, authentication, throttling and spend limits before opening a public AI search service. The in-process/SQLite rate limits are not strong distributed protection.

`HITMAN_ENABLE_WEATHER=1` is opt-in. The free Open-Meteo service is licensed for **non-commercial** usage; don't enable it on a commercial site without the proper plan and attribution. The app defaults `HITMAN_WEATHER_PUBLIC=0` in production.

This ZIP does not include your `.env` or API keys. Do not commit `.env` or share screenshots exposing keys. Existing Render or VS Code project can be updated using `UPDATE_EXISTING.ps1`, after backing up the original repository. You can also replace only the files from the patch ZIP, keeping `.env` and `.git` untouched.

## What was verified

- Existing and new Python test suite with fake HTTP/AI provider data; source sanitization and attribution assertions.
- Python compilation, JavaScript syntax and ZIP archive integrity.

**Not verified:** live Gemini Search, Brave Search, Open-Meteo network calls, browser/Chromium UI under your Windows installation, or deployment to your Render account. Test your own API entitlements and logs; no untested source should be claimed to produce the same output as ChatGPT Pro.
