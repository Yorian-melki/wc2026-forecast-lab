# Dashboard Page Map

Generated 2026-06-14T00:19:03 UTC · app.py · selector at line 356 · all pages AppTest-verified WORKING

| Page | Line | Live API | Cache | Product /10 | Tech /10 | Known issue |
|---|---|---|---|---|---|---|
| 🚀 Release Status | 383 | no | yes | 8 | 9 | none |
| 🏆 Champion Tracker | 448 | no | yes | 8 | 9 | none |
| ⚽ Live Standings | 627 | YES (API-Football) | yes (cached_live_state ttl=45) | 6 | 8 | product polish pending; depends on API_FOOTBALL_KEY for auto-refresh |
| 🎯 Match Predictor | 778 | no | partial | 7 | 8 | none |
| 🧬 Nation DNA | 1038 | no | yes | 7 | 8 | none |
| ⚔️ Head-to-Head | 1353 | no | yes | 7 | 9 | FIXED: was crashing (duplicate xaxis) |
| 📜 Historical Records | 1449 | no | yes | 7 | 8 | none |
| 🔮 Bracket Paths | 1563 | no | yes | 7 | 8 | none |
| 🧮 Model Lab | 1691 | no | yes | 7 | 8 | maturity gauge now v6 (was stale 5.25); some roadmap text could be refreshed further |
| 📡 Data Quality | 1945 | no | yes | 8 | 9 | none |

## Per-page detail

### 🚀 Release Status  (app.py ~L383)

- Data: outputs/audit/final_maturity_score_v6.json, data/model_stack_config.json
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none

### 🏆 Champion Tracker  (app.py ~L448)

- Data: outputs/tournament_run/live_summary.csv (calibrated Elo→DC + ML@0.20 — the displayed forecast; NOT summary.csv, which is the legacy expert model), data/live/champion_probability_intervals.json
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none

### ⚽ Live Standings  (app.py ~L627)

- Data: wc2026_live.json (persisted), live providers via live_engine
- Modules: wc2026.live_engine
- Refresh: st.fragment run_every=45s when AUTO_LIVE · Cache: yes (cached_live_state ttl=45) · Live API: YES (API-Football)
- Known issues: product polish pending; depends on API_FOOTBALL_KEY for auto-refresh
- Next: UI/UX polish; richer live cards

### 🎯 Match Predictor  (app.py ~L778)

- Data: data/teams.csv, elo_calibrated_params.json
- Modules: wc2026.calibrated_elo_model
- Refresh: on input · Cache: partial · Live API: no
- Known issues: none
- Next: none

### 🧬 Nation DNA  (app.py ~L1038)

- Data: data/teams.csv, data/style_metrics.csv
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none

### ⚔️ Head-to-Head  (app.py ~L1353)

- Data: data/h2h_records.csv
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: FIXED: was crashing (duplicate xaxis)
- Next: none — crash fixed

### 📜 Historical Records  (app.py ~L1449)

- Data: data/wc_history.csv
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none

### 🔮 Bracket Paths  (app.py ~L1563)

- Data: outputs/tournament_run/*
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none

### 🧮 Model Lab  (app.py ~L1691)

- Data: outputs/audit/final_maturity_score_v6.json, outputs/calibration/*, ablation
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: maturity gauge now v6 (was stale 5.25); some roadmap text could be refreshed further
- Next: refresh remaining roadmap text to v6

### 📡 Data Quality  (app.py ~L1945)

- Data: data/live/provider_status.json, wc2026_live.json, outputs/audit/*
- Modules: -
- Refresh: on load · Cache: yes · Live API: no
- Known issues: none
- Next: none
