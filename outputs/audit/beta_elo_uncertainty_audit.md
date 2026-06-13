# beta_elo Uncertainty & Sensitivity Audit

Generated 2026-06-13T16:14:47 · fitted beta_elo=0.543593 · N=30000/config

## Leakage assessment

- **WC2026 forecast**: NOT leakage — beta fit on 2010-2025; WC2026 is in the future.
- **WC2018/2022 backtest**: PARTIAL leakage — beta fit on full history incl. post-tournament; absolute backtest Brier mildly optimistic (~5%). Walk-forward ML-weight comparison holds beta FIXED, so that comparison is unaffected.
- **Era stability**: NOT re-fit per era this batch (compute cost). Beta era-stability remains an open verification item.

## Champion-prob sensitivity to beta (±25%) — level: HIGH

| Team | fitted | β=0.4077 | β=0.4892 | β=0.5436 | β=0.598 | β=0.6795 | range pp |
|---|---|---|---|---|---|---|---|
| ESP | 16.8% | 12.9% | 15.5% | 16.8% | 18.5% | 21.3% | 8.36 |
| ARG | 14.8% | 11.8% | 13.5% | 14.8% | 15.7% | 17.5% | 5.68 |
| FRA | 9.7% | 8.2% | 9.0% | 9.7% | 10.7% | 11.4% | 3.14 |
| ENG | 6.8% | 6.3% | 6.1% | 6.8% | 7.0% | 7.4% | 1.24 |
| BRA | 5.7% | 5.6% | 5.5% | 5.7% | 5.6% | 5.6% | 0.2 |
| COL | 4.9% | 4.8% | 4.8% | 4.9% | 4.9% | 4.6% | 0.28 |
| POR | 4.9% | 4.9% | 4.6% | 4.9% | 4.7% | 4.6% | 0.29 |
| GER | 3.2% | 3.2% | 3.3% | 3.2% | 2.8% | 2.7% | 0.6 |

A +/-25% beta shift moves the top favorite's champion probability by up to 8.36pp (ESP: 12.9% -> 21.3%). Sensitivity is HIGH: beta uncertainty is a FIRST-ORDER forecast-uncertainty source, not negligible.

## Recommendation

Champion probabilities must NOT be presented as point-precise. A bootstrap CI on beta (not yet implemented) should widen reported intervals. This is now the top remaining hard-cap item for uncertainty quantification.