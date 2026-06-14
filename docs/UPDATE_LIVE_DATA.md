# Update Live Data

## Automatic (in-app)
The Live Standings page auto-fetches every `LIVE_REFRESH_SECONDS` (45) when `API_FOOTBALL_KEY` is set.
`src/wc2026/live_engine.py`:
- `fetch_live_state()` → live + finished WC2026 matches (API-Football), groups resolved from `groups.json`.
- `merge_and_persist()` → appends finished to `data/wc2026_live.json`, dedups by (home,away), recomputes standings.
Failure-safe: any provider error → keeps last snapshot, no crash.

## Manual
```bash
PYTHONPATH=src .venv/bin/python scripts/update_live_data.py
```
Writes `data/wc2026_live.json` + `data/live/*`. Needs provider keys in `.env`.

## Known caveat
The persisted `upcoming_today` can hold finished matches; the app filters them out at render time
(QAT–SUI fix). A future improvement: prune `upcoming_today` inside `merge_and_persist`.
