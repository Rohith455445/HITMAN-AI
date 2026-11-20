# HITMAN AI: Render Free startup fix (Resend HTTPS)

This release fixes the exact startup exception from the Render logs:

`RuntimeError: Production requires SMTP email verification`

Only **main.py** and **account_security.py** were changed. It adds an alternative
production email transport `resend` using HTTPS (no SMTP port). Verification and
password-reset links still use one-time tokens. No secrets are included.

## Apply to your existing public GitHub repo

1. Back up your local project.
2. Replace `main.py` and `account_security.py` with the two supplied files.
3. In the VS Code terminal, from your Git repository root:

```powershell
py -3.12 -m py_compile main.py account_security.py
git add main.py account_security.py
git commit -m "Support HTTPS verification emails on Render Free"
git push origin main
```

4. In Render Dashboard > HITMAN-AI > Environment, set:

| Key | Value |
|---|---|
| APP_ENV | production |
| COOKIE_SECURE | 1 |
| EMAIL_TRANSPORT | resend |
| RESEND_API_KEY | Create privately on Resend |
| RESEND_FROM | HITMAN AI <verify@YOUR_VERIFIED_DOMAIN> |
| PUBLIC_BASE_URL | https://YOUR-EXACT-RENDER-URL.onrender.com |
| GEMINI_API_KEY | Your newly rotated Gemini secret |

Resend needs a verified sending domain for emails to arbitrary users. Its testing domain is not a substitute for production domain verification.

5. Render > Manual Deploy > Deploy latest commit; check `/health`.

## Important limits — not production ready yet

* **Render Free disk is ephemeral.** This project's SQLite accounts, tokens, chat history, and generated files are lost on restart or idle spin-down. A public signup system needs a durable external database and storage before real users are invited.
* Render Free may spin down when idle.
* This patch does not implement a persistent database, worker queue, or production-grade security audit.
* Never set `APP_ENV=development` on a public Render URL or print verification links to logs to bypass the check.
* If no verified sending domain is available, do not enable public signup; keep the site local until the email and database migration are completed.

To avoid hidden billing, check Resend and Google free-tier quotas before usage.
