# Reproducibility Pack

Generated 2026-06-13T17:17:37 UTC

## One command (full regenerate, ~16 min)
```
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py --full
```

## Fast smoke check (<60s)
```
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py
```

**Smoke pass:** True · conservation Σχampion=1.0 · ML active=True

## Reproducibility model
- **Forecast + validation reproduce fully OFFLINE** from committed data (martj42 results.csv, frozen params, saved live snapshot). No API keys needed.
- **Live API keys** only refresh provider data (scores/xG/odds). Listed in `.env.example`.

## Pipeline (offline)

| Step | Command | ~sec |
|---|---|---|
| ml_gate | `PYTHONPATH=src .venv/bin/python scripts/train_ml_match_model.py` | 5 |
| ml_ensemble_compare | `PYTHONPATH=src .venv/bin/python scripts/run_ml_ensemble_comparison.py --n 100000` | 240 |
| tournament_walkforward | `PYTHONPATH=src .venv/bin/python scripts/run_tournament_walkforward_validation.py --n 30000` | 240 |
| expanded_validation | `PYTHONPATH=src .venv/bin/python scripts/run_expanded_validation_and_dynamic_ml.py --n 30000` | 280 |
| beta_intervals | `PYTHONPATH=src .venv/bin/python scripts/run_beta_uncertainty_intervals.py --b 300 --n 50000` | 190 |

**Expected tests:** 558 passed (PYTHONPATH=src .venv/bin/python -m pytest tests/ -q)

## Inputs

- `data/external/international_results/results.csv`
- `data/elo_calibrated_params.json`
- `data/groups.json`
- `data/teams.csv`
- `data/model_stack_config.json`
- `data/xg_adjustment_config.json`

## Outputs

- `outputs/audit/ml_validation_report.json`
- `outputs/audit/tournament_walkforward_validation.json`
- `outputs/audit/expanded_tournament_validation.json`
- `outputs/audit/beta_uncertainty_bootstrap.json`
- `data/live/champion_probability_intervals.json`
- `outputs/audit/model_stack_final_decision.json`