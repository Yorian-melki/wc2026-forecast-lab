# ML Ensemble Probability Delta — Elo-only vs ML-ensemble

Generated: 2026-06-13T16:07:03 · N=100,000 · seed=20260613 (same seed both runs)
Ensemble: 0.5 Elo-Poisson + 0.5 ML logistic, reweighting DC scoreline W/D/L marginals.
use_ml active: True

**Max |champion Δ|: 1.861 pp**

| Team | Champ Elo-only | Champ ML-ens | Δpp | Final Δpp |
|---|---|---|---|---|
| ESP | 17.30% | 19.16% | +1.861 | +2.552 |
| ARG | 14.84% | 16.06% | +1.220 | +1.942 |
| FRA | 9.65% | 10.69% | +1.036 | +1.819 |
| ENG | 6.89% | 7.03% | +0.137 | +0.719 |
| BRA | 5.60% | 5.65% | +0.053 | +0.319 |
| POR | 4.91% | 4.93% | +0.022 | +0.065 |
| COL | 4.74% | 4.67% | -0.069 | +0.183 |
| NED | 3.22% | 3.23% | +0.012 | +0.106 |
| ECU | 3.21% | 3.02% | -0.188 | -0.131 |
| GER | 3.08% | 2.92% | -0.165 | -0.075 |
| MEX | 2.78% | 2.28% | -0.499 | -0.777 |
| JPN | 2.36% | 2.23% | -0.127 | -0.166 |

## Conservation check
- Σ champion (elo-only) = 1.00000
- Σ champion (ml-ens)  = 1.00000

## Interpretation
ML is more decisive on large Elo gaps, so favorites gain champion share and longshots lose it. Scoreline structure (goal diff, draws) is preserved — only W/D/L marginals are reweighted. Rollback: set use_ml_match_model=false in data/model_stack_config.json (or use_ml=False).