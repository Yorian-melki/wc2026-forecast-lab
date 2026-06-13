# Model Stack — Final Decision

2026-06-13T16:20:11 UTC

## Selected mode
**Elo-Poisson/Dixon-Coles + xG live adjustment + ML ensemble @0.20 (rollback-enabled); market-benchmarked, NOT market-integrated**

## Components
- **Core**: CalibratedEloMatchModel (Elo->Dixon-Coles Poisson) — robust spine, KEPT
- **xG**: KEPT — bounded ±8 Elo/match, guardrail passed (0.2pp), live-conditioning only
- **ML ensemble**: INTEGRATED @ weight 0.2. Match-level: Brier 0.508<0.529 (leak-free 3580 matches). Tournament walk-forward (WC2018+WC2022, per-cutoff retrained ML): aggregate champ Brier improves but w=0.5 OVERCONCENTRATES (hurts WC2018 upset). Robust choice = 0.20. Rollback: use_ml_match_model=false reverts to Elo-only
- **Market odds**: BENCHMARK_ONLY — 4 WC2026 matches only; model slightly overconfident vs market (entropy 0.970 vs 1.004); not enough to justify integration

## Why not more complex
w=0.5 ML and market integration were both REJECTED on evidence/robustness grounds, not adopted by default. The chosen stack is the best evidence/robustness tradeoff.

## Honest caveats
- Tournament validation = 2 tournaments. Directional, not statistically powered.
- ML helps favorites, hurts upsets — 0.20 limits but does not eliminate this.
- beta sensitivity is HIGH (8.36pp) — forecast intervals should widen; no beta CI yet.
- Market integration deferred (4-match sample).
