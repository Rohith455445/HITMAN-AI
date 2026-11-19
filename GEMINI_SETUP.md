# HITMAN AI v4 — Google Gemini API (Free-tier setup)

This edition uses **Google's native Gemini Developer API**, not the OpenAI API. The **ChatGPT-style frontend, accounts, chat history, workspaces and SQLite files remain unchanged**. You only need to update two Python source files and configure `.env`.

**Free tier has limits** and Google determines which models/features are available to a project. Google may use free-tier input/output to improve its products, so do not upload passwords, client secrets, private commercial repositories, or confidential documents. **HITMAN AI does not become ChatGPT Pro**, and Gemini does not give access to OpenAI's paid Astra models.

## A. Update your already-running HITMAN AI v4 (recommended)

**1. Back up** your current `HITMAN-AI-v4` folder (especially `.env` and `chats.db`). Stop the terminal running Uvicorn with `Ctrl+C`.

**2. Replace only these Python files** in your existing VS Code folder:

- `main.py` (overwrite existing)
- `gemini_bridge.py` (new file)

They are provided in `HITMAN-AI-v4-Gemini-Backend-Patch.zip`. Do not replace the `static` folder, `chats.db`, `.env`, or account files.

**3. Get your key** from https://aistudio.google.com/apikey . Create/select a Gemini Developer API key in an eligible free-tier project. This is **not** an OpenAI key. Keep the key private.

**4. In the VS Code terminal, enter the real project folder:**

```powershell
cd 'C:\Users\vvysh\Downloads\HITMAN-AI-ChatGPT-Style-v4-Full\HITMAN-AI-v4'
dir main.py
notepad .env
```

Use the exact actual folder path on your PC if different. If `.env` is missing, create it by copying `.env.example` first. Add/replace these lines in `.env`:

```dotenv
GEMINI_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_REASONING_MODEL=gemini-3.5-flash-lite
GEMINI_CHAT_MAX_OUTPUT_TOKENS=6000
GEMINI_OUTPUT_LIMIT=16000
GEMINI_ENABLE_SEARCH=0
GEMINI_ENABLE_CODE_EXECUTION=0
GEMINI_ENABLE_IMAGES=0
# Optional only if selected Gemini model supports it; otherwise blank:
GEMINI_THINKING_LEVEL=
```

The `GEMINI_API_KEY` line must contain your actual AI Studio key, not the literal placeholder. Remove any old `OPENAI_API_KEY` setting you no longer need. Do **not** place the key inside `main.py`, `static/app.js`, GitHub or chat messages.

**5. You do not need to reinstall packages** if your previous HITMAN AI v4 already runs: `httpx` is already in `requirements.txt`. Otherwise run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**6. Test that Python sees your Gemini key without printing it:**

```powershell
.\.venv\Scripts\python.exe -c "from dotenv import load_dotenv;import os;load_dotenv();print('Gemini key found:',bool(os.getenv('GEMINI_API_KEY')));print('Model:',os.getenv('GEMINI_MODEL'))"
```

**7. Restart and open HITMAN AI:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/ and sign in. Try `Hello, explain Python functions`.

## B. Install the complete Gemini edition from scratch

Extract `HITMAN-AI-v4-Gemini-Full.zip` and open the **inner** `HITMAN-AI-v4-Gemini` folder in VS Code (the one containing `main.py` and `requirements.txt`). On Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Python 3.12 is recommended; if not installed, `py -3.14 -m venv .venv` may work if the project's dependencies have compatible wheels. Set the Gemini key in `.env`, then run:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Visit `/signup` to create an account. In `EMAIL_TRANSPORT=console`, verification links are printed to the VS Code terminal instead of being sent to Gmail.

If you want your old account and chats in the full edition, **stop both servers**, then copy your backed-up v4 `chats.db` and `.env` into the new inner folder and add Gemini settings to that existing `.env`. Preserve any GitHub encryption key.

## What works, and what does not

| Feature | Free-tier Gemini edition |
|---|---|
| Chat, streaming responses, conversation history | Gemini API integration; live access must be tested with your key |
| Coding and planning chat | Gemini model responses |
| Generate project ZIPs and AI/ML starter projects | Gemini JSON generation, subject to free quota and output limits |
| Deep Debug and workspace proposals | Gemini model analysis, static validation, no guarantee of correctness |
| Image understanding, TXT/MD/PDF input | Sent to Gemini model on this turn; check supported formats/quotas |
| Saved memory, signup/login, private workspaces | Existing local SQLite implementation preserved |
| GitHub import and draft pull requests | Existing GitHub feature unchanged; requires separately configured GitHub access |
| Browser speech dictation | Preserved if browser supports it |
| Web search grounding | **OFF by default**: Google Search grounding may not be included in free tier on the selected new model |
| Hosted code execution for analysis | **OFF by default**, may be supported with compatible models |
| Image generation/editing | **OFF by default**, selected model may require paid API access |
| Live two-way voice | **Not integrated**: Gemini Live uses a different protocol; old OpenAI WebRTC button cannot be reused |
| OpenAI Astra/ChatGPT Pro | **Not included**: switching providers does not confer paid/proprietary model access |

These settings turn on a tool **only if your Gemini account/model supports it** (check the official pricing and model documentation first):

```dotenv
GEMINI_ENABLE_SEARCH=1
GEMINI_ENABLE_CODE_EXECUTION=1
GEMINI_ENABLE_IMAGES=1
GEMINI_IMAGE_MODEL=gemini-3.1-flash-lite-image
```

Do not enable paid-only features expecting them to be free. A project upgraded to billing can incur charges. Keep the toggles at `0` for the default no-billing setup.

## Troubleshooting

- `GEMINI_API_KEY is missing`: `.env` is in the wrong folder or key was not saved. Check `dir .env` from the folder containing `main.py`.
- `API_KEY_INVALID` / HTTP 400: incorrect Gemini key; regenerate at Google AI Studio.
- `NOT_FOUND` / HTTP 404: chosen model not available to your project; verify model list in AI Studio, then edit `GEMINI_MODEL`.
- `RESOURCE_EXHAUSTED` / HTTP 429: free quota/rate limit reached; check AI Studio usage, try later, or use a model with accessible limits.
- Search mode reports disabled: normal for this free-tier config. Use standard chat for explanations; web-realtime information requires grounding access.
- Image button reports disabled: normal for free-tier config; image understanding through an attached photo in chat is a different capability.
- The full ZIP has a second nested folder: open the folder that contains `main.py` in VS Code before running commands.
- Chat succeeds but a very large generated project fails: try a smaller project, fewer files, or ask for components separately; free model output may be truncated.

## Security

The Google API key is stored **only in `.env` on the server**. `.env` and `chats.db` are excluded from the released ZIP and from `.gitignore` tracking. Keep the server bound to localhost while testing. If a prior key has appeared in a screenshot or chat, revoke it at its provider and generate a new one.

Official documentation:
- API keys: https://aistudio.google.com/apikey
- Free-tier prices/availability: https://ai.google.dev/gemini-api/docs/pricing
- Models: https://ai.google.dev/gemini-api/docs/models
- Code execution: https://ai.google.dev/gemini-api/docs/code-execution
- Grounding: https://ai.google.dev/gemini-api/docs/google-search
