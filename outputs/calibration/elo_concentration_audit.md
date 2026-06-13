# P3.5 Elo Concentration Audit

## Reference context
Historical WC pre-tournament top3 concentration (betting markets): ~36% average
  - WC2018: Brazil ~15%, Germany/Spain/France ~10% each → top3 ≈ 35%
  - WC2022: Brazil ~15%, Argentina ~11%, France ~11% → top3 ≈ 37%

## Concentration comparison

| Metric | Expert | Elo-calibrated | Target |
|:-------|:------:|:--------------:|:------:|
| top1 | 8.2% | **30.4%** | ≤20% |
| top3 | 23.3% | **66.4%** | ≤46% |
| top5 | 36.6% | **77.9%** | ≤60% |
| top10 | 56.3% | **91.2%** | — |
| entropy | 3.440 | 2.195 | ≥3.2 |
| entropy ratio | 0.889 | 0.567 | ≥0.82 |
| Herfindahl | 0.04231 | 0.17403 | — |

## Diagnosis
- **beta_elo = 0.988** fitted on competitive-only data (2010-2025)
- Over-amplifies Elo signal: ESP vs median → 3.15 vs 0.50 xG
- Top3 = **66.4%** vs historical reference 36%
- Root cause: competitive matches are more Elo-predictable,
  but WC simulation includes many mismatches (rank 5 vs rank 45)
- Fix: temperature-scale beta_elo down to match historical concentration