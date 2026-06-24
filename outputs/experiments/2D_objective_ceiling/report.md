# Phase 2D — Objective & Ceiling audit (offline, in-repo historical set)

Set: martj42 competitive 2010-2025, **10,555 matches** (production grid g=8, μ∈[0.15,3.6]). REAL = production Poisson+DC scored vs actual results. CEILING = analytic expectation if outcomes were drawn from the model itself (the best any model of THIS family could score). TRIVIAL = global base-rate / modal-score climatology.

> **In-sample caveat:** REAL here is in-sample (model fit on 2010-2025). It flatters the model, so if even in-sample REAL sits well below CEILING, that gap is genuine mis-specification; if REAL ≈ CEILING, the metric is at its irreducible floor for this family. CEILING is the key column.

## Proper scores & exact-score metrics: REAL vs CEILING vs TRIVIAL
| metric      |   trivial |   real |   real_ci_lo |   real_ci_hi |   ceiling |   unrealized_headroom_frac | verdict                                                                     |
|:------------|----------:|-------:|-------------:|-------------:|----------:|---------------------------:|:----------------------------------------------------------------------------|
| outcome_acc |    0.4746 | 0.5830 |       0.5739 |       0.5923 |    0.4847 |                     0.0000 | near ceiling — little recoverable headroom                                  |
| rps         |    0.2309 | 0.1929 |       0.1910 |       0.1947 |    0.2132 |                     0.0000 | near ceiling — little recoverable headroom                                  |
| brier_wdl   |  nan      | 0.5560 |       0.5512 |       0.5604 |    0.6154 |                   nan      | near ceiling — little recoverable headroom                                  |
| nll_wdl     |    1.0488 | 0.9414 |       0.9347 |       0.9477 |    1.0255 |                     0.0000 | near ceiling — little recoverable headroom                                  |
| exact_top1  |    0.1090 | 0.1183 |       0.1124 |       0.1245 |    0.1267 |                     0.4754 | REAL headroom — ~48% of trivial→ceiling span unrealized                     |
| exact_top3  |  nan      | 0.3308 |       0.3222 |       0.3398 |    0.3343 |                   nan      | AT CEILING — irreducible for this model family (not a recoverable weakness) |
| exact_top5  |  nan      | 0.5060 |       0.4965 |       0.5158 |    0.5039 |                   nan      | AT CEILING — irreducible for this model family (not a recoverable weakness) |
| mean_rank   |  nan      | 8.0802 |       7.9198 |       8.2375 |    7.0462 |                   nan      | near ceiling — little recoverable headroom                                  |

## Scoreline rank by total goals: REAL vs CEILING (expected rank)
| subset    |    n |   real_rank |   ceiling_rank |
|:----------|-----:|------------:|---------------:|
| total 0-1 | 2832 |        3.33 |           7.05 |
| total 2-3 | 4576 |        4.93 |           7.05 |
| total 4   | 1401 |       10.89 |           7.04 |
| total 5+  | 1746 |       21.78 |           7.03 |
| blowout   | 3026 |       17.21 |           7.03 |

## Draws
- Draw recall under the argmax rule: REAL **0.000**. The model predicts 'draw' as the modal W/D/L outcome only **0.00%** of the time *at all* → the CEILING for draw recall under this decision rule is ~0. **Draw recall 0/14 is a decision-rule artifact, not a probability failure.**
- Draw calibration gap (actual draw rate − mean predicted P(draw)) = **-0.036** → the size of the only genuinely model-side draw issue (mild under-prediction).

## How noisy is an n=48 audit? (resample-48-from-history, 95% spread)
- exact_top1: [0.042, 0.208]
- exact_top3: [0.208, 0.458]
- outcome_acc: [0.438, 0.729]
- rps: [0.167, 0.222]
- draw predicted-rate: [0.000, 0.000] (spans 0 ⇒ a 48-match draw recall of 0 is fully consistent with the model).

## Read-off
- A metric whose **CEILING ≈ TRIVIAL** has almost no signal to extract by construction.
- A metric where **REAL ≈ CEILING** is at its irreducible floor — stop optimising it; keep it as a *diagnostic*, not a target.
- Only metrics with **REAL materially below CEILING** (unrealized headroom) are worth a model change.

## Honest interpretation (per weakness)
- **W/D/L proper scores (acc/RPS/NLL/Brier): REAL is BETTER than the self-sim reference.** The self-sim is a *self-consistency* point, not a hard ceiling: REAL beating it means real outcomes are MORE concentrated than the model's probabilities ⇒ the model is mildly **under-confident / over-dispersed** in-sample (a side-effect of the ×0.55 champion-level temperature). A *sharpening* lever could help match-level proper scores — but it directly fights the champion-level over-concentration the temperature was added to fix. Not free; do not touch without a champion-level guardrail.
- **Exact-score top-1: essentially irreducible.** Even a perfectly-specified model of this family tops out at ~12.7% (ceiling), barely above the 10.9% you get by always guessing 1-0. REAL 11.8% sits between. The entire achievable range above climatology is ~1.8pp. **Not worth chasing.**
- **Exact-score top-3 / top-5: AT CEILING** (REAL ≈ self-sim). No recoverable signal. Diagnostic only.
- **Scoreline rank: aggregate is ~1 rank above ceiling (8.08 vs 7.05) — but it splits by total goals.** Low-total games rank BETTER than ceiling (0-1: 3.33 vs 7.05); high-total games rank FAR WORSE (5+: 21.78 vs 7.03; blowout 17.21 vs 7.03). So the **high-total weakness is REAL** (genuine mis-specification for those matches, NOT purely a metric artifact) — but it affects a minority (~17% are 5+ goals), the naive fix (fatter marginal tail) backfired in 2B, and optimising rank trades against W/D/L calibration. **Keep scoreline rank as a DIAGNOSTIC, not a target.** Any real attempt must be a *conditional* lever for high-total matches, gated on not regressing the dominant low-total games or W/D/L scores.
- **Draws: recall 0/14 is a decision-rule artifact** (ceiling recall ≈ 0 under argmax). The only genuine model-side draw issue is mild under-prediction (calibration gap ≈ −3.6pp).
- **The live-48 audit is very noisy.** At n=48, exact_top1's 95% spread is ~[0.04, 0.21] and outcome_acc ~[0.44, 0.73]; the live point values all sit inside. Do not over-read single live-48 numbers.