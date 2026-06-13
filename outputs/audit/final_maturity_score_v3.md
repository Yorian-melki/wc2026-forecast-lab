# Final Maturity Score v3

**5.21 → 5.86** (Δ +0.65)

## Changed dimensions (justified)
| Dimension | Before | After | Why |
|---|---|---|---|
| data_quality | 6.0 | 7.5 | TSA S-tier active: per-shot shotmap xG + real odds |
| validation_methodology | 2.5 | 4.5 | Real leak-free held-out 1X2 vs baselines (single-match) |
| calibration_quality | 3.0 | 4.5 | ML ECE 0.008 measured; isotonic tested+rejected |
| model_selection_rigor | 6.0 | 6.5 | ML-vs-Elo hard gate |
| feature_engineering | 3.5 | 4.5 | leak-free rolling-Elo features + xG adj |
| test_quality | 4.5 | 5.5 | 533 tests |
| claims_honesty | 7.5 | 8.5 | upstream-overlap + not-wired caveats |
| uncertainty_quantification | 3.0 | 3.5 | xG guardrail + held-out variance |

## Hard cap
~6: ML validated but NOT integrated into the tournament sim; tournament-level walk-forward CV still absent; beta_elo CI absent.

## Next unlocks
- Wire ML 1X2 into group/KO sim with rollback
- Tournament-level walk-forward CV (refit beta per held-out year)
- Market calibration vs TSA odds
- beta_elo bootstrap CI
