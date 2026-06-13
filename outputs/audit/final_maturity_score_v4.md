# Final Maturity Score v4

**5.21 -> 6.18** (Δ +0.97)

## Changed this batch (justified)
| Dimension | v3-era | v4 | Why |
|---|---|---|---|
| validation_methodology | 4.5 | 6.0 | Clean leak-free tournament walk-forward (per-cutoff ML retrain) |
| model_selection_rigor | 6.5 | 7.0 | ML weight chosen by evidence; overconcentration caught & weight cut 0.5→0.2 |
| uncertainty_quantification | 3.5 | 4.5 | beta HIGH sensitivity (8.36pp) quantified; market overconfidence measured |
| calibration_quality | 4.5 | 5.0 | market baseline comparison |
| parameter_estimation | 3.5 | 4.0 | beta leakage assessed + sensitivity mapped |
| claims_honesty | 8.5 | 9.0 | surfaced ML-hurts-upsets, beta-HIGH, USA underrating |

## Hard cap
~6.5: (1) tournament validation is only 2 WCs; (2) no beta bootstrap CI despite HIGH sensitivity; (3) ML still hurts on upsets; (4) market not integrated; (5) no per-era beta refit.

## Next unlocks
- Bootstrap CI on beta_elo -> widen forecast intervals (HIGH sensitivity makes this top priority)
- Expand tournament validation to WC2010/2014 + EUROs for a real sample
- Per-era beta refit to test stability
- Upset-robust ML: down-weight ML when Elo gap is large (where it overconcentrates)
