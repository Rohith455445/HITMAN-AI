# HITMAN AI v11 — Research + Attachment Fix

This release fixes verified bugs in the v10 guest-chat integration. It does **not** reproduce OpenAI's proprietary ChatGPT Pro models, plan benefits, connected apps, or proprietary computer-use services. All external AI operations require your own API key, eligible model, and applicable quota/billing.

## 1. Correct Windows folder (Python 3.14)

**The full ZIP contains project files at the top level.** Extract it into a folder (for example `Downloads\HITMAN-AI-v11-Research-Fix-Full`) and open that folder in VS Code. Verify that `main.py`, `requirements.txt`, and `.env.example` are in the CURRENT terminal directory:

```powershell
Get-Location
Test-Path .\main.py
Test-Path .\requirements.txt
Test-Path .\.env.example
py -3.14 --version
```

All three `Test-Path` commands should return `True`. If not, run `Get-ChildItem -Recurse -Filter main.py` and `cd` to the folder containing that file.

Then:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

If dependencies fail on Python 3.14, use a compatible Python runtime such as 3.12 rather than trying to suppress package errors.

## 2. Enable *real* research (personal local development)

In `.env`, use **one occurrence** of each variable (delete duplicated definitions). Never paste an API key into chat, screenshots, GitHub, or ZIPs.

```dotenv
APP_ENV=development
COOKIE_SECURE=0
PUBLIC_BASE_URL=http://127.0.0.1:8000
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=YOUR_PRIVATE_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_REASONING_MODEL=gemini-3.5-flash-lite

# Set these to 1 to invoke Gemini's ACTUAL Google Search grounding API.
# Access and billing depend on your Gemini API account.
GEMINI_ENABLE_SEARCH=1
HITMAN_AUTO_WEB_SEARCH=1
HITMAN_PUBLIC_RESEARCH=1

# Optional: two-pass answer review + AI/ML Builder Studio tools.
HITMAN_PRO_REVIEW=1
HITMAN_PRO_PUBLIC=0
HITMAN_PUBLIC_STUDIO_BUILD=1
HITMAN_PUBLIC_STUDIO_REVIEW=1
HITMAN_PUBLIC_PROJECTS=1
HITMAN_PUBLIC_REPAIR=0
HITMAN_LOCAL_DOCKER_AGENT=0

# Local file limits. Public production stays 1.2 MB per file / 250 KB ZIP.
HITMAN_LOCAL_ATTACHMENT_BYTES=4000000
HITMAN_LOCAL_ZIP_BYTES=2000000
```

The Gemini API may reject grounding with certain models/accounts, or charge for usage. An API key alone does not guarantee Search eligibility. If research fails, read the banner in chat and examine your terminal for backend errors; choose a supported model and check your Google AI Studio usage/billing status. **Never invent current facts when grounding is unavailable.**

## 3. Start and verify

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and refresh the tab with Ctrl+Shift+R. The app should show a visible **Live web grounding enabled** status when both Search flags are set. Check http://127.0.0.1:8000/api/config and verify:

- `features.web_search: true`
- `features.auto_web_search: true`
- `features.deep_research: true` (when `HITMAN_PUBLIC_RESEARCH=1`)
- `max_attachment_mb: 4.0`
- `max_zip_mb: 2.0`

Try:

1. `Today cricket updates in India, with sources and match dates.`
2. `Give updates` (same conversation; this is a grounded follow-up).
3. Attach a small PDF **without typing a message**, click Send, and ask follow-up questions.
4. Attach a scanned PDF (up to 12 pages). Gemini receives its native document bytes; actual vision results depend on your model.
5. Attach a small `.zip` containing source code and ask for an analysis. This scans selected text files as **untrusted data**; it does not run them.
6. Open http://127.0.0.1:8000/studio to build/download source projects, run static scans, or request Gemini code review. Local Docker testing is a separate, off-by-default workflow.

### If a tool is missing

- Research controls hidden: `GEMINI_ENABLE_SEARCH=0` or service not restarted.
- Fresh questions still reply without sources: check `/api/config` for `auto_web_search=true`; the provider may have rejected search. Do not trust a model's claims to have browsed without actual grounded citations.
- Error 400/404 from Gemini: your model or API may not support the specific tool.
- Error 429: quota or rate limits; you must resolve them with your provider.
- Image generation / two-way live voice: require separate enabled models/tools; not part of this fix and not guaranteed by Render Free.
- File upload fails: read the exact backend error; check size, file type, and whether it's password-protected. Public deployment has smaller limits.

## 4. Upgrade the EXISTING GitHub repo and Render

If you want to update your existing repo rather than replace it, extract the full ZIP separately and run `UPDATE_EXISTING.ps1` **from the extracted v11 project folder**:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\path\to\your\existing\HITMAN-AI-repo"
```

This leaves `.git`, `.env`, local databases, and `.venv` untouched. Inspect `git status --short`, ensure keys/secrets are not staged, then commit and push.

For Render Free, keep the following *safe defaults* until you add login/identity, a database, abuse controls, spending limits and tested API entitlements:

```dotenv
APP_ENV=production
COOKIE_SECURE=1
PUBLIC_BASE_URL=https://hitman-ai.onrender.com
HITMAN_PUBLIC_DEMO=1
GEMINI_ENABLE_SEARCH=0
HITMAN_AUTO_WEB_SEARCH=0
HITMAN_PUBLIC_RESEARCH=0
HITMAN_LOCAL_DOCKER_AGENT=0
HITMAN_PUBLIC_STUDIO_BUILD=0
HITMAN_PUBLIC_STUDIO_REVIEW=0
HITMAN_PUBLIC_PROJECTS=0
HITMAN_PRO_REVIEW=0
HITMAN_PRO_PUBLIC=0
```

Use Render Environment for `GEMINI_API_KEY`. **If you choose to enable grounding on a public deployment** (`GEMINI_ENABLE_SEARCH=1`, `HITMAN_AUTO_WEB_SEARCH=1`), account/billing limits and malicious traffic can consume quota. Current single-instance request limits are not production-grade. A live deployment cannot be verified using this ZIP alone.

## 5. What was tested

`python -m pytest -q` and `node --check static/app.js` should pass. The regression suite uses mocked AI responses to check search routing, follow-ups, streamed status messages, PDF payload shape, ZIP validation, and file submission code. A headless browser run was blocked by this testing environment (ERR_BLOCKED_BY_ADMINISTRATOR); it was not counted as a successful UI test. It does not make live Gemini requests or prove correctness of sports scores, image generation, voice, or autonomous computer actions.
