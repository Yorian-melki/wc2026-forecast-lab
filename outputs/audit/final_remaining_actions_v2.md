# Remaining Actions v2

## User (external, blocking)
1. **TheStatsAPI**: activate plan / regen key (see thestatsapi_resolved_probe.md). Until then, no per-shot xG.

## Claude (next dedicated session)
2. **Phase 5 — Validation**: install scikit-learn; walk-forward CV refitting beta_elo per held-out tournament; compute ECE/reliability; compare vs Elo-only + random + (if available) market baselines. Replaces the circular WC2018/22 backtest.
3. **Phase 6 — ML gate**: logistic + HistGradientBoosting 1X2 on martj42 features; accept ONLY if beats Elo on held-out Brier/logloss; isotonic calibration if it cuts ECE; else write 'ML rejected'.
4. **Phase 4 — Math reaudit**: formal writeup of beta_elo temperature heuristic, Wilson CI scope, K_FACTOR=40 arbitrariness, penalty/third-place variance.
5. **Phase 9 — Dashboard**: full score-only vs xG-adjusted toggle + validation scorecard surface.
