# Market Baseline Audit (TheStatsAPI odds)

Generated 2026-06-13T16:08:32 · 4 completed WC2026 matches · **benchmark only, not integrated**

| Match | Actual | Market (H/D/A) | Model ML-ens | Max disagree | Model H | Mkt H |
|---|---|---|---|---|---|---|
| MEX-RSA | H | [0.671, 0.219, 0.11] | [0.731, 0.174, 0.096] | 0.06 | 0.731 | 0.671 |
| KOR-CZE | H | [0.368, 0.31, 0.319] | [0.388, 0.278, 0.334] | 0.033 | 0.388 | 0.368 |
| CAN-BIH | D | [0.521, 0.275, 0.204] | [0.588, 0.233, 0.18] | 0.067 | 0.588 | 0.521 |
| USA-PAR | H | [0.466, 0.3, 0.237] | [0.292, 0.265, 0.443] | 0.206 | 0.292 | 0.466 |

**Brier vs actual** (lower=better): model ML-ens 0.6025, Elo-Poisson 0.5974, market 0.5089
**Confidence**: model mean entropy 0.9699 vs market 1.0041 → model is **overconfident** vs market
**Large disagreements (>0.15)**: ['USA-PAR']

## Decision

BENCHMARK ONLY — odds are NOT integrated into the model. 4 matches is far too few to justify market integration or recalibration. Used as a sanity check.

## Honest caveats

- 4 completed matches only — Brier comparison is anecdotal, not significant.
- 3/4 home teams are host nations (MEX/USA/CAN) so model applies a host boost.
- Market is a near-optimal baseline; model being close is reassuring, not proof of calibration.