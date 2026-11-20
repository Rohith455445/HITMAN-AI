# HITMAN AI v6 → Render Free — update your existing website

This guide upgrades your existing public website `https://hitman-ai.onrender.com` without creating a second Render service.

## A. Update existing source in VS Code

1. Extract `HITMAN-AI-v6-Gemini-Studio.zip`.
2. Open the extracted project folder. In its terminal run (adapt the target only if your clone is elsewhere):

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\Users\vvysh\Downloads\HITMAN-AI-v4-Render-Deployment\HITMAN-AI-v4-Render"
```

If scripts are blocked, manually copy `main.py`, `public_tools.py`, `gemini_bridge.py`, `static/app.js`, `static/index.html`, `static/styles.css`, the test files and `render.yaml` into your current Git clone. **Do not overwrite `.env`, `chats.db`, `.git`, or private user files.**

3. Open the **target** folder in VS Code. Verify staged files, then push:

```powershell
git status --short
git add main.py public_tools.py static/app.js static/index.html static/styles.css render.yaml .env.example tests README.md DEPLOY_V6_RENDER_FREE.md
git status --short
git commit -m "Upgrade HITMAN AI to Gemini Studio v6"
git push origin main
```

If you changed additional source files, review them individually before adding. **Never commit API keys, `.env`, user account databases, or session tokens.**

## B. Render environment

Open Render Dashboard → your existing `HITMAN-AI` web service → Environment. Set:

| Key | Value |
|---|---|
| `HITMAN_PUBLIC_DEMO` | `1` |
| `HITMAN_PUBLIC_PROJECTS` | `0` (default: protects Gemini quota) |
| `APP_ENV` | `production` |
| `COOKIE_SECURE` | `1` |
| `PUBLIC_BASE_URL` | `https://hitman-ai.onrender.com` |
| `GEMINI_API_KEY` | **your private key** (never commit or screenshot) |
| `GEMINI_MODEL` | a model available to your account; example `gemini-3.5-flash-lite` |
| `GEMINI_REASONING_MODEL` | a model available to your account; example `gemini-3.5-flash-lite` |
| `GEMINI_ENABLE_SEARCH` | `0` |
| `GEMINI_ENABLE_CODE_EXECUTION` | `0` |
| `GEMINI_ENABLE_IMAGES` | `0` |
| `ALLOW_FIRST_ADMIN_SETUP` | `0` |
| `ENABLE_DOCKER_TESTS` | `0` |
| `ENABLE_DEP_INSTALL` | `0` |

Remove `RESEND_API_KEY`, `RESEND_FROM` and `EMAIL_TRANSPORT` **only if you will use anonymous demo mode exclusively**. Don't change `APP_ENV` to `development` on Render.

## C. Deploy and verify

Render → Manual Deploy → Deploy latest commit. Check latest logs for `Application startup complete`. Open:

- `https://hitman-ai.onrender.com/health` → `{"status":"ok"}`
- `https://hitman-ai.onrender.com/` → the login-free chat UI
- Send `Hello` and test basic coding help.
- Attach a small `.txt` file and ask for a summary; it should be analyzed without requiring a login.
- Memory menu → save a note and confirm it appears in a later conversation on the **same browser**.

## D. Optional testing: downloadable project ZIPs

`HITMAN_PUBLIC_PROJECTS=1` exposes `/api/public/project` to anonymous users, which can consume substantial Gemini quota. **Do not enable on an unrestricted public website without authentication, stronger rate limits, per-user quotas and abuse monitoring.** For local controlled testing, set the flag in `.env`, restart and use Tools → Build project.

## E. Free service limitations

Render Free may spin down during inactivity and its filesystem is ephemeral. The frontend stores its conversation history in browser localStorage, not a durable cross-device cloud database. Gemini API model/tool quota and pricing are separate from ChatGPT Pro. This build is not a production-ready multi-user ChatGPT clone.
