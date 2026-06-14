# Live System — Truth Audit

> Honest answers about what the "live" system actually does. Updated 2026-06-14.

| Question | Answer |
|---|---|
| Truly live **locally**? | **Yes**, when `API_FOOTBALL_KEY` is in `.env`. The Live Standings page re-fetches every 45s via `st.fragment(run_every)`. |
| Live **publicly**? | **No.** The Streamlit app is not deployed yet. yorian-melki.com (portfolio) is live; the app is not. |
| Which providers are called live? | **API-Football** (`fixtures?live=all` + today + finished) via `ProviderRouter`. TheStatsAPI/Highlightly/FDO are used by extract scripts, not the live loop. |
| What file is persisted? | `data/wc2026_live.json` — `live_engine.merge_and_persist()` writes completed_matches + recomputed group_standings. |
| Auto-update without user action? | **Yes** — the fragment reruns on a timer; new finished matches are detected and merged automatically. |
| Is the refresh interval truthful? | **Yes** — `LIVE_REFRESH_SECONDS` (default 45). `cached_live_state` TTL matches, so the API is hit ~once per interval. |
| Does completed-match locking work? | **Yes** — finished (status FT/AET/PEN) matches are merged into `completed_matches`; standings recompute (3/1/0 pts). |
| Does upcoming filtering work? | **Now yes.** ROOT CAUSE of the QAT–SUI bug: `upcoming_today` in the json was not pruned against completed. **Fixed** — upcoming is filtered against `completed ∪ live` pairs in the fragment. |
| Can a match appear in both completed + upcoming? | **No longer** (post-fix). Re-verify after any change to the live fragment. |
| Group table basis | **Completed matches only** (final scores). Live in-progress matches show in the 🔴 banner but do NOT yet alter standings until full-time. |
| No `API_FOOTBALL_KEY`? | `AUTO_LIVE=False` → no auto-refresh, no API calls → app reads the committed static snapshot. No crash. |
| On Render with no env vars? | Same as above — static snapshot, "SNAPSHOT" badge shown. Add keys in Render env to enable live. |

## Root-cause record: QAT–SUI duplicate (FIXED)
`data/wc2026_live.json` carried `upcoming_today: [QAT-SUI, ...]` generated when QAT-SUI was a future fixture.
After it finished, `merge_and_persist` added it to `completed_matches` but left the stale `upcoming_today`.
The Live Standings page rendered both lists → the same match twice.
**Fix** (`app.py`, Live Standings fragment): `upcoming` is filtered to drop any pair already in `completed` or `live_now`.
**Residual risk:** the persisted `upcoming_today` is still stale on disk; the filter hides it at render time. A future improvement is to also prune `upcoming_today` inside `merge_and_persist`.

## Files
- Engine: `src/wc2026/live_engine.py` (`fetch_live_state`, `merge_and_persist`, `build_standings`) — failure-safe.
- App wiring: `app.py` Live Standings fragment (~L627) + `cached_live_state` (~L48) + `AUTO_LIVE`/`LIVE_REFRESH`.
- Manual refresh script: `scripts/update_live_data.py` (OpenFootball-primary; the in-app engine is the live path).
