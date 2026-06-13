# WC2026 Forecast — Technical Summary

**Model:** Elo-calibrated Poisson simulator (temperature-corrected)  
**Simulations:** 100,000 Monte Carlo · Seed: 20260609 · Date: 2026-06-10

---

## Dataset

- **49,450** international football match records (martj42, 1872–2025)
- **10,555** competitive matches used for Elo parameter calibration (2010–2025)
- 336 unique national teams in the full database

---

## Models tested

| # | Model | NLL vs baseline | ECE | Decision |
|:-:|:------|:---------------:|:---:|:--------:|
| A | Random baseline | +0.167 | — | Rejected |
| B | Empirical frequency | +0.126 | — | Rejected |
| C | Elo, no home adj. | +0.025 | — | Rejected |
| D | Elo + home adj. | +0.013 | — | Rejected |
| E | **Elo + calibrated draw** | **0 (reference)** | **0.0170** | ✓ Selected backbone |
| F | Independent Poisson (MLE) | +0.000 | — | Rejected (P1) |
| G | Elo + DC rho only | +0.000 | — | Marginal |
| H | Hybrid rho=0 | −0.001 | — | Not significant |
| I | Full Hybrid Elo-DC | −0.002 | **0.0199** | **Rejected — ECE +17%** |

*Ablation across 4 temporal splits, ~10,500 competitive matches per split.*

---

## Model selection rationale

**Key finding:** The biggest single model improvement was home advantage (+0.155 NLL avg). Everything beyond the calibrated draw baseline was statistically noise on 3 of 4 splits, and the Full Hybrid actively degraded calibration quality (ECE +17%).

**Rule applied:** Promote the most robust model, not the most complex.

---

## Final model specification

**Elo-calibrated Poisson with temperature correction**

```
log_μ_A = 0.2269 + 0.5436 × (Elo_A − Elo_B) / 400
log_μ_B = 0.2269 − 0.5436 × (Elo_A − Elo_B) / 400
```

With Dixon-Coles low-score correction (ρ = −0.021).

**Temperature correction:** Original beta_elo=0.988 (competitive-only training) produced over-concentration (top-3 = 66.4%). Shrinkage to 0.544 brings top-3 to 41.76%, consistent with pre-tournament Elo-snapshot simulations for WC2018 and WC2022.

---

## Concentration correction

| | Before | After |
|:--|:------:|:-----:|
| Top-1 (ESP) | 30.4% | **17.0%** |
| Top-3 | 66.4% | **41.8%** |
| Top-5 | 77.9% | **54.2%** |

---

## Final top-10 forecast

| Rank | Team | P(champion) |
|:----:|:-----|:-----------:|
| 1 | ESP | 16.97% |
| 2 | ARG | 14.76% |
| 3 | FRA | 10.03% |
| 4 | ENG | 6.71% |
| 5 | BRA | 5.69% |
| 6 | COL | 4.82% |
| 7 | POR | 4.81% |
| 8 | NED | 3.30% |
| 9 | ECU | 3.09% |
| 10 | GER | 3.02% |

All probabilities verified: Σ = 1.000 (conservation law holds).

---

## Limitations

- Temperature correction validated internally only (not against external market data)
- Elo frozen at data cutoff — no real-time form update
- No injury / squad depth modeling
- Tournament bracket path correlations not captured

---

## Reproducibility

```bash
PYTHONPATH=src .venv/bin/python scripts/reproduce_public_outputs.py
```

All results deterministic from seed 20260609.
