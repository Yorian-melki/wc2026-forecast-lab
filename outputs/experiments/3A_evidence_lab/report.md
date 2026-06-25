# Phase 3A — Evidence Lab: do pre-match features beat Elo-only? (offline, walk-forward OOS)

In-repo historical set (martj42 competitive 2010-2025). Walk-forward folds [2016, 2018, 2020, 2022, 2024] (train < y, test [y, y+1]); **pooled OOS n = 6,961**. Production `expected_goals` is **Elo-only**, so the baseline is a logistic/Poisson on `elo_diff` alone; the augmented model adds rolling form, goal rates, rest, and `elo_sum`. Features: ['elo_diff', 'elo_sum', 'gf_diff', 'ga_diff', 'form_diff', 'rest_diff', 'neutral'].

## Acceptance
A feature set **survives** only if OOS proper scores improve **beyond bootstrap noise** (95% CI of the per-match delta entirely < 0). W/D/L needs both log-loss AND RPS; the high-total lever needs total-goals Poisson deviance.

## OOS results (delta = augmented − baseline; negative = better)
| metric          |   baseline |   augmented |    delta |    ci_lo |    ci_hi |
|:----------------|-----------:|------------:|---------:|---------:|---------:|
| wdl_logloss     |    0.88134 |     0.87303 | -0.00831 | -0.01260 | -0.00410 |
| wdl_rps         |    0.17464 |     0.17211 | -0.00252 | -0.00365 | -0.00141 |
| wdl_brier       |    0.51819 |     0.51232 | -0.00587 | -0.00855 | -0.00322 |
| tot_poisson_dev |    1.36847 |     1.36527 | -0.00320 | -0.01310 |  0.00637 |
| tot_mae         |    1.47682 |     1.48105 |  0.00423 | -0.00287 |  0.01115 |

## Augmented W/D/L coefficients (standardised, last fold)
|         |   elo_diff |   elo_sum |   gf_diff |   ga_diff |   form_diff |   rest_diff |   neutral |
|:--------|-----------:|----------:|----------:|----------:|------------:|------------:|----------:|
| class_0 |      0.727 |    -0.030 |     0.132 |    -0.274 |      -0.178 |       0.028 |     0.067 |
| class_1 |      0.036 |     0.080 |    -0.017 |    -0.013 |      -0.026 |      -0.007 |    -0.004 |
| class_2 |     -0.763 |    -0.050 |    -0.115 |     0.287 |       0.204 |      -0.021 |    -0.064 |

## Verdict: **RESEARCH — partial OOS signal (W/D/L improves beyond noise; the other does not)**

_Offline research only. No production model/data/config/nav change. A surviving candidate would still require a separate, explicitly-approved Model-Lab integration phase._