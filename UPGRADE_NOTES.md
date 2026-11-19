# HITMAN AI v3 — Upgrade changelog

## Added
- Public signup with required email verification and resend endpoint
- Login throttling, token expiry and single-use password recovery
- User-scoped chat, persistent memory and downloadable artifacts
- Encrypted GitHub token storage and private repository listing/source import
- Draft pull request publishing via new branch (no direct default-branch writes)
- Dependency-aware Docker test workflow; network enabled only during optional restricted dependency installation stage
- Bounded AI auto-debug/test-feedback loop with review-and-approve guardrail
- VS Code debugging profile, setup script, configuration guide
- Per-user daily request caps and important HTTP security headers

## Verified offline
- 11 automated tests (provider, SMTP, GitHub and Docker operations mocked)
- Python source compilation, JavaScript syntax, ZIP integrity

## Not verified / not implemented
- Live OpenAI/GitHub/SMTP credentials, real Docker images/runtime, HTTPS hosting
- Full ChatGPT Pro proprietary features or billing entitlements
- Full GitHub administration, arbitrarily large repository management, automatic merges, autonomous deployment
- Public-cloud security certification, distributed session storage, advanced production sandboxing, MFA

## Migration notes
- Back up `chats.db` before using the updated code against an old installation.
- SQLite migrations add email and ownership columns. Existing users without an email are allowed to sign in, and legacy unowned chats/memories are not exposed to members.
- Configure SMTP and HTTPS before public deployment; do not use console email delivery online.
- `GITHUB_TOKEN_ENCRYPTION_KEY` must be generated privately; tokens are not stored in ZIP/README/.env.example.
