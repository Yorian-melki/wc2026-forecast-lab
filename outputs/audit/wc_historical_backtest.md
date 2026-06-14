# WC Historical Backtest — Calibrated Elo Model

Generated: 2026-06-14  |  Elapsed: 134s

## Methodology

- **Model**: CalibratedEloMatchModel  
- **β_elo**: 0.543593  
- **log_base**: 0.262464  
- **ρ** (Dixon-Coles): -0.021  
- **Elo source**: martj42 results.csv rolling Elo (eloratings.net K-factors)  
- **Simulations**: 100,000 per tournament  

> ⚠️ **Known limitation**: beta_elo fit on 2010-2025 full data — includes post-WC2022 matches. This makes backtest partially optimistic (~5% Brier improvement estimate). Full walk-forward cross-validation not performed.

## Brier Scores by Tournament

| Tournament | Group | SF | Champion | Model Pick | Actual | Rank |
|---|---|---|---|---|---|---|
| FIFA World Cup 2022 | 0.2132 | 0.0967 | 0.0222 | ARG (19.3%) | ARG (19.3%) | #1 |
| FIFA World Cup 2018 | 0.1785 | 0.1046 | 0.0304 | BRA (19.4%) | FRA (5.6%) | #5 |
| **Uniform 1/48 null (champion)** | — | — | 0.0204 | — | — | — |

## Combined

- Average champion Brier: **0.0263**
- Uniform 1/48 null (champion): **0.0204** — the honest no-information baseline (mean-Brier over 48 teams, not a 0.50 coin-flip).
- Champion-level Brier is on par with that null; the model's discrimination is at group/round granularity. n=2 tournaments — a track record, not a skill guarantee.
- Actual champion ranks: {'wc2022': 1, 'wc2018': 5}

## Top 10 Champion Probabilities

### FIFA World Cup 2022

| # | Team | Prob | Outcome |
|---|---|---|---|
| 1 | ARG | 19.3% | **CHAMPION** |
| 2 | BRA | 18.2% |  |
| 3 | ESP | 7.2% |  |
| 4 | NED | 7.2% |  |
| 5 | FRA | 6.7% |  |
| 6 | BEL | 5.3% |  |
| 7 | POR | 4.4% |  |
| 8 | ENG | 3.5% |  |
| 9 | URU | 3.5% |  |
| 10 | DEN | 3.2% |  |

### FIFA World Cup 2018

| # | Team | Prob | Outcome |
|---|---|---|---|
| 1 | BRA | 19.4% |  |
| 2 | ESP | 11.1% |  |
| 3 | ARG | 9.4% |  |
| 4 | GER | 8.2% |  |
| 5 | FRA | 5.6% | **CHAMPION** |
| 6 | POR | 5.5% |  |
| 7 | ENG | 5.3% |  |
| 8 | BEL | 4.9% |  |
| 9 | PER | 4.8% |  |
| 10 | COL | 4.4% |  |

## Interpretation

Because this Brier is averaged over 48 teams, the no-information baseline is the uniform
1/48 null (~0.0204), not a coin-flip baseline. At champion granularity the model sits on that
null — it does not reliably pinpoint the single winner. Its useful discrimination is at the
group/round level, where each stage has many positive teams. Two backtested tournaments are a
track record, not a skill guarantee; a single upset (FRA 2018) is expected.