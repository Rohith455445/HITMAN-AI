# Full project with Tavily integrated

**Start here:** [START_HERE_TAVILY.md](START_HERE_TAVILY.md) — full Windows installation, free web search configuration, troubleshooting, and Render security notes.

# HITMAN AI v12 — Researched Answers & Source Cards

**Start with [V12_START_HERE.md](V12_START_HERE.md).** This full release retains the earlier HITMAN AI guest chat, project builder, attachments, AI/ML starter projects, code repair and optional local Docker tools. v12 adds verifiable source cards, configurable Google Search grounding / Brave Search API, real-provider weather cards and explicit local research configuration. Provider API keys, quotas, commercial licences and possible charges still apply. This is not a copy of ChatGPT Pro services.

---

# HITMAN AI v11 — Research and Attachment Reliability Update

**START HERE:** [`V11_READ_THIS_FIRST.md`](V11_READ_THIS_FIRST.md) for correct Windows Python 3.14 commands, Gemini Search grounding opt-in, attaching PDFs and ZIPs, Builder Studio, and safe Render deployment.

This fixes ordinary-chat live research routing, current-info follow-ups, scanned PDF inputs, and file-only submissions. It does not implement proprietary ChatGPT Pro services; it is an independent Gemini/OpenAI-API-based project with provider-dependent tools.

---

# HITMAN AI v10 — Pro-style Workspace (Gemini / optional OpenAI API)

**This is an independent ChatGPT-inspired app; it does not include ChatGPT Pro model entitlements or proprietary OpenAI services.** API billing, model access, and hosting are separate.

### New in v10

- **Pro Review mode (opt-in):** a two-request draft → critique → revised final response pipeline. Uses your separately configured Gemini or OpenAI API. Not a guarantee of correctness.
- **Answer detail:** concise, balanced, or detailed, remembered on the current browser.
- **Longer answers:** configurable 1,200–8,000 output-token cap (default 3,500; may increase API cost).
- **Stop current response** on the browser; network cancellation does not guarantee API charges are avoided.
- **Safer model defaults:** optional OpenAI model defaults changed from unverified legacy IDs to `gpt-4.1`; use only models your API project actually has access to.
- Everything from v9 remains: Builder Studio, file/image understanding, optional grounded search and image generation, source ZIP checks, local Docker test/auto-fix. These are separately gated and not all are enabled on Render Free.

See **V10_QUICK_START.md** for Windows Python 3.14 and Render setup.

### Verification

Automated tests use simulated provider responses and do not use real API tokens; actual output quality and remote services still depend on your account, selected model, and quotas.

---

# HITMAN AI v9 — Advanced Builder + Local Test/Repair Agent

**Start here:** [V9_QUICK_START.md](V9_QUICK_START.md) for Windows Python 3.14, Docker Desktop, Gemini configuration, Builder Studio, and Render Free deployment.

**What's new:** optional local Docker syntax/unit tests for uploaded project ZIPs; up to two Gemini repair iterations; test reruns; diff and JSON/Markdown reports; strict loopback and origin restrictions. Public Render never runs project code.

Existing features from v8 (project generation, Gemini code review, offline AI/ML starters, static analyzer, chat, optional advanced provider integrations) are retained. The app is not an exact ChatGPT Pro clone; a ChatGPT subscription does not grant third-party access to OpenAI's private models and tools.

---

## Prior version documentation

# HITMAN AI v8 — Builder Studio

A ChatGPT-style **Gemini-powered assistant and development workspace**, now including a dedicated builder and safe code analyzer. This project is **not ChatGPT Pro** and cannot inherit its proprietary services or subscription.

## What's new in v8

- `/studio`: Full-stack apps, AI assistants/bots, ML pipelines, data science notebooks, APIs, automation and custom projects.
- Generate downloadable ZIPs with source, `README.md`, `HITMAN_BUILD_MANIFEST.json` and `HITMAN_BUILD_REVIEW.md`.
- Pre-export Python/JSON/notebook syntax checks. A single AI correction pass can repair invalid generated source. **No generated code is executed on Render.**
- Inspect an uploaded source ZIP for parsing failures and potential hard-coded credentials **without calling the AI model**.
- Opt-in Gemini review of a source ZIP; user must explicitly click **Ask Gemini to review**. Source is sent to the AI provider and is not stored by this endpoint.
- Three **free offline starter ZIPs** (AI bot, scikit-learn ML and CSV data science) require no Gemini generation calls.
- Retains prior HITMAN AI chat, file reading, research/image/voice feature gates, private workspaces and existing local authenticated backend.

## Local setup on Windows (Python 3.14 where compatible)

1. Extract the ZIP; open the actual `HITMAN-AI-v8-Builder-Studio` folder containing `main.py` and `requirements.txt` in VS Code.
2. Run:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

