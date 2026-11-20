# HITMAN AI v8 · Fast setup (Windows and Render Free)

## Open the right folder

Extract `HITMAN-AI-v8-Builder-Studio-Full.zip`. Open the **inner** `HITMAN-AI-v8-Builder-Studio` directory in VS Code. It must contain `main.py`, `requirements.txt`, `studio_engine.py`, `offline_templates.py` and `static/studio.html`.

## Local with Python 3.14 (try existing version first)

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Inside `.env`, set (keep any other existing keys):

```dotenv
HITMAN_PUBLIC_DEMO=1
APP_ENV=development
COOKIE_SECURE=0
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=your_real_private_gemini_key
HITMAN_PUBLIC_STUDIO_BUILD=1
HITMAN_PUBLIC_STUDIO_REVIEW=1
```

Launch:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open [chat](http://127.0.0.1:8000/) or [Builder Studio](http://127.0.0.1:8000/studio). For Python package compatibility issues, install Python 3.12 and recreate `.venv` with that version.

## How to use Builder Studio

1. Select **AI bot**, **AI/ML model**, **Data Science**, **Full-stack app**, **Backend API**, **Automation**, or **Custom project**.
2. Describe the requirements and click **Generate project ZIP**. Requires valid Gemini API key and the `HITMAN_PUBLIC_STUDIO_BUILD=1` switch. Output is a reviewable source-code starter (max 16 files).
3. For AI Bot / ML / Data Science, click **Download offline starter**. This requires no Gemini API key or quota.
4. Use **Analyze code ZIP** to inspect an existing project. Static analysis does not call Gemini. **Ask Gemini to review** requires `HITMAN_PUBLIC_STUDIO_REVIEW=1` and sends source to Gemini. Remove credentials from uploaded code.
5. Check `HITMAN_BUILD_REVIEW.md` and run the project's own setup/tests locally before trusting the result.

## Update the existing Render repo

From the **newly extracted** v8 source folder:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\Users\vvysh\Downloads\HITMAN-AI-v4-Render-Deployment\HITMAN-AI-v4-Render"
```

Review `git status --short` and ensure no credentials, `.env`, `.db`, `.venv` are staged. Then in your **existing Git repo folder**:

```powershell
git add .
git status --short
git commit -m "Add HITMAN AI v8 Builder Studio"
git push origin main
```

On Render set `HITMAN_PUBLIC_DEMO=1`, `APP_ENV=production`, `COOKIE_SECURE=1`, and `PUBLIC_BASE_URL=https://<your-actual-service>.onrender.com`. Keep Gemini API key in Render's secure environment variables.

**For a public Render Free service, keep `HITMAN_PUBLIC_STUDIO_BUILD=0` and `HITMAN_PUBLIC_STUDIO_REVIEW=0`** until you add proper user authentication and robust server-side quotas. Offline starter downloads and static source inspection remain available. Render Free filesystem changes are temporary, so do not rely on its local SQLite database for durable public accounts.

The application is a practical developer tool but **not identical to ChatGPT Pro**, cannot inherit your ChatGPT subscription, and does not autonomously execute unknown uploaded programs or guarantee correctness.
