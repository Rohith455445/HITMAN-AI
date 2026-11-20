# Deploy HITMAN AI v5 — existing Render Free service

## 1. Back up and update your local source

Extract this ZIP. It contains the complete app, including `main.py`, `gemini_bridge.py`, `workspace.py`, `account_security.py`, `static/`, `tests/`, `.env.example`, and `render.yaml`.

**Important:** If updating your current Git repository, copy the code files into the folder that contains the `.git` directory. Do NOT copy an old `.env` into GitHub. If using an already-created account/database on Windows, leave your existing `chats.db` alone. Never push a database or credentials.

### Simple update command for your existing repository

In PowerShell, **open the extracted v5 folder containing `UPDATE_EXISTING.ps1`**. Then run this signed/local-script-aware command after reviewing the script:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\Users\vvysh\Downloads\HITMAN-AI-v4-Render-Deployment\HITMAN-AI-v4-Render"
```

If your PowerShell policy blocks scripts, instead copy `main.py`, `gemini_bridge.py`, backend `.py` modules, `render.yaml`, and the `static` and `tests` folders using VS Code's file explorer. Keep your existing `.env`, `chats.db`, `.git`, `.venv`, and generated projects. Do **not** change the Windows execution policy globally just for this update.

The update script validates that your target contains `main.py` and `.git`, and it does not remove or overwrite local credentials or databases.

## 2. Git commands (PowerShell in your Git repository root)

```powershell
git status --short
git check-ignore .env
git add .
git status --short
# Only continue after checking no credentials, .env or DB are staged.
git commit -m "Upgrade HITMAN AI to complete no-login v5"
git push origin main
```

If `git check-ignore .env` outputs nothing because the file does not exist, this is normal. Check `.gitignore` and `git status --short` anyway.

## 3. Render → HITMAN-AI → Environment

Keep or set these exact variables in the Render dashboard (one key/value per row):

| KEY | VALUE |
| --- | --- |
| `HITMAN_PUBLIC_DEMO` | `1` |
| `APP_ENV` | `production` |
| `COOKIE_SECURE` | `1` |
| `PUBLIC_BASE_URL` | `https://hitman-ai.onrender.com` |
| `GEMINI_API_KEY` | Your **new, private** Google AI Studio key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` (only if available in your project) |
| `GEMINI_REASONING_MODEL` | `gemini-3.5-flash-lite` (only if available) |
| `GEMINI_ENABLE_SEARCH` | `0` |
| `GEMINI_ENABLE_CODE_EXECUTION` | `0` |
| `GEMINI_ENABLE_IMAGES` | `0` |
| `ENABLE_DOCKER_TESTS` | `0` |
| `ENABLE_DEP_INSTALL` | `0` |
| `ALLOW_FIRST_ADMIN_SETUP` | `0` |

You **do not need Resend** when `HITMAN_PUBLIC_DEMO=1`. Remove `EMAIL_TRANSPORT`, `RESEND_API_KEY`, and `RESEND_FROM` if they are unused. Login and verification routes are blocked in public demo mode.

Keep your Gemini key in Render, **never in GitHub or screenshots**. Rotate any keys previously exposed in screenshots.

## 4. Render deployment settings

- Service: your existing `HITMAN-AI` **Web Service**, instance **Free**
- Branch: `main`, Root directory: blank if `main.py` is in repo root
- Build: `pip install -r requirements.txt`
- Start: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Save Environment changes, then choose **Manual Deploy → Deploy latest commit** if needed.

Expected health check: `https://hitman-ai.onrender.com/health` → `{"status":"ok"}`. When the service is `Live`, open `https://hitman-ai.onrender.com/` and send `Hello`.

## 5. How to confirm no login

- `/` should open HITMAN AI immediately.
- `/login` and `/signup` should redirect to `/` in demo mode.
- `GET /api/config` should return `"public_demo":true`.
- Anonymous visitors **cannot** use saved user accounts, workspaces, memory or file APIs.
- Browser-local chat is stored only in localStorage; users can delete it in the sidebar.

## 6. Local VS Code preview on Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
# Enter your Gemini API key and keep HITMAN_PUBLIC_DEMO=1
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/`.

## Caveats

This is a **chat-only guest demo**, not a complete clone of ChatGPT Pro. Code assistance means explaining and generating text; downloadable project ZIPs, file analysis and private coding agents are deliberately disabled without accounts. Free Render loses filesystem data whenever the instance restarts or spins down; API rate limits in local SQLite reset. The app rate limits to 12 requests per 15 minutes per observed IP and 60 total requests per UTC day **per running instance**; these are best-effort and can be bypassed by determined abuse. Configure stronger gateway protection before broad public use.
