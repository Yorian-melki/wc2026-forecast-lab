# beta_elo Uncertainty Bootstrap -> Champion Intervals

Generated 2026-06-13T16:35:31 · 10,555 matches · B=300 bootstrap · N=50,000/band

## Bootstrap beta_elo (iid match resample)
- point fit: **0.9884** (production uses 0.543593)
- P5 / P50 / P95: **0.5285 / 0.5433 / 0.5550**  ·  SE 0.0077  ·  90% CI width 0.0265

## Champion probability intervals (top 12)

| Team | low (P5) | base (P50) | high (P95) | width pp |
|---|---|---|---|---|
| ESP | 18.66% | 19.02% | 19.28% | 0.618 |
| ARG | 15.82% | 15.67% | 16.10% | 0.28 |
| FRA | 10.44% | 10.78% | 10.86% | 0.422 |
| ENG | 7.01% | 7.11% | 7.13% | 0.124 |
| BRA | 5.59% | 5.60% | 5.71% | 0.122 |
| POR | 4.64% | 4.87% | 4.82% | 0.176 |
| COL | 4.70% | 4.70% | 4.89% | 0.19 |
| NED | 3.15% | 3.29% | 3.15% | 0.002 |
| ECU | 3.04% | 3.11% | 3.06% | 0.022 |
| GER | 2.83% | 2.94% | 2.94% | 0.11 |
| NOR | 2.25% | 2.24% | 2.28% | 0.03 |
| JPN | 2.16% | 2.14% | 2.18% | 0.012 |

## Honest caveats

- SAMPLING uncertainty on beta is SMALL (10.5k matches pin it well) — narrow intervals. This is NOT the same as the +/-25% sensitivity STRESS TEST (which moved ESP ~8pp); that stress test asks 'what if beta were badly wrong', not 'what does the data support'.
- iid match bootstrap ignores cross-match dependence -> LOWER bound on parameter uncertainty.
- These bands capture beta SAMPLING error only. They EXCLUDE the dominant uncertainties: temperature_mul calibration choice (0.55, not bootstrapped), structural/model error, and small-tournament variance. Treat as a floor on true forecast uncertainty.
- Monte Carlo noise (~0.1pp) is separate and additional. Intervals are on the unconditioned pre-tournament forecast.