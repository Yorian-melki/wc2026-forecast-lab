# Phase 3A — Evidence Lab / Model Improvement Search

> **Offline research only.** No production model/data/config/nav/UI change. Isolated research files:
> `src/wc2026/experimental/match_features.py`, `scripts/exp_feature_search.py`,
> `outputs/experiments/3A_evidence_lab/`, `tests/test_match_features.py`. No production integration.
> Rule honoured: **no improvement claimed without out-of-sample test evidence.**

## 1. Current frozen baseline
- Production model `v0.6.93-ml20-dc` (tag `model-baseline-v0.6.93-ml20-dc`): Calibrated Elo →
  Dixon-Coles Poisson → ML 1X2 ensemble @0.20 → 100k MC. **`expected_goals` is Elo-only.**
- Established performance (live 48-match audit): outcome acc 58.3%, RPS 0.180 vs 0.229 coin-flip.
- Phase 2D ceiling audit: the model sits **near its irreducible floor** on most metrics; W/D/L proper
  scores already beat the self-sim reference (mildly over-dispersed). **Phase 2B (fat tail) and 2F
  (draw calibration) both failed to ship.** Model math currently FROZEN (Phase 2G).

## 2. Weakness audit (from 2D/2G, re-confirmed)
- **Real & bounded:** high-total / blowout *conditional* ranking (5+ rank 21.78 vs ceiling 7.03) — but
  it lacks a usable pre-match signal in the Elo-only model. W/D/L mildly under-confident (over-dispersed).
- **Fake / metric-induced:** draw recall 0/14 (decision-rule artifact). Scoreline rank (demoted to
  diagnostic). Draw "under-calibration" (was noise; model mildly over-predicts draws — Phase 2F).
- **Near-irreducible:** exact-score top-1/3/5 (top-1 ceiling ≈ 12.7%).

## 3. Candidate features and data coverage (honest inventory)
| Source | What it is | Historical coverage for OOS test? |
|---|---|---|
| `data/external/international_results/results.csv` | 49k-match historical log (10,555 competitive 2010-25) | **YES** — supports derived rolling features |
| `style_metrics`, `teams`, `form_history`, `h2h_records`, `wc_history`, `penalty_history`, `elo_snapshot` | **WC2026-only snapshots** (~48 rows) | **NO** — current-state only, cannot be backfilled |
| `market_odds_sample.csv` | 18 rows | **NO** — sample only; real odds need acquisition |

⇒ The only honestly-testable features are those **derivable from match history itself** (no train/serve
skew, available for both training and live): `elo_diff` (baseline), `elo_sum`, rolling `gf_diff`,
`ga_diff`, `form_diff` (momentum), `rest_diff`, `neutral`.

## 4. Experiment design
Leakage-free rolling features (`match_features.build_rolling_features`, 5 unit tests) → walk-forward OOS
folds {2016,2018,2020,2022,2024} (train < y, test [y,y+1]; pooled OOS n = 6,961). Two targets:
- **W/D/L:** multinomial logistic, baseline = `elo_diff` only vs augmented = all features.
- **Total goals** (the high-total lever): Poisson GLM, same baseline vs augmented.
Accept a candidate only if OOS proper scores improve **beyond bootstrap noise** (95% CI of per-match
delta entirely < 0). Standardised features; mild regularisation; coefficients inspected for sanity.

## 5. Results (delta = augmented − baseline; negative = better)
| metric | baseline | augmented | delta | 95% CI | beyond noise? |
|---|---|---|---|---|---|
| W/D/L log-loss | 0.8813 | 0.8730 | **−0.0083** | [−0.0126, −0.0041] | **YES** |
| W/D/L RPS | 0.1746 | 0.1721 | **−0.0025** | [−0.0037, −0.0014] | **YES** |
| W/D/L Brier | 0.5182 | 0.5123 | **−0.0059** | [−0.0085, −0.0032] | **YES** |
| total-goals Poisson dev | 1.3685 | 1.3653 | −0.0032 | [−0.0131, +0.0064] | **NO** |
| total-goals MAE | 1.4768 | 1.4811 | +0.0042 | [−0.0029, +0.0112] | **NO** |

Signal source (standardised W/D/L coefficients): after `elo_diff`, the largest contributors are
**recent goals-against rate (`ga_diff`)** and **recent points momentum (`form_diff`)**, with modest
`gf_diff`. `elo_sum`, `rest_diff`, `neutral` are near-zero.

## 6. Surviving vs failed candidates
- **SURVIVES (W/D/L):** recent-form features (defensive form + momentum) add **genuine OOS signal beyond
  Elo alone**, beyond bootstrap noise on all three proper scores. Small but real (~0.9% log-loss, ~1.4%
  RPS relative).
- **FAILS (total goals / high-total lever):** derivable features do **not** predict total goals OOS
  (CIs straddle 0). The Phase-2D high-total ranking weakness has **no usable conditioning signal** in
  match-history features → that path stays closed unless external data (market totals, xG, lineups) is
  acquired. This is the decisive negative the "3a kill-test" was meant to deliver.

## 7. The critical caveat (why this is RESEARCH, not READY)
The baseline here is a **pure-Elo logistic**, but production already blends an **ML 1X2 layer @0.20**
on top of Elo→DC. So this proves features beat *Elo-alone* — it does **not** yet prove they beat the
**deployed model**, which may already capture much of this signal. The measured lift likely **overstates**
the marginal value over production. Until tested against the real production W/D/L, this is a promising
lead, not a shippable win.

## 8. Required data (for the paths that did NOT survive here)
- **High-total / total-goals signal:** historical + live **market O/U totals** (best free predictor), or
  pre-match **xG**, or **lineup/injury** data — all need acquisition, and must cover BOTH 2010-25
  (training) AND live (serving) or they're unusable. None are in-repo as time-series.
- **Style/tempo, market 1X2, lineups:** in-repo only as WC2026 snapshots → not backfillable.

## 9. Exact next experiment (decisive)
**Compare the augmented W/D/L model against the ACTUAL production W/D/L (Elo→DC→ML@0.20), OOS on the same
walk-forward folds** — i.e. does the recent-form signal survive *on top of* the production ML layer?
- If YES (beyond noise) → genuine incremental value → **READY_FOR_MODEL_LAB** (then a separate, approved
  integration phase with champion-calibration guardrails, since W/D/L feeds the MC).
- If NO → the production ensemble already captures it → **WATCHLIST/KILL**; confirms the freeze.
Still offline, in-repo, no new data. This closes the "is the improvement real *vs production*" question.

## 10. Recommendation: **RESEARCH**
There is a **real, out-of-sample, recoverable W/D/L signal** in recent-form features beyond Elo alone —
the first positive evidence after 2B and 2F. But it is small and measured against a weaker-than-production
baseline, and the high-total lever stays dead. **Do not integrate.** Promote to the decisive head-to-head
vs the production W/D/L (§9); only a win there earns READY_FOR_MODEL_LAB. The model math stays frozen
until then.
