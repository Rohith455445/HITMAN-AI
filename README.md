# HITMAN AI v4 — Gemini API Edition

**START HERE:** Read [GEMINI_SETUP.md](GEMINI_SETUP.md) for the updated Windows/VS Code commands and free-tier limitations. This edition replaces OpenAI API calls with Gemini via `gemini_bridge.py` and `GEMINI_API_KEY`, while keeping the same ChatGPT-style UI.

---

## Legacy reference notes (original v4)

The following instructions were written for the original OpenAI-based edition. **Do not use their OPENAI_API_KEY / OPENAI_MODEL instructions for this Gemini edition.**

# HITMAN AI — v4 ChatGPT-style Interface + Developer Workspace

**NEW:** Redesigned chat interface, theme toggle, chat search, grouped tools menu, mobile navigation, copyable code. See [`UPGRADE_V4.md`](UPGRADE_V4.md) for setup and accurate feature limits.

If you already configured accounts and email in v3, **install only the UI files** rather than replacing your old project or database.

## Existing v3 backend documentation


A **ChatGPT Pro-inspired** application with user accounts, AI chat, advanced reasoning-model configuration, file analysis, image APIs, realtime voice integration, personalized memory, project ZIP generation, GitHub import/draft PRs, and review-first multi-file coding edits.

**What this is not:** It does not contain the proprietary ChatGPT Pro system or confer Pro subscription entitlements. A valid OpenAI API key and separate API billing are required for live AI features; your GitHub token and email service are also separate. This is a **single-server prototype**, not certified production-ready software.

## Run locally in VS Code (Windows)

1. Extract the download and open the **`hitman-ai-v3`** folder in VS Code: `File → Open Folder`.
2. Install Python 3.11 or newer, and the VS Code Python extension. Python 3.12 is recommended.
3. Run `start_windows.bat` or execute in the VS Code terminal:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

4. Add `OPENAI_API_KEY=...` to your local `.env`. Do **not** commit `.env` or share API keys.
5. Visit <http://127.0.0.1:8000/signup>. Register a username, email and password. In local development, the verification link is printed **only in your local server terminal**. Visit it and then sign in.
6. Work in <http://127.0.0.1:8000/workspace> or use the chat at <http://127.0.0.1:8000/>.

VS Code debugging configuration is included under `.vscode/launch.json` (Run and Debug → **HITMAN AI • FastAPI**). `start_windows.bat` creates the virtualenv/installs requirements; edit `.env` afterwards for API access.

If you prefer a Linux/macOS terminal: `./start_linux_mac.sh`.

Create an **administrator** from your **trusted local terminal** with `.venv\Scripts\python.exe manage_admin.py`. Administrator rights are never granted to public sign-ups.

## Signup, verification and recovery

- Anyone can register a **member** account. Verification emails contain a single-use token valid for 24 hours; unverified accounts cannot log in. Existing legacy accounts without email stay enabled until migrated manually.
- `/verify-email` verifies or resends verification links. `/forgot-password` sends a 30-minute reset link, and `/reset-password` changes the password and invalidates all existing sessions.
- All tokens are stored as hashes, not reusable plaintext. Sessions are HttpOnly and SameSite=Strict; `COOKIE_SECURE=1` is mandatory for a public HTTPS site.
- `EMAIL_TRANSPORT=console` is exclusively for a local development server: links are printed in the local backend console. **Do not publicly expose the application with development email mode.**
- For real users on your website, configure `APP_ENV=production`, `EMAIL_TRANSPORT=smtp`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `PUBLIC_BASE_URL=https://your-domain.example` and `COOKIE_SECURE=1`. Check outbound SMTP availability from your host. SMTP delivery has **not** been live-tested in this package.

## GitHub integration (fine-grained token)

Create a *fine-grained personal access token* on GitHub scoped to only the repositories needed. You need repository Metadata read / Contents read to import, and Contents write / Pull requests write to publish a draft pull request. Some repo/organization policies may restrict access.

1. Run `.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`; put the value in `GITHUB_TOKEN_ENCRYPTION_KEY` in `.env`. **Keep the key secret; losing it means reconnecting tokens.**
2. Sign in to HITMAN AI → **Developer Workspace → Connect GitHub**. Paste the token. HITMAN encrypts it before storing it in SQLite and does not expose it to the browser again.
3. Click **List repositories**, then **Import** a repository into your private workspace. Import is limited to 55 UTF-8 text/source files and 350 KB total, and excludes hidden files, binary data, and unsafe paths. It is **not** a full Git clone (no Git history, branches, LFS, submodules or large monorepos).
4. Describe an edit → generate an AI proposal → review the diff → explicitly **Approve**. Optionally run tests. Click **Create draft pull request**, review the confirmation, and HITMAN creates a new GitHub branch and draft PR. It does not push to the default branch or merge the PR.
5. If the remote default branch changed since import, publishing refuses to proceed until you re-import to avoid conflicts.

