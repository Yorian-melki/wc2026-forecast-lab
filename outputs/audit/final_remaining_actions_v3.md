# Remaining Actions v3

## Done this session
- TheStatsAPI ACTIVE + full extraction (shotmap xG, odds) with proof
- ML 1X2 model trained + gated (ACCEPTED, beats Elo-only held-out)
- Approved packages installed (sklearn/statsmodels/penaltyblog)
- xG comparison + ML gate surfaced on dashboard
- 533 tests pass

## Next (highest leverage)
1. **Wire ML 1X2 into the tournament sim** (group+KO) behind model_stack_config rollback flag; re-measure champion probs.
2. **Tournament-level walk-forward CV**: refit beta_elo per held-out tournament -> kills the circular WC2018/22 backtest.
3. **Market calibration**: compare model vs TSA de-vigged odds; apply calibration only if held-out ECE drops.
4. **statsmodels/penaltyblog goal model**: test Poisson/DC vs current; accept only if beats on held-out log-loss.
5. **beta_elo bootstrap CI** for parameter uncertainty.
