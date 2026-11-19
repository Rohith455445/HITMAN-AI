# HITMAN AI v4 — ChatGPT-style interface upgrade

This is an original HITMAN AI interface inspired by common AI chat interaction patterns. It is not the ChatGPT app, does not duplicate OpenAI trademarks, and does not confer ChatGPT Pro features, model entitlements, or usage allowances.

## What changed

- Desktop left sidebar and mobile slide-out navigation; new chat and conversation-history search
- Mode picker: Chat, Reasoning, Code expert, Web search, Data analysis, Agent planning
- Large, expandable chat composer with drag-and-drop file attachment and visible attachment removal
- Organized Tools menu: Build project, Build AI model, Generate/edit image, Deep Debug, Repair ZIP, Memory, Export, Live Voice
- Conversation reply formatting (headings and fenced code) with safe text rendering, per-message copy and copy-code buttons
- Light and dark themes (locally remembered when browser storage is available)
- Shortcut Ctrl/Cmd+K for new chat; / to search history; Enter to send and Shift+Enter for a line break
- Existing authentication, workspace, email verification/recovery, GitHub integration, testing, API routes and image/voice integrations retained

**API models and actual capability:** The picker chooses a configured workflow, not an independent ChatGPT Pro subscription or every public API model. The `Reasoning`, `Code expert`, and `Agent planning` modes use the reasoning model configured on the backend. Web search and data analysis require API tool eligibility; image/voice features similarly need separate API access and a working browser. The UI cannot verify credentials until you use a tool.

## Keep your existing account and configuration (recommended)

If your previous HITMAN AI v3 already runs in VS Code, **do not replace its project folder** or delete `.env` / database files. Stop the running server and copy only these three files from the update into your **existing** `hitman-ai-v3/static` folder, replacing the old files:

1. `static/index.html`
2. `static/styles.css`
3. `static/app.js`

Restart `uvicorn`, then hard refresh your browser with **Ctrl + Shift + R**. Your existing user accounts and application configuration stay in the old project.

## Full project in VS Code

If you want a fresh folder instead, extract the full download, and open the folder containing `main.py` in VS Code.

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Set `OPENAI_API_KEY` in `.env` and verify the chosen models are accessible on your own API account. Run the application at http://127.0.0.1:8000 and sign in. In development, email verification links appear in the server terminal when `EMAIL_TRANSPORT=console`.

## What is already wired to this interface

- Streaming AI chat, private conversation history, text/document/image input
- Reasoning mode, Code expert mode, web search, hosted code interpreter (when supported)
- AI image generation/editing, microphone dictation, realtime voice connection (when supported)
- Memory CRUD, project ZIP generation, AI/ML model scaffolds, deep-debug two-pass review, ZIP repair
- Dedicated developer workspace with reviewable edits, GitHub repo import and draft PR creation, optional Docker testing

## Still not equivalent to ChatGPT Pro

Native ChatGPT Pro models and allowances are not included. HITMAN AI does not offer the full official ChatGPT Work/Codex cloud-computer environment, production-grade browser agents, full scheduled tasks, long-running background research, connectors to every third-party service, the complete ChatGPT multimodal stack, or enterprise-grade public hosting. Existing ZIP tooling is bounded; production deployment requires sandbox/security work and real integration tests. **Do not advertise it as providing all ChatGPT Pro features.**

## Testing

Backend automated tests: `python -m pytest -q`. The UI is plain HTML/CSS/JS; `node --check static/app.js` verifies JavaScript syntax. Browser interactions have been checked in a mocked, non-provider preview. None of these checks prove that paid AI services work with your own credentials.
