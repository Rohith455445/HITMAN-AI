# HITMAN AI v9 — Build, Test, Review, Auto-Fix

**Scope:** a ChatGPT-style app using Gemini APIs, not ChatGPT Pro itself. Your ChatGPT subscription does **not** provide API calls, private OpenAI tools, model access, or hosting for HITMAN AI.

## Start HITMAN AI on Windows (your existing Python 3.14)

1. Extract `HITMAN-AI-v9-Pro-Builder-Full.zip`. In VS Code, open the **inner** `HITMAN-AI-v9-Pro-Builder` directory, where `main.py`, `.env.example`, `requirements.txt` and `static/studio.html` are located. This fixes the previously seen `requirements.txt / .env.example not found` issue.
2. Run these commands in the VS Code PowerShell terminal, from that inner folder:

```powershell
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

3. In `.env` set the following entries (leave unrelated entries intact). **Never paste real API keys into GitHub or screenshots.**

```dotenv
APP_ENV=development
COOKIE_SECURE=0
HITMAN_PUBLIC_DEMO=1
HITMAN_TEXT_PROVIDER=gemini
GEMINI_API_KEY=YOUR_ACTUAL_PRIVATE_GEMINI_API_KEY
GEMINI_MODEL=YOUR_AVAILABLE_GEMINI_MODEL
GEMINI_REASONING_MODEL=YOUR_AVAILABLE_GEMINI_MODEL
HITMAN_PUBLIC_STUDIO_BUILD=1
HITMAN_PUBLIC_STUDIO_REVIEW=1
HITMAN_LOCAL_DOCKER_AGENT=1
HITMAN_AGENT_PYTHON_IMAGE=python:3.12-slim
HITMAN_AGENT_NODE_IMAGE=node:22-alpine
```

Use a model identifier you can actually access in [Google AI Studio](https://aistudio.google.com/) rather than assuming that any model name is available. If installing packages fails on Python 3.14, install Python 3.12 and recreate `.venv` with `py -3.12 -m venv .venv`.

4. Start the backend **bound to localhost only**:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

5. Open <http://127.0.0.1:8000/studio>. Your chat is <http://127.0.0.1:8000/>.

## Enable actual Docker test execution

Local Python `venv` is **not** a safe sandbox for executing unknown uploaded code. HITMAN v9 uses Docker Desktop instead. Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) and **start it**; check in PowerShell:

```powershell
docker version
docker info
docker pull python:3.12-slim
docker pull node:22-alpine
```

The basic `python:3.12-slim` image supports Python syntax and `unittest` tests that need no additional packages. It does **not** include pytest, pandas or scikit-learn. For a curated Python image with pytest and common ML dependencies, build it separately:

```powershell
docker build -t hitman-agent-python:local -f tools/Dockerfile.python-agent .
```

Then change `.env` to `HITMAN_AGENT_PYTHON_IMAGE=hitman-agent-python:local` and restart the server. The Docker build uses the internet to obtain the base image and packages; **running uploaded code has no network access**. The image is not automatically downloaded during a test.

## How the new agent works

1. On Builder Studio, create an AI bot, AI/ML model, data science project, web app, API or automation and download its ZIP. This uses Gemini when generation is enabled. Three existing offline starters remain available without a model call.
2. Choose **Analyze code ZIP**, upload a **small source ZIP**, and optionally click **Ask Gemini to review**. Review sends your text source to the AI provider; static checks do not.
3. Under **Local Docker Test & Auto-Fix Agent**, select **checks only**, **1 fix**, or **2 fixes**. Confirm consent, then click **Run Docker tests / auto-fix**. An AI-fix selection sends the source and failing logs to Gemini.
4. Download the resulting ZIP and read `HITMAN_AGENT_REPORT.md` and `HITMAN_AGENT_MANIFEST.json`. A passing Python syntax check is **not** a passed unit test; the manifest has separate `tests_executed` and `tests_passed` flags. Review diffs before installing or deploying.

You can also use the optional CLI without opening a browser:

```powershell
.\.venv\Scripts\python.exe tools/local_agent_cli.py --zip ".\example-project.zip" --output ".\checked-project.zip" --rounds 1 --i-accept-risk
```

A `--rounds 0` run does not call Gemini. `--rounds 1` or `2` attempts AI fixes *only after a test failure*. The model may be unable to resolve issues without installing project-specific dependencies or running an interactive UI. The local agent accepts up to 20 text source files / 180 KB expanded; static-only public analysis has a smaller 12-file limit. The agent **does not** modify your original ZIP, install packages, train a model, deploy to Render, publish to GitHub, or run arbitrary requested shell commands.

### Docker security restrictions

The agent uses `--network=none`, a **read-only source bind mount**, `--read-only` root filesystem, a non-root user, dropped Linux capabilities, `no-new-privileges`, CPU/memory/process limits, a 25-second per-command timeout, and only predefined test commands. No API keys or credential variables are forwarded to Docker. These protections reduce but do not eliminate the risks of running untrusted code; use only code you own or trust and prefer a dedicated testing machine/VM for unknown software. The local API is disabled in production and rejects non-loopback requests and unauthorized browser origins.

## Render Free — chat and static tools only

Your existing Render service may deploy the same source with **different environment variables**. Keep the Docker agent and expensive public tools OFF:

```dotenv
APP_ENV=production
COOKIE_SECURE=1
PUBLIC_BASE_URL=https://hitman-ai.onrender.com
HITMAN_PUBLIC_DEMO=1
HITMAN_LOCAL_DOCKER_AGENT=0
HITMAN_PUBLIC_STUDIO_BUILD=0
HITMAN_PUBLIC_STUDIO_REVIEW=0
HITMAN_PUBLIC_PROJECTS=0
HITMAN_PUBLIC_REPAIR=0
ENABLE_DOCKER_TESTS=0
ENABLE_DEP_INSTALL=0
```

Keep a valid private Gemini API key in Render's Environment settings. Public users can use chat (subject to quotas), static ZIP review, and offline starter ZIPs. **Do not turn on local Docker auto-execution on Render or a public instance.** The Render Free instance is not an isolated, persistent multi-tenant code execution service.

For an existing GitHub repo, extract the v9 ZIP outside your repository and run from the inner v9 folder:

```powershell
.\UPDATE_EXISTING.ps1 -Target "C:\path\to\your\existing\HITMAN-AI-Git-repository"
```

Then open your existing Git repository, inspect `git status --short` and `git diff`, confirm `.env` and keys aren't staged, and run `git add .`, `git commit -m "Upgrade HITMAN AI v9"`, and `git push origin main`. Render can rebuild from `main`.

## What is and is not provided

- **Included:** Gemini chat and formatted answers; Builder Studio; reviewable multi-file project generation; optional AI source review; static syntax checking; offline AI/ML/data-science templates; local restricted Docker tests; at most two Gemini auto-fix passes with test reruns and reviewable diff ZIPs.
- **Provider-dependent:** Gemini research grounding, image generation/editing, Live voice, hosted code execution, separately billed OpenAI API text mode. These features were introduced in v7 and retain their provider, quota and environment gates.
- **Not claimed:** ChatGPT Pro/GPT proprietary model entitlement, full autonomous computer use, unrestricted agents, exact response quality or unlimited requests, safe public execution of arbitrary user code, production-ready security, comprehensive correctness proofs, or live Render deployment from this package.

Tests in the release use mocked Gemini and Docker calls; they **do not** establish that your real Gemini key, Docker Desktop, third-party packages, or hosted deployment will work until you test them locally.
