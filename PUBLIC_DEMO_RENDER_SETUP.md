# HITMAN AI — Login-Free Render Free Demo

## What changed

- Visitors open `/` without signup, login, password or email verification.
- Public chat runs at `POST /api/public/chat` with streaming Gemini responses.
- Chat transcripts are **browser-local only**, and are not stored in server-side account databases.
- Public mode disables private API routes (accounts, saved memory, authenticated conversations, private project workspaces, file uploads, GitHub and ZIP generation).
- `/login`, `/signup`, `/workspace` and recovery pages redirect to `/` when the demo is enabled.
- Render Free production can start **without Resend or SMTP** in anonymous demo mode.
- Quotas: up to 12 requests per 15 minutes per observed IP and 60 requests per UTC day across the single instance. These quotas are **best-effort** and reset when temporary SQLite data disappears; add external rate limiting before large-scale public access.

## Install in your existing GitHub + Render service

1. Back up your local project. Extract `HITMAN-AI-No-Login-Patch.zip`.
2. Copy the patch `main.py`, `static/app.js`, `static/index.html`, `static/styles.css` into your current **HITMAN-AI-v4-Render** project, preserving their relative paths. The patch also includes this guide, `render.yaml`, `.env.example` and the new tests.
3. Use `git add main.py static/app.js static/index.html static/styles.css .env.example render.yaml PUBLIC_DEMO_RENDER_SETUP.md tests/test_public_demo.py`; then `git commit -m "Enable login-free public chat demo"` and `git push origin main`.
4. In **Render → HITMAN-AI → Environment** add/update exactly:

   ```dotenv
   HITMAN_PUBLIC_DEMO=1
   APP_ENV=production
   COOKIE_SECURE=1
   PUBLIC_BASE_URL=https://hitman-ai.onrender.com
   GEMINI_API_KEY=<your-private-rotated-key>
   GEMINI_MODEL=<a-model-available-in-your-Gemini-account>
   GEMINI_REASONING_MODEL=<a-model-available-in-your-Gemini-account>
   ENABLE_DOCKER_TESTS=0
   ENABLE_DEP_INSTALL=0
   ```

   Keep API keys **only** in Render environment settings. You do **not** need `EMAIL_TRANSPORT`, `RESEND_API_KEY`, or `RESEND_FROM` in demo mode; delete those variables if they are not used elsewhere.

5. Keep Render instance **Free**, build command `pip install -r requirements.txt`, start command `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`, Root Directory blank if your repo has `main.py` at root.
6. **Manual Deploy → Deploy latest commit**, or Save & Deploy if editing variables.
7. Verify `https://hitman-ai.onrender.com/health` returns `{"status":"ok"}`. Open `https://hitman-ai.onrender.com/` and send `Hello`.

## Important security and behavior notes

- Don't remove the authentication checks from existing private endpoints. The public mode explicitly blocks them.
- The login files are preserved for re-enabling the private app later; they are inaccessible through their page routes in guest mode.
- Your Gemini free-tier API key is still consumed when strangers send messages. The built-in quota is limited and not an abuse-proof protection. Restrict API usage and monitor quotas; for a broader audience use a third-party gateway/WAF and distributed rate limits.
- Anonymous chat currently supports text (including code help), not file uploads, AI images, saved memory, GitHub editing, or project ZIP generation.
- Chats are saved in localStorage on each browser, not shared between browsers or backed up. Avoid sharing sensitive information or using shared computers.
- The Render Free filesystem is ephemeral. Anonymous mode does not promise account or project persistence.
- To switch back to authenticated mode, change `HITMAN_PUBLIC_DEMO=0` and configure persistent storage plus a verified email transport before allowing public registration.
- Before deployment, rotate any Gemini/OpenAI/Resend keys accidentally shown in screenshots and confirm `.env` is excluded from the Git repository.

## Local preview

```powershell
Copy-Item .env.example .env
# Set GEMINI_API_KEY=<your key>, HITMAN_PUBLIC_DEMO=1 in .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Test coverage

`python -m pytest -q` checks that the public page is accessible, protected endpoints are blocked, guest chat streams, and that the old authenticated behavior is preserved when the demo flag is off. Live Gemini API requests and Render deployments require your credentials and remain unverified here.
