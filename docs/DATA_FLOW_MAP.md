# Data Flow Map

Generated 2026-06-14T00:19:59 UTC

## Flows

### live_refresh
API-Football/TheStatsAPI/Highlightly/football-data.org → providers/router.py → live_engine.fetch_live_state() → merge_and_persist() → data/wc2026_live.json → Live Standings page (st.fragment 45s).

### offline_snapshot
No API key → live_engine returns ok=False → app reads committed data/wc2026_live.json (static). Never crashes.

### tournament_sim (the DISPLAYED forecast)
data/elo_calibrated_params.json + teams.csv + groups.json → **CalibratedEloMatchModel (+ ML 1X2 @ 0.20)** → `scripts/run_live_simulation.py` (live-conditioned on data/wc2026_live.json) → **outputs/tournament_run/live_summary.csv** (+ live_stage_probs.csv, live_group_position_probs.csv) → Champion Tracker / Bracket Paths.

⚠️ **Do not confuse models.** `outputs/tournament_run/summary.csv` & `summary.json` are the **LEGACY EXPERT (analyst-prior) model** — a *different* favourite (FRA ~8% vs the displayed ESP ~19%). They are **NOT displayed**; they only feed the offline odds/value-detector demo scripts. The dashboard reads `live_summary.csv` only. Full per-file map: `outputs/tournament_run/ARTIFACTS.md`.

### ml_validation
martj42 results.csv → ml/features+train_match_model → outputs/audit/ml_validation_report.* (Brier 0.508).

### tournament_validation
results.csv → run_expanded_validation_and_dynamic_ml.py (WC2010/14/18/22) → outputs/audit/expanded_tournament_validation.*

### uncertainty_intervals
results.csv → run_beta_uncertainty_intervals.py (bootstrap) → data/live/champion_probability_intervals.json → Champion Tracker/Release Status.

### market_flags
TheStatsAPI odds → de-vig → data/live/market_disagreement_flags.json → Data Quality.

### maturity
manual per-dimension → outputs/audit/final_maturity_score_v6.json → Model Lab gauge + sidebar.

## Key artifacts

| Path | Produced by | Consumed by | Authority | Manual-edit safe? |
|---|---|---|---|---|
| `data/wc2026_live.json` | live_engine.merge_and_persist / update_live_data.py | Live Standings, Data Quality | AUTHORITATIVE/RUNTIME | no — app overwrites |
| `data/groups.json` | manual | live_engine, tournament, validation | AUTHORITATIVE | yes carefully |
| `data/live/*` | provider extract scripts | Data Quality | mixed | no |
| `outputs/audit/final_maturity_score_v6.json` | manual (this session) | Model Lab, Release Status | AUTHORITATIVE_GENERATED | via script only |
| `outputs/audit/global_maturity_score.json` | old baseline | (legacy) | LEGACY | NO |
| `render.yaml` | manual | Render deploy | DEPLOYMENT | yes |
| `.env.example` | manual | template | DEPLOYMENT | yes |