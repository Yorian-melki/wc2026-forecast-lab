# P3.5 Historical Tournament Concentration

Approximate champion concentration using WC2026-bracket simulation
with pre-tournament Elo snapshots for WC2018 and WC2022 teams.

Note: uses WC2026 48-team bracket structure as proxy (not exact WC32).

| tournament | beta_mul | beta_elo | top1 | top3 | top5 | entropy |
|:----------:|:--------:|:--------:|:----:|:----:|:----:|:-------:|
| WC2018_approx | 1.00 | — | 31.0% | **57.1%** | 73.1% | 2.314 |
| WC2018_approx | 0.55 | — | 16.2% | **35.6%** | 51.0% | 3.006 |
| WC2018_approx | 0.55 | — | 16.2% | **35.6%** | 51.0% | 3.006 |
| WC2022_approx | 1.00 | — | 30.5% | **61.6%** | 74.6% | 2.243 |
| WC2022_approx | 0.55 | — | 16.9% | **39.2%** | 51.1% | 2.995 |
| WC2022_approx | 0.55 | — | 16.9% | **39.2%** | 51.1% | 2.995 |

## Reference
WC2018 pre-tournament (betting): top3 ≈ 35%, top1 ≈ 15%
WC2022 pre-tournament (betting): top3 ≈ 37%, top1 ≈ 15%