This build supports repository listing, safe source import, draft PR creation, and disconnect. **It does not yet manage every GitHub feature** (issues, protection rules, workflows, commits history, merging, release management, OAuth app installation). The integration was tested with a mocked GitHub API; real GitHub credentials were not provided.

## Automated coding and tests

- **Propose code changes:** Uses a configurable advanced API reasoning model to generate complete-file patches; up to 3 tries to correct static syntax problems.
- **Auto-debug and verify:** Bounded iterative workflow (up to 3 validation cycles and 2 model edit attempts) using test feedback; the result is an **unapplied proposal**. Review and approve changes to use them.
- **Static checks:** Python AST and JSON syntax parsing.
- **Optional Docker tests:** Disabled until `ENABLE_DOCKER_TESTS=1` is set and Docker is installed. Uses locally preloaded Python/Node images; image downloads are explicitly prevented. Python uses pytest and Node uses npm test.
- **Optional dependency installation:** Requires `ENABLE_DEP_INSTALL=1` **and** the user selecting **Install dependencies** for that run. Python requires `requirements.txt` with pinned `package==version` entries and binary-only installation; Node requires `package-lock.json` and runs `npm ci --ignore-scripts`. The installation container can access the network to fetch packages; the subsequent test container has no network, no elevated privileges, and resource limits. Only temporary copies of projects are mounted.
- **Security warning:** Docker alone is not sufficient isolation for adversarial code in a public multi-tenant SaaS. Do not allow anonymous code execution on the public Internet. For real production use, run tests in disposable microVMs, restrict egress during dependency installation, set file/network quotas and isolate workers from the API service and internal networks.
- Without Docker/appropriate images/dependencies, HITMAN explicitly reports **tests not executed** rather than faking passing tests.

## User isolation and security

- Users own their chats, saved memory, uploaded project workspaces and generated-project downloads.
- Per-user GitHub tokens are encrypted with Fernet, from a secret held outside the database.
- Server-side sessions can be revoked. Passwords are salted PBKDF2-SHA256 hashes (450,000 iterations); login attempts and recovery submissions are throttled in SQLite.
- Same-origin checks and strict cookies reduce CSRF risk; response headers include CSP, no-sniff, clickjacking protection and no-referrer.
- Daily caps on major paid AI operations prevent accidental uncontrolled bills, but **do not** replace provider-side spending limits and abuse controls.
- Legacy chat/memory records without an owner ID are not shown to newly registered users. Export/back up your existing database before migration if upgrading an old installation.

**Remaining production gaps:** external identity/OAuth and MFA, a trusted proxy/HTTPS setup, centralized Redis rate limits for multiple web replicas, PostgreSQL migration/backup and encryption-at-rest strategy, proper CSRF token handling for unusual cross-origin deployments, sandbox escapes hardening, full per-user cost accounting of model tokens/voice duration, malware scanning, vulnerability auditing, observability, disaster recovery, GDPR/data retention workflows, tenant-scale load tests, and real credential-based integration tests. Verify these before opening a public paid AI service.

## Tests

Install requirements then `python -m pip install pytest`; run `python -m pytest -q`. Eleven offline tests are included for authentication, password recovery, workspace isolation, GitHub PR construction, bounded repairs and sandbox command isolation. Tests mock remote AI/GitHub/SMTP and Docker commands. Source syntax and ZIP integrity checks are also included in release validation.

## Troubleshooting

- **No AI replies:** Check `OPENAI_API_KEY`, model access/billing, the configured model name and backend logs. The API costs are separate from ChatGPT subscriptions.
- **GitHub connect says key missing:** Set `GITHUB_TOKEN_ENCRYPTION_KEY`, then restart the server. Never put GitHub tokens in browser local storage.
- **Not receiving email locally:** Look in the terminal where Uvicorn is running; local console transport logs verification/reset links.
- **Password reset worked but you're logged out:** Expected; sessions are revoked.
- **Docker tests unavailable:** Install Docker Desktop, preload image(s), enable the flags in `.env`, and restart. Avoid public deployment of this feature without dedicated isolated worker infrastructure.
- **Public site gets origin error:** Ensure `PUBLIC_BASE_URL` exactly matches the public HTTPS origin and the reverse proxy forwards requests securely. Never trust arbitrary `X-Forwarded-For` from the Internet for rate limiting.
- **Can't open in VS Code:** Extract the ZIP first; open the folder containing `main.py` and `.vscode`, not the ZIP file itself.
