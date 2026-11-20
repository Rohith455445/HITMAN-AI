# HITMAN AI v7 — Update your existing Render Free web service

This guide uses your existing public repository and `https://hitman-ai.onrender.com`. It does **not** require a new Render service, new domain, or Resend for the login-free public demo.

## 1. Update existing Git source

Download and extract v7 ZIP. In VS Code, open the extracted `HITMAN-AI-v7-Advanced-Studio` folder. Run:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\Users\vvysh\Downloads\HITMAN-AI-v4-Render-Deployment\HITMAN-AI-v4-Render"
```

The target must be your actual existing Git project. Back up first; updater replaces source but skips `.git`, `.env`, `chats.db` and generated projects. Open the **target** folder, not the extracted folder:

```powershell
git status --short
git add .
git status --short
# Check staged file names and content: no .env, API keys, personal files or databases.
git commit -m "Upgrade HITMAN AI to v7 advanced studio"
git push origin main
```

## 2. Render environment — free, safe defaults

Go to Render Dashboard → existing `HITMAN-AI` web service → Environment. Keep Python build `pip install -r requirements.txt`, start `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`, Free instance. Set:

| Variable | Value |
|---|---|
| `HITMAN_PUBLIC_DEMO` | `1` |
| `APP_ENV` | `production` |
| `COOKIE_SECURE` | `1` |
| `PUBLIC_BASE_URL` | `https://hitman-ai.onrender.com` |
| `GEMINI_API_KEY` | private, rotated key from AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` if available |
| `GEMINI_REASONING_MODEL` | `gemini-3.5-flash-lite` if available |
| `HITMAN_TEXT_PROVIDER` | `gemini` |
| `HITMAN_PUBLIC_PROJECTS` | `0` |
| `HITMAN_PUBLIC_RESEARCH` | `0` |
| `HITMAN_PUBLIC_IMAGE` | `0` |
| `HITMAN_PUBLIC_REPAIR` | `0` |
| `HITMAN_PUBLIC_LIVE_VOICE` | `0` |
| `GEMINI_ENABLE_SEARCH` | `0` |
| `GEMINI_ENABLE_CODE_EXECUTION` | `0` |
| `GEMINI_ENABLE_IMAGES` | `0` |
| `ALLOW_FIRST_ADMIN_SETUP` | `0` |
| `ENABLE_DOCKER_TESTS` | `0` |
| `ENABLE_DEP_INSTALL` | `0` |

Resend/SMTP are not required in public demo mode. Never set production to development to bypass security settings. Never paste secrets into source files, GitHub or screenshots.

## 3. Deploy and test

Save Render variables, then choose **Manual Deploy → Deploy latest commit**. When Live, test:

- `https://hitman-ai.onrender.com/health` → `{"status":"ok"}`
- `https://hitman-ai.onrender.com/` → login-free chat
- Send `Hello`, test code formatting, attach a small text file, and use browser-local memory notes.

## 4. Advanced tools (optional; not guaranteed free)

Only enable one after checking API quota and model support. `HITMAN_PUBLIC_RESEARCH=1` requires `GEMINI_ENABLE_SEARCH=1`. Image generation requires `HITMAN_PUBLIC_IMAGE=1`, `GEMINI_ENABLE_IMAGES=1` and image-model access; typically a paid API model. ZIP repair uses `HITMAN_PUBLIC_REPAIR=1` and consumes large token budgets. Live voice requires `HITMAN_PUBLIC_LIVE_VOICE=1`, a Live model, and installing `requirements-voice.txt` in the build command; not end-to-end tested. Publicly exposing these without additional identity/quotas can exhaust API credits. Deep research here is a bounded two-stage grounded report, *not* ChatGPT Work or Pro Deep Research. The optional read-only computer/browser inspection script works **locally**, not on Render Free.

## 5. Limits

Render Free's disk is ephemeral and the service spins down. No persistent multi-user accounts, cloud chat history, shared workspaces or unrestricted autonomous computer control are provided by anonymous mode. The strongest ChatGPT Pro models are proprietary and/or separately billed via APIs; a ChatGPT subscription cannot fund this deployment. Do not deploy sensitive data or open unmetered guest AI endpoints publicly without abuse and billing protection.
