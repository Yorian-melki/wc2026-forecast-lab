# Phase 3F — Market Odds vs FULL Production Baseline

> **Offline research only.** No production model/app/data/config change, no integration, no betting, no
> new API calls (reuses the frozen Phase 3E dataset + the production ML pickle + rolling Elo, all
> read-only). Settlement used only as a validation diagnostic, never a feature. Files: `scripts/research/
> market_vs_full_production_baseline.py`, `outputs/research/phase_3f_market_vs_production/`.

## 1. Was the full production baseline reproducible? — YES
Production W/D/L = Elo→Dixon-Coles → ML 1X2 ensemble @0.20. The ML layer's features are just
`[elo_diff, neutral=1]` (verified in `calibrated_elo_model._ml_wdl`), and the ensemble reweight makes the
final W/D/L collapse to **`full_wdl = 0.8·DC_wdl + 0.2·ML_wdl`**. Reproduced offline from rolling Elo
(martj42) + the trained pickle `outputs/models/ml_match_model.pkl` (weights 0.8/0.2 from
`model_stack_config.json`, `ml_weight_mode=fixed`). **128/128** usable-1X2 fixtures matched.

## 2. Sample size
**128** WC fixtures with usable no-vig 1X2 (2018: 64, 2022: 64). 2026 has no usable 1X2 (live tournament).

## 3–5. Results — market vs FULL production (OOS, bootstrap CIs)
| Segment | n | **full prod** RPS | (dc-only) | **market** RPS | ΔRPS market−prod [95% CI] | prod NLL | market NLL | ΔNLL beyond noise? | prod ECE | market ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 64 | 0.2368 | (0.2358) | **0.1967** | **−0.040 [−0.072, −0.008]** ✓ | 1.059 | 0.942 | ✓ | 0.087 | **0.047** |
| 2022 | 64 | 0.2307 | (0.2324) | **0.2072** | −0.024 [−0.059, +0.013] ✗ | 1.064 | 0.998 | ✗ | 0.131 | **0.101** |
| **Pooled** | **128** | 0.2338 | (0.2341) | **0.2020** | **−0.032 [−0.055, −0.007]** ✓ | 1.062 | 0.970 | ✓ | 0.109 | **0.047** |

**The ML@0.20 layer does not close the gap:** full production (0.2338) ≈ DC-only (0.2341) on pooled RPS —
the ML ensemble adds essentially nothing on WC matches. So the Phase 3E caveat is **resolved**: the market
beats the *full* production stack, not merely Elo→DC.

## 6. Does the market signal help on top of production?
**Best blend = α=1.0 (pure market)** on pooled & 2018 (α=0.9 for 2022). Blend−production ΔRPS pooled
−0.032 [−0.055, −0.007]. **Production adds no incremental W/D/L signal over the market on this sample.**
- α=1.0 wins ⇒ per the brief, **production adds no incremental W/D/L signal over market here.**

## 7. Does improvement survive proper-score evidence vs the FULL baseline? — YES (pooled)
Pooled RPS *and* NLL bootstrap CIs exclude 0; 2018 individually significant; 2022 individually within
noise (n=64). Market also wins on Brier and accuracy (54.7% vs ~47.7%).

## 8. Guardrail analysis
- **Does market anchoring damage calibration? NO — it improves it.** Market ECE **0.047** vs production
  **0.109** (pooled). Anchoring toward market would *tighten* calibration, not harm it.
- **Identity risk? YES — this is the real constraint.** The RPS-optimal blend is α=1.0, i.e. "become the
  bookmaker." Fully deferring to odds abandons the product's stated identity ("probabilities, not
  predictions" — an *independent* forecast). The statistics say "use market"; the product says "don't
  dissolve the model into odds." Resolution is a **principled anchor/blend** (a chosen weight balancing
  accuracy vs independence), not the naive α=1.0 — accepting a small accuracy give-up to keep an
  independent, explainable model.
- **What's needed before champion Monte-Carlo integration:**
  1. reweight each match's scoreline grid to the (blended) market W/D/L via the existing
     `_reweight_flat_to_wdl` — keeps within-region scoreline shape;
  2. **re-validate champion-level concentration + champion-Brier** on the 4-WC walk-forward (W/D/L feeds the
     100k MC; the ×0.55 temperature guardrail must still hold);
  3. **live pre-match odds for all WC2026 matches** (Sportmonks live or The Odds API) + a **fallback** to the
     model when odds are missing;
  4. a decided **blend weight** (product decision on accuracy vs identity);
  5. de-vig + bookmaker-aggregation rule frozen and documented (median no-vig used here).

## 7b (task 6). Broader international sample — DEFERRED (documented)
Not extracted this phase. Rationale: the decisive *vs-full-production* question is answerable on the
existing 128 fixtures with **no new API calls**; a broad international odds extract (Euro / Copa / Nations
League / WC qualifiers 2018+) is a heavy *bounded* effort (hundreds–thousands of odds calls) better run as
its own phase; the Sportmonks trial expires **2026-07-09**. This is the **main remaining evidence gap** —
does the market edge hold beyond two World Cups? → recommended as **Phase 3G** (bounded international
generalization).

## Final recommendation: READY_FOR_MODEL_LAB (confirmed vs full production) — with conditions
The Phase 3E signal **survives against the full production baseline**: market-implied 1X2 beats Elo→DC→ML@0.20
on proper scores beyond noise (pooled n=128) **and** is better calibrated. This is the first external signal
to clear that bar. **Do not integrate.** Conditions before any Model-Lab integration:
1. **Generalize beyond 2 WCs** — bounded international sample 2018+ (Phase 3G). This is the gating evidence.
2. Integrate only as a **market-informed anchor/blend** preserving the independent-forecast identity (not α=1.0).
3. **Champion-calibration guardrail** on the walk-forward MC.
4. **Live odds availability + fallback** for WC2026.
No production change until 1–4 clear.

## Honest caveats (unchanged, sharpened)
- n=128 = **two World Cups**; pooled clears the bar, 2022 alone does not. Generalization untested → 3G.
- The market is *legitimately* sharper (prices lineups/late info the model never sees); not leakage
  (pre-match closing lines; settlement excluded from features).
- α=1.0 ("pure market") is an accuracy result, **not** an integration recommendation — that's a product
  decision about how much independence to trade for accuracy.
