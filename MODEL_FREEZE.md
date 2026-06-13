# MODEL FREEZE — WC2026 Forecast

**Freeze date:** 2026-06-10  
**Status:** FROZEN — do not change before publication

---

## Final selected model

**`elo_calibrated` (temperature-corrected)**

- File: `src/wc2026/calibrated_elo_model.py`
- Params: `data/elo_calibrated_params.json`
- beta_elo: **0.543593** (original: 0.988351, temperature_mul: 0.55)
- log_base: 0.226934 (base_xg: 1.2547 goals/team)
- rho (Dixon-Coles): −0.021007
- Fitted on: 10,555 competitive international matches, martj42 2010–2025

---

## Rejected models

| Model | Phase | Reason |
|:------|:-----:|:-------|
| Pure MLE Dixon-Coles | P1 | Did not beat Elo baseline on holdout NLL |
| Full Hybrid Elo-DC + residuals | P2.5 | ECE degraded 17% (0.0199 vs 0.0170). 0/4 clear-win splits. Gate: BORDERLINE_EXPERIMENTAL. 646 extra params add noise not signal. |
| Elo-calibrated (original, no temperature) | P3.5 | beta_elo=0.988 over-concentrates: top3=66.4% (expected ~40%). Corrected by temperature_mul=0.55. |

---

## Exact reproduction commands

```bash
# Install
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Run calibration (if params.json missing)
PYTHONPATH=src .venv/bin/python -c "
from wc2026.calibrated_elo_model import fit_elo_calibrated_params
fit_elo_calibrated_params(save=True, verbose=True)
"

# Run simulation
PYTHONPATH=src .venv/bin/python scripts/simulate_models.py \
  --model elo_calibrated --iterations 100000 --seed 20260609

# Run full audit
PYTHONPATH=src .venv/bin/python scripts/reproduce_public_outputs.py

# Run tests
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q \
  --ignore=tests/test_data_and_mapping.py
```

---

## Final output files

| File | Description |
|:-----|:-----------|
| `outputs/tournament_run/elo_calibrated_summary.csv` | 100K simulation results |
| `outputs/tournament_run/expert_summary.csv` | Expert model (reference) |
| `outputs/public/wc2026_final_forecast_chart.png` | Public chart |
| `outputs/public/model_selection_report.md` | Full model comparison |
| `outputs/public/technical_summary.md` | One-page technical summary |
| `outputs/calibration/ablation_results.csv` | P2.5 ablation (9 models, 4 splits) |
| `outputs/calibration/elo_calibration_gate.json` | P3.5 gate: PASS_WITH_TEMPERATURE |
| `outputs/calibration/elo_temperature_ablation.csv` | Beta shrinkage ablation |
| `data/model_freeze_manifest.json` | Machine-readable freeze state |

---

## Known limitations

1. Elo ratings frozen at last recorded match — no pre-tournament form update
2. beta_elo corrected via internal sanity audit (not external calibration dataset)
3. Does not model squad depth, injuries, or in-tournament events
4. Bracket path correlations not captured (groups treated independently)
5. Penalty win probability uses team skill proxies, not penalty shoot-out specialists data
6. Host nation advantage is a flat xG boost (+8%) — no granular crowd effect
7. Dixon-Coles rho=−0.021 (very small) — correction is near-negligible

---

## DO NOT CHANGE BEFORE PUBLICATION

- `beta_elo` in `data/elo_calibrated_params.json`
- `seed` (20260609) in any simulation rerun
- `iterations` (100,000) in any public simulation
- `data/external/international_results/results.csv` — source data is frozen
- `outputs/tournament_run/elo_calibrated_summary.csv` — frozen output

If any of the above must change, re-run the full P3.5 audit, update MODEL_FREEZE.md, and regenerate all public outputs.
