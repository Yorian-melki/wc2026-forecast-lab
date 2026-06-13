# Private File Manifest — must NOT push

## Secrets (NEVER push)
- `.env`
- `.env.backup.20260613_192400`
## Raw API responses (account-bound)
- `data/raw/provider_responses/**`
## Masked-fragment artifacts
- `outputs/audit/*.json`
- `outputs/audit/*.csv`
- `outputs/audit/thestatsapi_*`
- `data/live/thestatsapi_*.json`
- `data/live/*odds*.json`
## Generated / heavy
- `.venv/ (938M)`
- `__pycache__/**`
- `outputs/*.json`
- `outputs/*.csv`
- `outputs/tournament_run/**`
- `outputs/live/** (regenerated)`
## Review-before-publish (optional)
- `API_NOTES.md (endpoint notes, no keys — optional)`
- `session_handoff/** (internal notes — keep local)`
- `ui/** (review)`

> All of these are covered by `.gitignore` (secrets, raw responses, masked-fragment artifacts, generated/heavy files). `session_handoff/` and `API_NOTES.md` are local-only by choice.
