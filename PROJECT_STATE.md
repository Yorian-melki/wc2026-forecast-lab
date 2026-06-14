# PROJECT_STATE — Single Source of Truth

> If you read one file, read this one. Last updated 2026-06-14 · commit `8484b07`+ (this org pass).
> Honest state, not marketing. For navigation start with `docs/FUTURE_AGENT_START_HERE.md`.

## A. Live / public state
| Thing | Live? | URL / note |
|---|---|---|
| GitHub repo | ✅ PUBLIC | https://github.com/Yorian-melki/wc2026-forecast-lab |
| Portfolio (Vercel) | ✅ LIVE | https://www.yorian-melki.com |
| Streamlit public app | ❌ NOT deployed | runs locally only; Render pending |
| wc2026.yorian-melki.com | ❌ NOT live | needs Render deploy + Spaceship CNAME |
| Render | ⚙️ blueprint ready (`render.yaml`) | not connected; CLI not installed; manual |
| DNS (Spaceship) | ⏳ pending | add CNAME `wc2026` AFTER Render gives target. DO NOT touch @ / www |

## B. Local state
- Path: `~/FinderProjects/wc2026_june2026`
- Run: `PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.port 8512 --server.headless false`
- Tested URL: http://localhost:8512 (HTTP 200)
- Latest commit: `8484b07` (Head-to-Head fix + live engine). This org pass adds docs + the upcoming/completed dedup fix.
- Tests: **571 passed** · py_compile OK · **AppTest: all 10 pages execute** (verified this session).

## C. Model state
- Core: Calibrated **Elo → Dixon-Coles Poisson** (β_raw 0.988 × temperature 0.55 = β_elo 0.544).
- **ML 1X2 ensemble ACCEPTED** (leak-free Brier 0.508 vs 0.529) and **wired into the tournament sim**, reweighting Dixon-Coles W/D/L marginals.
- **ML weight = 0.20** (cut from 0.50 by tournament walk-forward; 0.50 over-concentrated favorites).
- Tournament validation: **WC2010 / 2014 / 2018 / 2022** (leak-free, ML retrained per cutoff).
- **Champion probability intervals** exist (β_elo bootstrap; a FLOOR — sampling only, not total uncertainty).
- Market odds = **benchmark / control layer, NOT blended** into the model by default.
- **Dynamic upset-robust ML** mode exists (`ml_weight_mode="dynamic"`) but is **NOT the default**.

## D. Provider state (all active locally with keys in .env)
| Provider | Supplies | Live update |
|---|---|---|
| API-Football | live score/events/lineups, today fixtures, finished | PRIMARY for live (`fixtures?live=all`) |
| TheStatsAPI | shotmap xG, odds, player stats, lineups, timeline, referee | extract scripts (not in live loop) |
| Highlightly | team xG / advanced stats | extract scripts |
| football-data.org | standings/scorers/fixtures | extract scripts |
| OpenFootball | fallback scores/schedule | fallback |
- **xG upstream caveat:** Highlightly ≈ TheStatsAPI team-xG (likely shared upstream) → NOT independent.
- **Fallback:** no `API_FOOTBALL_KEY` → live engine returns `ok=False` → app reads the committed static `data/wc2026_live.json`; never crashes.

## E. Dashboard pages (all WORKING — AppTest verified)
| Page | Status | Note |
|---|---|---|
| 🚀 Release Status | WORKING | v6 status summary |
| 🏆 Champion Tracker | WORKING | champion probs + intervals |
| ⚽ Live Standings | WORKING (product polish pending) | auto-refresh 45s; upcoming/completed dedup fixed this pass |
| 🎯 Match Predictor | WORKING | — |
| 🧬 Nation DNA | WORKING | — |
| ⚔️ Head-to-Head | WORKING | crash FIXED (was duplicate plotly `xaxis`) |
| 📜 Historical Records | WORKING | — |
| 🔮 Bracket Paths | WORKING | — |
| 🧮 Model Lab | WORKING | maturity gauge now v6 6.93 (was stale 5.25); some roadmap prose could be further refreshed |
| 📡 Data Quality | WORKING | provider status + audits |

## F. Known real issues (honest)
1. **Live Standings product quality** — functional but not "premium app" UX. (priority: HIGH product, not correctness)
2. **QAT–SUI duplicate** (finished match also under "Upcoming") — ROOT CAUSE: `upcoming_today` in the json wasn't pruned vs completed. **FIXED this pass** (upcoming now filtered against completed+live). Re-verify after any live edit.
3. **Model Lab** older tabs (Limitations/roadmap) still contain some pre-v6 prose; gauge is fixed but not every sentence.
4. **Stale legacy files retained** for history: `global_maturity_score.json` (5.25), `MODEL_CARD.md`/`MODEL_FREEZE.md` (P4), `session_handoff/`. See `docs/FILE_AUTHORITY_TABLE.md`.
5. **Live auto-refresh needs `API_FOOTBALL_KEY`** — on deploy without keys it shows the static snapshot.

## G. Manual patch history
- `app.py.bak_before_dashboard_hotfix` was created by a manual hotfix (matchId f-string + TheStatsAPI text). It is now **gitignored** (BACKUP_DO_NOT_USE). The real app.py was audited and the hotfix content reconciled/kept where correct.
- Other backups: `data/teams.csv.bak`, `data/*_BACKUP_PRE_P0.csv` — gitignored.

## H. Next actions (ranked)
1. **CRITICAL** — none blocking; app runs, tests pass, no secrets at risk.
2. **HIGH** — (a) polish Live Standings UX to product grade; (b) deploy live app on Render + add `wc2026` CNAME at Spaceship; (c) re-verify QAT–SUI fix on the running app.
3. **MEDIUM** — refresh remaining Model Lab Limitations/roadmap prose to v6; archive `session_handoff/`.
4. **LATER** — structural-uncertainty quantification (the real modeling cap); expand validation beyond 4 WCs.
