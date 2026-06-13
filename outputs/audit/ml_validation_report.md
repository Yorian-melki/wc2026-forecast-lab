# ML Validation Report (Phase 7)

Generated: 2026-06-13T13:16:50 · split: train≤2018, test 2019-2022 (leak-free)
Features: ['elo_diff', 'neutral_int'] · model: multinomial logistic regression

| Model | Brier | NLL | ECE | Acc | n |
|---|---|---|---|---|---|
| random | 0.66667 | 1.09861 | 0.0 | 0.486 | 3580 |
| Elo-only | 0.52903 | 0.89954 | 0.0541 | 0.6064 | 3580 |
| **ML** | 0.50847 | 0.86663 | 0.00845 | 0.6059 | 3580 |
| ML+isotonic | 0.50844 | 0.86714 | 0.00855 | 0.6056 | 3580 |

## Gate: **ACCEPTED**
ML beats Elo-only on Brier (0.50847 < 0.52903) and NLL (0.86663 < 0.89954) on held-out 3580 matches.

## Calibration
Isotonic reduces ECE: **False** → reject isotonic (no ECE gain)

## Honest notes
- Elo-only baseline uses the SAME pre-match elo_diff feature -> fair test of learned vs hand-set mapping.
- Features are intentionally lean (elo_diff, neutral) to avoid overfitting.
- Test set is strictly after train -> no temporal leakage.
- This validates a single-match 1X2 model, NOT the tournament Monte Carlo directly.