3. Set the following in `.env` (never commit this file):

```dotenv
APP_ENV=development
COOKIE_SECURE=0
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=your_private_key_from_google_ai_studio
HITMAN_PUBLIC_STUDIO_BUILD=1
HITMAN_PUBLIC_STUDIO_REVIEW=1
```

4. Start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

5. Open `http://127.0.0.1:8000/studio` for Builder Studio; open `http://127.0.0.1:8000/` for chat. Test Builder Studio **offline templates** even with `GEMINI_API_KEY` unset.

If Python 3.14 cannot install a dependency, install Python 3.12 and recreate `.venv` using `py -3.12 -m venv .venv`. Prefer an isolated virtual environment.

## Render Free

Use the existing **Web Service**, connected to your GitHub repository. Deploy the new source on `main`. Build command: `pip install -r requirements.txt`; start command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`. Keep:

```dotenv
APP_ENV=production
COOKIE_SECURE=1
PUBLIC_BASE_URL=https://YOUR-ACTUAL-RENDER-HOST.onrender.com
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=secret_added_in_Render_only
HITMAN_PUBLIC_STUDIO_BUILD=0
HITMAN_PUBLIC_STUDIO_REVIEW=0
HITMAN_PUBLIC_PROJECTS=0
HITMAN_PUBLIC_REPAIR=0
HITMAN_PUBLIC_LIVE_VOICE=0
```

**Free public functionality:** chat (within Gemini quota), offline template downloads, and static source ZIP checks. Builder Studio AI project generation and AI code review are opt-in because anonymous public access consumes your API quota. They use only per-instance best-effort rate limits and are **not recommended for an unrestricted public deployment**. A persistent server-side auth/quota layer is necessary for public use at scale. Render Free has an ephemeral filesystem; do not rely on its local SQLite files for durable accounts or histories.

When testing advanced features only on a controlled instance you can turn `HITMAN_PUBLIC_STUDIO_BUILD=1` and/or `HITMAN_PUBLIC_STUDIO_REVIEW=1` on in Render and redeploy. Review charges and provider quota first.

## Existing repo update

Extract this full release beside your existing HITMAN AI Git clone and run:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\path\to\your\HITMAN-AI-Git-folder"
```

The updater copies source and excludes `.git`, `.env`, SQLite DBs and other local secrets. Inspect `git status --short` and the diff before committing and pushing to public GitHub. Rotate any exposed keys.

## Validation and limits

The full application test suite runs with `python -m pytest -q` (test dependencies may need separate installation: `python -m pip install pytest`). AI model calls are mocked; no live Gemini calls or Render deployments were performed in the package tests. The three bundled starter projects' own unit tests were executed locally. The ZIP analyzer parses only text-source files (250 KB compressed, maximum 12 files and 95 KB expanded context), and does not execute uploads, install dependencies or verify semantic correctness. Generated projects are starter repositories, not automatically deployed or trained models. You must review dependencies, secrets, licenses, permissions, ML validation and runtime behavior.

---

## Previous HITMAN AI documentation

# HITMAN AI v7 — Advanced Studio

**ChatGPT-inspired AI workspace built with FastAPI, Gemini and a modern web chat interface.** This application is **not ChatGPT Pro** and does not inherit your ChatGPT subscription, GPT Astra access, private OpenAI tools, unlimited usage or safety guarantees.

## Included and verified (offline)

- Login-free chat with streaming replies, improved Markdown answers, inline links, safe code display, copy/save, dark/light theme, searchable browser-local chat history and transcript export.
- Programming help, debugging advice, AI/ML assistance, bounded image/PDF/text attachments, optional browser-local notes, voice dictation and speech playback.
- Optional **project starter ZIP** generation (`HITMAN_PUBLIC_PROJECTS=1`) with static Python/JSON checks. Generated source is **not executed**.
- Optional **two-pass grounded research** (`HITMAN_PUBLIC_RESEARCH=1` and `GEMINI_ENABLE_SEARCH=1`): research focus followed by Google Search-grounded response with returned source links. **Not identical to ChatGPT Deep Research.**
- Optional **Gemini-hosted Python code execution** via the Data Analysis mode (`GEMINI_ENABLE_CODE_EXECUTION=1`). Runs in Google's hosted tool if supported, not on the HITMAN AI server; availability is model/account-dependent.
- Optional **image generation/editing** (`HITMAN_PUBLIC_IMAGE=1`, `GEMINI_ENABLE_IMAGES=1`, and an eligible `GEMINI_IMAGE_MODEL`). Requires an image-capable Gemini model, often paid.
- Optional **reviewable AI ZIP code repair** (`HITMAN_PUBLIC_REPAIR=1`): accepts limited source ZIPs, proposes existing-file replacements, runs syntax checks and creates a patch ZIP containing a unified diff. **Does not execute, test or deploy projects.**
- Optional **Gemini Live voice proxy** (`HITMAN_PUBLIC_LIVE_VOICE=1`, install `requirements-voice.txt`): bidirectional microphone/audio using WebSocket, server-side API key, concurrency/time limits. A real provider session has **not** been tested. Uses optional model availability and costs.
- Optional **OpenAI API text mode** (`HITMAN_TEXT_PROVIDER=openai`, install `requirements-openai.txt`, set a separately billed `OPENAI_API_KEY`). Only when your OpenAI API project allows selected model IDs. It is *not* included in ChatGPT Pro subscriptions.
- **Local-only read-only browser inspector** (`tools/local_browser_inspect.py`), using explicit website allowlists and Playwright. This is a small browser research utility, *not* autonomous ChatGPT computer use. It is never exposed on Render.

