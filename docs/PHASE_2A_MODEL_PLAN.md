# Phase 2A — Model Improvement Planning (PLANNING ONLY)

> Read-only analysis. **No model / config / data / probability change.** Source of truth =
> the official live 48-match audit `outputs/audit/live_metric_snapshots/2026-06-24_14-54.json`
> (model `v0.6.93-ml20-dc`). Baseline tag `model-baseline-v0.6.93-ml20-dc`.
> Status: planning complete · next = **Phase 2B offline experiment** (tail overdispersion diagnostic).
>
> **[Corrected by Phase 2F]** Where this doc says draws are "under-weighted/under-predicted" (from the
> noisy live-48 buckets): on robust historical data the model mildly **OVER-predicts** draws, and 2F
> showed calibrating them does not pass the proper-score gate. The live-48 draw signal is not reliable.

## 1. Current model architecture
- **Elo backbone** — per-team Elos (`data/elo_calibrated_params.json`), fit on martj42 competitive
  2010–2025 (**10,555 matches**).
- **Expected goals** (`calibrated_elo_model.py:334-355`): `log μ_a = log_base + β·(Elo_a−Elo_b)/400`
  (symmetric for b). `log_base=0.2269` (even-match μ≈1.25), `β=0.5436` = raw-MLE `0.988 × 0.55`
  temperature. μ ×= home-boost, jet-lag; **clamped [0.15, 3.60]**.
- **Scoreline distribution** (`_build_dc_flat:357-372`): **independent Poisson(μ_a)⊗Poisson(μ_b)**
  with **Dixon-Coles τ** correction on only the 4 low-score cells (0-0/1-0/0-1/1-1), `ρ=−0.021`.
- **ML ensemble** (`scoreline_probs:374-390`): logistic 1X2 blended at **0.20** (Elo 0.80),
  reweighting only the W/D/L *mass*, preserving within-region scoreline shape. Fixed (dynamic avail).
- **Monte Carlo** — 100k sims → champion/tournament probabilities.
- **Scorecard** (`scorecard.py:46-68`): predicted outcome = **`argmax(P_home,P_draw,P_away)`**;
  rank = position of real scoreline in descending-prob order; RPS over ordered W/D/L.

## 2. Weakness diagnosis (48-match audit)
| Symptom | Audit number | Root cause |
|---|---|---|
| **Draw recall 0/14** | confusion `pred draw = [0,0,0]` | **Mostly a decision-rule artifact.** Under symmetric DC-Poisson (μ≈1.25), `P(draw)≈0.26–0.28 < P(home)≈0.36` → `argmax` is structurally never draw. Draw *calibration* only mildly low (pred 0.15–0.25 vs actual 0.27–0.36). ⇒ ~70% decision-rule, ~30% mild draw under-weight. |
| **High-total ranking collapse** | rank by total: 0-1→4.58, 2-3→4.12, 4→8.67, **5+→18.0**; blowouts n=15 mean rank **13.73**, top-10 cov 26.7% | **Thin Poisson tail** + μ cap 3.60 + low base → ~all mass on ≤3-goal totals; high scorers buried. **Biggest, cleanest gap.** |
| **Exact top-1 8.3% / top-3 29.2%** | `mean_prob_actual_score 6.86%` | Inherent difficulty; partly downstream of the tail + draw under-weight. |

**Key context — W/D/L signal is SOLID:** outcome accuracy **58.3%**, RPS **0.180 vs 0.229** baseline.
The W/D/L *probabilities* are fine; the weaknesses are concentrated in **(a)** the draw decision
rule and **(b)** the scoreline tail — **not** the core outcome model.

## 3. Candidate improvements (ranked by upside / risk)
| Rank | Candidate | Targets | Upside | Risk | Testability |
|---|---|---|---|---|---|
| **1** | **Overdispersed / fat-tail scoreline dist** (Negative-Binomial marginals or shared shock in `_build_dc_flat`) | 5+/blowout rank, exact top-k | **High** | Med-High (core dist; re-fit; protect Brier/RPS/ECE) | High (existing backtest + live-48 shadow) |
| **2** | **Draw-mass calibrator** (isotonic on P(draw); hook `use_isotonic_calibrator` exists, off) | draw calibration + RPS | Med | Med (protect ECE 0.0170 backbone) | High |
| **3** | **Draw decision-rule / threshold** (scorecard band) | draw recall metric only | Med for metric | Low tech / **High integrity** (metric-gaming) | High |
| **4** | **Temperature / μ-cap re-fit** | totals, discrimination | Med | **High — entangled** (0.55 fixed top-3 over-concentration) | Med |
| **5** | **Dynamic ML weight** (already available) | upset robustness | — | Low | **Out of scope** here |

## 4. Files touched LATER (separate explicit approval each — all RED LINE)
- **Production (protected):** `src/wc2026/calibrated_elo_model.py` (`_build_dc_flat`,
  `expected_goals`); `data/elo_calibrated_params.json` (+dispersion, re-fit); `data/model_stack_config.json`
  (toggle); `src/wc2026/scorecard.py` (only for candidate 3).
- **New / non-production (safe):** `scripts/exp_tail_dispersion.py`, an `evals/` entry,
  experiment report doc. Reuses read-only `scripts/audit_live_scorecard.py`,
  `run_tournament_walkforward_validation.py`, `run_wc_historical_backtest.py`, `calibrate_mle.py`.

## 5. Offline experiment protocol
1. Branch from baseline tag; candidate **behind a parameter in a scratch module** — production path
   byte-identical, default **off**.
2. Re-fit any new param via MLE on the **same frozen 10,555-match** set (`calibrate_mle.py` pattern).
3. Evaluate on **three** sets: (a) live-48 shadow rescore, (b) WC historical backtest, (c) leak-free
   tournament walk-forward (WC2010/14/18/22).
4. **Pre-registered gate:** blowout & 5+ `mean_rank` ↓ materially **AND** `Brier_wdl`/`RPS`/`NLL`/
   champion-Brier/**ECE** within MC noise or improved **AND** no top-3 over-concentration regression.
5. Snapshot new audit JSON + experiment report. Production change = a separate approved phase
   (version bump + `CHANGELOG_MODEL.md` + `configs/archive/` snapshot).

## 6. Rollback / safety
- Experiments **offline on a branch**; production untouched until separate explicit approval.
- Production rollback if ever shipped: `git checkout model-baseline-v0.6.93-ml20-dc -- data/*.json
  src/wc2026/calibrated_elo_model.py` (or `cp configs/archive/v0.6.93-ml20-dc__*.json data/`), then `pytest`.
- **Freeze invariant:** `data/wc2026_live.json` blob `bbcd3ef82b520034bd51f8fce58d41c49e648271` untouched.
- Never present re-fit params as externally validated unless the walk-forward shows it.

## 7. Recommendation — first experiment
**Candidate 1 (tail overdispersion), fully offline diagnostic-then-fit.** It attacks the single
largest, most unambiguous gap (`5+ goals mean rank 18.0` vs `~4` low totals), the gating harness
already exists and is leak-free, and it's zero production risk (scratch module, default off) without
touching what already works (W/D/L accuracy, RPS, champion calibration). Draws (candidate 2) = the
natural second experiment. The decision-rule hack (3) is **not** recommended — it games the recall
metric without improving the forecast, conflicting with "probabilities, not predictions".

**Concrete first step (Phase 2B):** an offline script re-scoring the live-48 + WC backtests under a
grid of Negative-Binomial dispersion `r` (and μ-cap variants) → the rank-vs-Brier tradeoff curve.
**Measure before committing to any production change.**
