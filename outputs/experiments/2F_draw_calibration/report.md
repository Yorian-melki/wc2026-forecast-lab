# Phase 2F — Draw-calibration experiment (offline, walk-forward OOS)

In-repo historical set (martj42 2010-2025). Baseline = DC-implied W/D/L (no ML reweight — a documented simplification; the shipped calibrator, if any, sits after the ML step). Expanding walk-forward folds; **pooled OOS n = 5,713**. Overall draw rate 0.219 vs mean predicted P(draw) 0.255 (full-set). Fitted gamma per fold: 2018->0.84, 2020->0.82, 2022->0.84, 2024->0.84.

## Acceptance gate (pre-registered)
PASS only if OOS **RPS and NLL** both improve **beyond noise** (95% bootstrap CI of the per-match difference entirely < 0), AND Brier, ECE, outcome accuracy, home/away calibration, and the champion proxy (W/D/L mass shift ≤ 3%) do not regress materially.

## OOS metrics (lower better: rps/nll/brier/ece; gaps nearer 0 better)
| candidate   |    rps |    nll |   brier |    acc |    ece |   draw_gap |   home_gap |   away_gap |
|:------------|-------:|-------:|--------:|-------:|-------:|-----------:|-----------:|-----------:|
| baseline    | 0.1826 | 0.9104 |  0.5344 | 0.6049 | 0.0982 |    -0.0291 |     0.0335 |    -0.0044 |
| A_gamma     | 0.1812 | 0.9089 |  0.5313 | 0.6049 | 0.0726 |     0.0117 |     0.0104 |    -0.0221 |
| B_isotonic  | 0.1799 | 0.9096 |  0.5278 | 0.6041 | 0.0595 |     0.0225 |     0.0016 |    -0.0242 |

## Improvement vs baseline, with 95% bootstrap CI (negative = better)
- **A_gamma**: ΔRPS -0.00138 [-0.00166, -0.00109] · ΔNLL -0.00153 [-0.00399, +0.00106] · W/D/L mass shift 0.0408
- **B_isotonic**: ΔRPS -0.00274 [-0.00317, -0.00228] · ΔNLL -0.00078 [-0.00725, +0.00661] · W/D/L mass shift 0.0524

## Verdict
- **A_gamma**: INCONCLUSIVE/FAIL — RPS and/or NLL not beyond noise
- **B_isotonic**: INCONCLUSIVE/FAIL — RPS and/or NLL not beyond noise

_No production change. Shipping a passing calibrator would be a separate Phase 2G._