All optional public tools are **disabled by default**. The existing private account/workspace code remains in this source tree but is **blocked** in public demo mode. The public demo does not have persistent cross-device accounts, GitHub agents or production-ready shared project storage.

## Windows VS Code quick start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Set `GEMINI_API_KEY` in `.env` privately. Use `HITMAN_PUBLIC_DEMO=1`, `APP_ENV=development`, `COOKIE_SECURE=0`, and `PUBLIC_BASE_URL=http://127.0.0.1:8000` for local demo. Open <http://127.0.0.1:8000>. **Never commit `.env` or keys.**

## Optional integrations — one at a time

Research: `HITMAN_PUBLIC_RESEARCH=1` and `GEMINI_ENABLE_SEARCH=1`. Google Search grounding may incur billing. Tools → Deep research, or select Deep research mode.

Hosted data analysis: `GEMINI_ENABLE_CODE_EXECUTION=1` and choose Data analysis in the mode selector. Do not assume support on every model.

Images: `HITMAN_PUBLIC_IMAGE=1`, `GEMINI_ENABLE_IMAGES=1`, `GEMINI_IMAGE_MODEL=gemini-3.1-flash-lite-image` (only if that model is available). Tools → Generate / edit image; image editing accepts small PNG/JPEG/WEBP attachment. Often paid; never turn on anonymously without quota controls.

ZIP patch proposal: `HITMAN_PUBLIC_REPAIR=1`. Attach a source `.zip` up to 250KB, describe a repair, Tools → Repair ZIP. It edits **only existing text files** in an in-memory ZIP and supplies a diff report. Review changes yourself; **no tests run**.

Live voice: `pip install -r requirements-voice.txt`, set `HITMAN_PUBLIC_LIVE_VOICE=1`, `GEMINI_LIVE_MODEL=...` to a Live model allowed for your account. HTTPS/localhost and browser microphone permission required. The server keeps the API key private; each connection has a short time limit. Live streaming is experimental and has not been end-to-end validated here. To install on Render, change build command to `pip install -r requirements-voice.txt`. The default Free hosting instance may be insufficient for multiple streams.

OpenAI API: `pip install -r requirements-openai.txt`; set `HITMAN_TEXT_PROVIDER=openai`, `OPENAI_API_KEY=...`, and model IDs available for your project. This changes only public **chat text**; Gemini remains the provider for optional research, voice and images. API billing is separate from ChatGPT plans.

Browser inspector, local only:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-browser.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe tools/local_browser_inspect.py --url https://example.com --allow-host example.com
```

The read-only inspector captures screenshot and page text into `browser-inspection/`. It never clicks, fills forms, makes purchases or controls your desktop.

## Upgrade your existing HITMAN AI Render Git repository

Read [DEPLOY_V7_RENDER_FREE.md](DEPLOY_V7_RENDER_FREE.md). Run `UPDATE_EXISTING.ps1` from this extracted v7 folder targeting your **existing** Git repository. The updater preserves `.git`, `.env`, SQLite and locally generated data. Back up first.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q
```

The automated tests use mocked provider results, not real Gemini/OpenAI requests. `node --check static/app.js` and `node --check static/live_v7.js` validate frontend JavaScript syntax. No live billing, web research, remote computer access, voice model, image generation or provider workflows were verified in the supplied environment.

## Security and cost

**Never expose a public AI service without per-user accounts, persistent storage, provider-level spending limits, strong abuse controls, request auditing and isolated tool execution.** The built-in anonymous rate limiter is best-effort only. The Render Free instance has ephemeral storage and may sleep; browser-local data is only on that device. Guest file content and notes are sent to Gemini during requests. Never upload secrets or sensitive data. The image/research/live modes may cost money or be unavailable on your account even when enabled in environment settings.
