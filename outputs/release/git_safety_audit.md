# Git Safety Audit

Generated 2026-06-13T21:07:16 UTC

- **Is git repo:** No → clean start, no history to scrub.
- **Full-key scan:** CLEAN — no full API keys in any file type.
- **Masked fragments:** first6..last6 of 37-char keys appeared only in outputs/audit/thestatsapi_* and *.json (now all gitignored); not recoverable secrets.

## Sensitive files — ignore status

| File | Status |
|---|---|
| `.env` | ignored (.env) |
| `.env.backup.20260613_192400` | ignored (.env.*) — contains OLD real key, stays private |
| `.env.example` | TRACKED intentionally (template, no values) |
| `data/raw/provider_responses/` | ignored |
| `outputs/audit/*.json + *.csv` | ignored |
| `outputs/audit/thestatsapi_*` | ignored (masked fragments) |
| `data/live/thestatsapi_*.json + *odds*.json` | ignored |
| `.venv/` | ignored (938M) |

## Verify before any push

```
git check-ignore .env .env.backup.20260613_192400   # both must print
```
```
grep -rInE 'fapi_[A-Za-z0-9]{25,}|[a-f0-9]{64}' --exclude-dir=.venv .   # must be empty
```
```
git status --porcelain | grep -iE '\.env($|\.)' | grep -v example   # must be empty
```

**Verdict:** SAFE to initialize and push once .env/.env.backup remain untracked (verified by patterns).