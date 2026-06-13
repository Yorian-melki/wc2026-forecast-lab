# Data Source Audit — P2

## Source
GitHub: martj42/international_results

## Raw Dataset
- URL: https://raw.githubusercontent.com/martj42/international_results/master/results.csv
- Rows: 49,450
- Date range: 1872 → 2026

## Processed Dataset (Full 1990-2025)
- Matches: 31975
- Teams: 326
- Tournaments: 145
- Neutral games: 28.1%
- Post-2000: 25031
- Post-2010: 15505
- Competitive post-2010: 10638
- Mean home goals: 1.652
- Mean away goals: 1.108

## Processed Dataset (Competitive 2010-2025)
- Matches: 10555
- Teams: 293
- Competitive post-2010: 10555

## Mapping Failures
All 48 WC2026 teams match exactly by name (0 failures).
For non-WC2026 teams: used as-is (full name as identifier for rolling Elo).

## Training Split Strategy
No leakage: rolling Elo fitted only on data BEFORE test period start date.
