# HITMAN AI v11 — Tested change log

| Area | Root cause in v10 | Updated behavior |
|---|---|---|
| Today's cricket/news requests | Chat standard mode never used Google Search | Local opt-in `GEMINI_ENABLE_SEARCH=1` AND `HITMAN_AUTO_WEB_SEARCH=1` routes fresh questions to a real search-grounded Gemini request |
| "Give updates" follow-ups | No history-based search routing | Conservatively checks recent user question context |
| Search availability | Hidden tools with no obvious status | Shows grounding availability in guest chat |
| Search failures | Generic error only | Distinguishes common quota, unsupported model, and grounding issues without exposing keys |
| Attachment without prompt | JS returned early | Adds a file analysis question automatically |
| PDF scans | Required extractable PDF text | Native Gemini PDF document input; up to 12 pages |
| ZIP code review in chat | Browser rejected all ZIP uploads | Bounded static archive inspection; never executes uploaded code |
| Larger file upload | Hardcoded public size limit | Local 4 MB opt-in, while production retains 1.2 MB |
| Larger source ZIP | 250 KB cap for all modes | Local 2 MB opt-in, production 250 KB; caps extracted text, rejects known secrets |
| Browser file read errors | Could leave send disabled | Resets composer and provides error message |
| Installing on Windows | Previous ZIP had a nested folder | Full ZIP now contains files at its root, with a folder check in the quick start |

**Not verified:** real Gemini API grounding, billing, image creation, live voice, code execution in Docker, live Render service or all possible browsers. **No claim of exact ChatGPT Pro equivalence.**
