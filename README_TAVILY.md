# HITMAN AI v12: free Tavily search patch

This patch adds the Tavily Search API to existing HITMAN AI v12. It leaves Builder Studio, PDFs, images, source ZIP analysis, voice and other existing routes intact. It adds a new `search_tavily()` function in `research_sources.py`, uses it in anonymous chat and research, and reports Tavily in `/api/config` and `check_v12_setup.py`.

## Apply on Windows / PowerShell

1. Back up your HITMAN AI project.
2. Unzip this patch into a separate folder. Do not extract it over the project.
3. From the patch folder, run (change the path to your actual folder):

   ```powershell
   .\APPLY_PATCH.ps1 -Target 'C:\Users\vvysh\Downloads\HITMAN-AI-v12-Research-Workspace-Full'
   ```

   This backs up the three changed files with a `.before_tavily.bak` suffix. It does **not** modify `.env`, private API keys, local database, frontend files, Builder Studio, or tests.

4. Obtain a key at https://app.tavily.com/ . In your EXISTING project `.env` file set:

   ```dotenv
   TAVILY_API_KEY=tvly-YOUR_PRIVATE_KEY
   GEMINI_ENABLE_SEARCH=0
   HITMAN_AUTO_WEB_SEARCH=1
   HITMAN_PUBLIC_RESEARCH=1
   HITMAN_PUBLIC_DEMO=1
   HITMAN_TEXT_PROVIDER=gemini
   ```

   Keep your existing valid `GEMINI_API_KEY` and model configuration. The Tavily API key is for search only, Gemini remains the AI answer model. For localhost use `APP_ENV=development`, `COOKIE_SECURE=0`.

5. Restart the server:

   ```powershell
   .\.venv\Scripts\python.exe check_v12_setup.py
   .\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Open http://127.0.0.1:8000 and ask `today cricket updates`. Sources should be shown when Tavily returns results. Do not assume snippets are whole-article fact checking. The model must still have free quota for generating the answer.

## Cost, privacy and limitations

- Tavily Researcher free tier currently grants 1,000 credits/month, typically 1 per basic web search, without a credit card. See https://tavily.com/pricing .
- This is a **source retrieval integration**, not ChatGPT Pro services. It does not make a Gemini account's model or quota available for free. If plain Gemini calls fail, check the model, key, and quota separately.
- The app will not crawl arbitrary URLs; source cards use sanitised HTTPS links from Tavily. Search snippets are untrusted and may be inaccurate.
- This patch is for HITMAN AI **v12 as provided**. Do not apply unchanged over newer or independently modified versions without merging the changes.
- For a public Render service, protect API keys, add strong abuse controls, and confirm Tavily's licence and permitted usage.

## Tests

The two Tavily regression tests in `tests/test_v12_tavily.py` use a mocked provider; the full v12 suite plus those tests passed locally (**94 tests**). No real Tavily or Gemini API calls were made. For a local run with pytest installed, from project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Official Tavily search API: https://docs.tavily.com/documentation/api-reference/endpoint/search
