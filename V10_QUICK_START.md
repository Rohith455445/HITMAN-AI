# HITMAN AI v10 — Install & Pro Review

This is an independent Gemini/OpenAI-API-based ChatGPT-style workspace. It cannot clone a ChatGPT Pro subscription, OpenAI proprietary models, internal tools, or unlimited quotas. Pro Review is a TWO-PASS Gemini/OpenAI API workflow.

## Windows local (Python 3.14 already installed)

1. Extract the complete ZIP. In VS Code open the **inner** folder `HITMAN-AI-v10-Pro-Workspace` (the one containing `main.py`, `requirements.txt`, `.env.example` and `static/`).
2. Run in the VS Code PowerShell terminal, while inside that folder:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

If requirements are incompatible with Python 3.14, install Python 3.12 and recreate the environment with `py -3.12 -m venv .venv`.

3. Edit `.env` (**never commit or share the actual key**). Set:

```dotenv
APP_ENV=development
COOKIE_SECURE=0
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=PASTE_YOUR_PRIVATE_API_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_REASONING_MODEL=gemini-3.5-flash-lite
HITMAN_PRO_REVIEW=1
HITMAN_PRO_PUBLIC=0
HITMAN_PRO_GROUNDING=0
HITMAN_CHAT_MAX_OUTPUT_TOKENS=3500
HITMAN_LOCAL_DOCKER_AGENT=0
```

`GEMINI_REASONING_MODEL` may be a stronger Gemini model available in your account. **The name “Pro Review” describes a two-pass process, not a proprietary model.**

4. Start the server (localhost only):

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` → mode dropdown → **Pro Review (two passes)**. Pick Concise / Balanced / Detailed. The first answer is drafted, the second API call rewrites and streams the final. Use `http://127.0.0.1:8000/studio` for AI/ML project tools.

For source ZIP testing see `V9_QUICK_START.md`; Docker is **only** for a trusted local workstation, and it remains off with `HITMAN_LOCAL_DOCKER_AGENT=0`. If needed, set to 1 and follow the separate Docker install/test instructions.

## Existing GitHub + Render Free

Extract v10 **outside** your existing cloned Git folder, then open PowerShell in its inner folder:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\path\to\your\existing\HITMAN-AI-repo"
```

The update script preserves `.git`, `.env`, local database files, virtual environments and generated projects. Check `git status --short` and `git diff` before committing. Confirm no API keys or private files have been staged. Then run `git add .`, `git commit -m "Update HITMAN AI v10 Pro Review"`, `git push origin main`.

Render Web Service build: `pip install -r requirements.txt`
Render start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Set environment variables:

```dotenv
APP_ENV=production
COOKIE_SECURE=1
PUBLIC_BASE_URL=https://hitman-ai.onrender.com
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
HITMAN_PRO_REVIEW=0
HITMAN_PRO_PUBLIC=0
HITMAN_PRO_GROUNDING=0
HITMAN_LOCAL_DOCKER_AGENT=0
HITMAN_PUBLIC_STUDIO_BUILD=0
HITMAN_PUBLIC_STUDIO_REVIEW=0
HITMAN_PUBLIC_PROJECTS=0
HITMAN_PUBLIC_REPAIR=0
```

Add a *private* `GEMINI_API_KEY` too. Use a valid `GEMINI_MODEL` and `GEMINI_REASONING_MODEL` for your API account.

**Do not enable Pro Review for anonymous public traffic until you add real user authentication, provider spending controls, and distributed rate limits.** Turning `HITMAN_PRO_REVIEW=1` and `HITMAN_PRO_PUBLIC=1` on Render explicitly permits it but incurs extra API requests and raises abuse risks. The app currently uses only single-instance best-effort quotas.

### Existing v9 features / limitations

- ChatGPT-like conversation UI, browser-local history, file PDF/image understanding, Gemini chat, optional web grounding, code assistance, Builder Studio, source ZIP analysis, templates, and local-only Docker auto-repair.
- Pro Review is not the same as ChatGPT Pro; no ChatGPT plan or GPT entitlement is transferable through this code.
- Real-time Live voice, image creation, hosted code execution and grounded research depend on separately configured API tools and model access; not enabled by default.
- Source ZIP scans are static, while local Docker testing has specific restrictions; never execute untrusted code on Render Free.
- No guaranteed factual accuracy, unrestricted autonomous computer use, or unlimited API usage.

## Local verification (no API calls)

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

`pytest` is a test dependency and may require `pip install pytest` separately; it is not required for running the application. On deployment, test `/health` first and a real chat request second.
