# Data Lineage Map

Generated 2026-06-13T17:19:52 UTC — every major dashboard number traced to source.

| Number | Source file | Provider | Transformation | Caveat |
|---|---|---|---|---|
| Champion probability (base) | `outputs/live/ml_ensemble/stage_probs.csv` | internal (martj42 Elo) | run_ml_ensemble_comparison.py → CalibratedEloMatchModel(ML@0.20) | Monte Carlo 100k; ML-ensemble reweighted |
| Champion probability interval (P5/P50/P95) | `data/live/champion_probability_intervals.json` | internal | run_beta_uncertainty_intervals.py (beta bootstrap) | beta SAMPLING uncertainty only — a FLOOR |
| xG live adjustment | `data/live/xg_adjustment_log.json` | Highlightly | run_xg_comparison.py (bounded ±8 Elo) | live-conditioning only; not xG-trained |
| Shotmap xG (per-shot, x/y) | `data/live/thestatsapi_shotmap.json` | TheStatsAPI | direct extraction | same upstream as Highlightly (not independent) |
| Odds-implied 1X2 | `data/live/thestatsapi_odds_implied.json` | TheStatsAPI | de-vig (median of bookmakers) | 4 completed matches only |
| ML validation metrics (Brier/NLL/ECE) | `outputs/audit/ml_validation_report.json` | internal (martj42) | train_ml_match_model.py | leak-free held-out 2019-2022 (3580 matches) |
| Tournament validation (champ Brier) | `outputs/audit/expanded_tournament_validation.json` | internal (martj42) | run_expanded_validation_and_dynamic_ml.py | 4 WCs; beta fixed; per-cutoff ML |
| beta intervals | `outputs/audit/beta_uncertainty_bootstrap.json` | internal (martj42 1990-2025) | bootstrap 300x, temp-scaled | iid match bootstrap = lower bound |
| Provider agreement | `data/live/provider_status.json, provider_disagreements.json` | 4 live providers | update_live_data.py | 4 matches; 0 disagreements |
| Market disagreement flags | `data/live/market_disagreement_flags.json` | TheStatsAPI odds + internal model | market_disagreement_control | benchmark only, not blended |
| Maturity score | `outputs/audit/final_maturity_score_v5.json` | internal self-assessment | manual per-dimension | self-assigned, not externally reviewed |

## Root data sources

- **martj42/international-football-results** — 49,450 matches 1872-2025 (Elo, ML, validation). OFFLINE.
- **TheStatsAPI** — shotmap xG, odds, stats (live, key-gated).
- **Highlightly / API-Football / football-data.org** — xG / live / standings (live, key-gated).
- **frozen params** — data/elo_calibrated_params.json (beta_elo=0.5436 = 0.988 × temperature 0.55).