# HITMAN AI v4 Gemini — Publish on Render

## Before proceeding

- This bundle includes `render.yaml` configured for a **PAID Render web service plus a persistent disk**. Review estimated costs in the Render dashboard before creating anything.
- The source uses **SQLite for accounts, sessions, chat history, memory and workspace files**, plus local ZIP artifacts. That is why persistent disk storage is required. Render's free web service is **not suitable for public user accounts on this current architecture**: storage resets and outbound SMTP on ports 25/465/587 is blocked.
- The app has not undergone a formal external security audit. For unrestricted public traffic, add monitoring, backups, abuse protection, secure review of AI-generated code and a scalable database architecture. Avoid enabling Docker tests on this web server.
- Gemini's free tier is separately metered and rate-limited; your Render plan is separate and can incur charges.

## Step 1: Upload the source to GitHub (without secrets)

Extract the ZIP. Open **the folder containing `main.py`, `requirements.txt`, and `render.yaml`** in VS Code. Do not upload `.env`, `chats.db`, `.venv`, or `generated_projects`. `.gitignore` excludes these.

Recommended: create a new **private** GitHub repository, e.g. `hitman-ai-gemini`. In VS Code: **Source Control → Initialize Repository → Stage → Commit → Publish Branch**. Or use these commands if Git is installed, after creating a blank remote repository:

```powershell
git init
git add .
git commit -m "Prepare HITMAN AI for Render"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Never put a real `GEMINI_API_KEY`, SMTP password, GitHub token, or encryption key in the repository.

## Step 2: Create the Render service

1. Sign in at https://dashboard.render.com and connect GitHub.
2. Choose **New → Blueprint**, select the repository containing the `render.yaml` file.
3. Review the paid service and disk costs. The Blueprint configures the Python web service with a persistent volume at `/var/data`, and the FastAPI server at the Render-assigned `$PORT`.
4. Render will ask for secret values marked `sync: false`. Enter these **only in Render's UI**:

| Key | Value |
| --- | --- |
| `GEMINI_API_KEY` | Your Gemini API key from Google AI Studio |
| `PUBLIC_BASE_URL` | Your assigned HTTPS URL, e.g. `https://hitman-ai-gemini.onrender.com`, **no trailing slash** |
| `SMTP_HOST` | Your real transactional SMTP server |
| `SMTP_FROM` | Verified sender email address |
| `SMTP_USERNAME` | SMTP provider login |
| `SMTP_PASSWORD` | SMTP provider password or token |

`PUBLIC_BASE_URL` must equal your actual Render public URL **exactly** (the host may have a numeric suffix if the requested name is taken). If you do not know the URL yet, set a placeholder HTTPS URL during creation, then **update `PUBLIC_BASE_URL` in the Render service Environment page before testing signups**. This is important for CSRF origin checks and account email links.

> Gmail App Password SMTP may be unsuitable for production transaction volume; use a verified transactional SMTP sender. Free Render blocks standard SMTP ports, so the Blueprint explicitly uses paid compute.

### Manual web-service route (without Blueprint)

Choose **New → Web Service → Connect GitHub**, set Runtime Python, Build Command `pip install -r requirements.txt`, Start Command `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`, Health Check Path `/health`, Python version 3.12. Choose a paid plan with 1 GB persistent disk mounted at `/var/data`. Add the same environment variables listed in `render.yaml` plus SMTP secrets, Gemini key, and actual public HTTPS URL.

## Step 3: Deploy and test

- Click Deploy. Watch **Events / Logs** for build errors or startup failures.
- Visit `https://YOUR-APP.onrender.com/health` → `{"status":"ok"}`.
- Visit `/signup`, register a fresh account, check for a real verification email, then sign in and test the Chat page.
- Project creation and chat features require valid Gemini credentials and available API quota.
- New Render database starts empty. Your existing local account and chats **will not migrate automatically**. Keep a backup of local `chats.db`; do not upload it to a public Git repo.

## Troubleshooting

- **No email received**: Check SMTP settings, provider sender verification, logs, and spam folder; make sure the provider accepts connections on port 587 from the paid instance.
- **403 Cross-origin request blocked**: Set `PUBLIC_BASE_URL` to the exact `https://...onrender.com` service origin, without a trailing slash.
- **No chat**: Check the backend logs, Gemini key validity and free-tier quota/rate limits.
- **App starts but data disappears**: The persistent disk is missing or the `DATABASE_PATH`/`PROJECT_STORAGE_PATH` variables are wrong.
- **Import or build failures**: Verify `requirements.txt` and `.python-version` are at the connected service's repository root.
- **Web service not accessible**: Check that the start command uses `--host 0.0.0.0 --port $PORT` (not localhost).
- **Admin**: `ALLOW_FIRST_ADMIN_SETUP` is disabled for safety. Public signups create normal member accounts; set up an admin using an authorized administrative method, not an internet-accessible bootstrap endpoint.

## Security notes

This is a deployment configuration, not an audited production release. Before broad public launch, implement proper backups, monitoring, distributed rate limiting if scaling beyond a single instance, API spend protection and abuse detection, and a hardened sandbox for untrusted code. A Render web service is not itself a secure arbitrary code-execution environment. Avoid running user code on the host.

Official docs: https://render.com/docs/deploy-fastapi , https://render.com/docs/disks , https://render.com/docs/free , https://render.com/docs/blueprint-spec
