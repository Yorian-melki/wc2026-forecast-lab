# Final Maturity Score v2

**Before: 5.21 → After: 5.5** (Δ +0.29)

Grade: still D+/C- by quant-fund standards. Honest bump from data_quality + claims_honesty + test_quality only.

## Changed dimensions (justified)
| Dimension | Before | After | Why |
|---|---|---|---|
| data_quality | 6.0 | 7.0 | TSA resolved; 3 live providers proven, raw saved |
| claims_honesty | 7.5 | 8.5 | TSA proof + xG labeled live-only + guardrail |
| test_quality | 4.5 | 5.5 | +17 real tests (521 total) |
| feature_engineering | 3.5 | 4.0 | bounded xG adjustment (small) |
| uncertainty_quantification | 3.0 | 3.5 | guardrail sensitivity bound |

## UNCHANGED (the binding cap)
- validation_methodology: 2.5 (no walk-forward CV run)
- calibration_quality: 3.0 (no calibration layer applied)
- parameter_estimation: 3.5 (no beta_elo CI)

## Hard cap
Capped ~5.5 because validation_methodology (2.5) and calibration_quality (3.0) are UNCHANGED this session. No walk-forward CV was run, no ML model trained/validated, no calibration layer applied. beta_elo CI still absent. These are the binding constraints; until they move, global maturity cannot exceed ~6.

## What moves it higher
- Walk-forward CV refitting beta_elo per held-out year (validation 2.5->5+)
- Train + gate an ML 1X2 model vs Elo baseline on martj42 (feature_engineering, model_selection)
- Apply isotonic/Platt calibration if it reduces held-out ECE (calibration 3.0->5+)
- Bootstrap CI on beta_elo (uncertainty_quantification)
- Attach TheStatsAPI plan -> per-shot xG -> xG cross-validation (data_quality)
