# Environment Variable Inventory

**NAMES ONLY — no secret values appear here or in any committed file.**
Source of truth: `.env` (gitignored as of this batch) and `.env.example` (template, no values).

| Variable | Needed for | Required to reproduce forecast? |
|---|---|---|
| `API_FOOTBALL_KEY` | API-Football live scores/events/lineups | No (live refresh only) |
| `API_FOOTBALL_HOST` | API-Football host (non-secret) | No |
| `THESTATSAPI_KEY` | TheStatsAPI shotmap xG + odds | No (live refresh only) |
| `HIGHLIGHTLY_API_KEY` | Highlightly xG/stats | No (live refresh only) |
| `HIGHLIGHTLY_BASE_URL` | Highlightly endpoint (non-secret) | No |
| `HIGHLIGHTLY_DOC_URL` | Highlightly docs (non-secret) | No |
| `FOOTBALL_DATA_ORG_KEY` | football-data.org standings/scorers | No (live refresh only) |
| `THESPORTSDB_API_KEY` | TheSportsDB metadata (low priority) | No |
| `PRIMARY_LIVE_PROVIDER` | provider routing (non-secret) | No |
| `LIVE_REFRESH_SECONDS` | refresh cadence (non-secret) | No |
| `LIVE_STRICT_SOURCE_LOG` | logging flag (non-secret) | No |
| `ALLOW_UNOFFICIAL_SCRAPERS` | scraper gate (non-secret) | No |

## Rules
- The **offline forecast + all validation reproduce with ZERO keys**. Keys are only for live refresh.
- On any host, set secrets in the host's env/secret store — never in the repo.
- `.env` is now gitignored; `.env.*` excluded except `.env.example`.
- For a public demo, deploy against the committed offline snapshot → **no keys deployed at all** (safest).

## Pre-commit / pre-deploy secret check
```bash
git check-ignore .env            # must print ".env"
# scan tracked files for assignment-style secrets (generic, no provider prefixes embedded here):
grep -rInE '(api[_-]?key|secret|token|bearer)[[:space:]]*[:=]' --exclude-dir=.venv . \
  | grep -v .env.example
```
