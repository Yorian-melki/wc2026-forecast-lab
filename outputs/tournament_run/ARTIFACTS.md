# `outputs/tournament_run/` — which file is which model

> Truth map for the simulation artifacts. **The dashboard displays only the CALIBRATED
> `live_*` files.** The generic-named `summary.*` files are the LEGACY EXPERT model and are
> kept only for offline demo scripts. Do not confuse them — they have a different favourite.

Two distinct models live in this folder:

- **Calibrated** = `CalibratedEloMatchModel` — Elo → Dixon-Coles Poisson + ML 1X2 ensemble @ weight 0.20
  (β_elo production 0.5436). **This is the public/displayed forecast.** Favourite: **ESP ~19%**.
- **Expert (legacy)** = `MatchModel` — hand-tuned analyst priors + StatsBomb features, zero MLE.
  **Not displayed.** Favourite: **FRA ~8%**.

| File | Model | Role | Displayed? | Produced by |
|---|---|---|---|---|
| `live_summary.csv` | **Calibrated** | champion/stage probs, live-conditioned + Wilson CIs | **YES** (Champion Tracker, Bracket Paths) | `scripts/run_live_simulation.py` |
| `live_stage_probs.csv` | **Calibrated** | per-stage advancement probs | **YES** | `scripts/run_live_simulation.py` |
| `live_group_position_probs.csv` | **Calibrated** | group-finish position probs | **YES** | `scripts/run_live_simulation.py` |
| `elo_calibrated_summary.csv` | **Calibrated** | pre-tournament (no live conditioning) | fallback only | `scripts/simulate_models.py` |
| `summary.csv` · `summary.json` | **Expert (legacy)** | generic-named expert output | **NO** | `python -m wc2026.cli simulate-tournament` (default `MatchModel`) |
| `expert_summary.csv` | **Expert (legacy)** | identical content to `summary.csv`; comparison baseline | **NO** (tab 2 "Expert vs Elo") | `scripts/simulate_models.py` |
| `stage_probs.csv` · `group_position_probs.csv` · `top_paths.json` | **Expert (legacy)** | expert sim by-products | **NO** | `python -m wc2026.cli simulate-tournament` |
| `bracket_difficulty.csv` · `death_group_scores.csv` | **Expert (legacy)** | derived from `summary.csv` | **NO** | `scripts/bracket_difficulty.py`, `scripts/death_group.py` |
| `model_delta_summary.csv` | both | expert-vs-calibrated delta | **NO** | `scripts/simulate_models.py` |
| `summary_p0.csv` | **Expert (P0-era)** | historical snapshot | **NO** | legacy |

## Why the expert files are kept (not deleted/renamed)
`summary.csv` is read by `src/wc2026/odds/fetcher.py`, `src/wc2026/odds/value_detector.py`,
`scripts/bracket_difficulty.py`, `scripts/death_group.py`, `scripts/odds_report.py`,
`scripts/generate_chart.py`. Renaming would break those offline demos. They are **labeled here**
instead. The app (`app.py: load_live_summary`) reads `live_summary.csv` → `elo_calibrated_summary.csv`
only — it deliberately **never** falls back to `summary.csv`, so the dashboard can never silently
display the expert model.

## Regenerate the displayed forecast (one command, offline)
```bash
PYTHONPATH=src python scripts/run_live_simulation.py
```
