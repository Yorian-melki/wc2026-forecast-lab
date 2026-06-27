# Phase 3I — Market-Informed Model-Lab Prototype

> **Offline lab prototype only.** No production model/app/data/config change, no integration, no UI, no
> provider calls, no secrets (none used). Isolated files: `src/wc2026/experimental/market_blend.py`,
> `scripts/research/market_model_lab_prototype.py`, `tests/test_market_blend.py`,
> `outputs/research/phase_3i_market_model_lab/`. Default forecasts and deployed behaviour are unchanged.

## What was built
A pure, tested blend module + an offline driver that applies the Phase 3H-B identity-preserving blend on the
frozen **3E (WC) + 3G (international)** market datasets vs the **FULL production W/D/L** (`0.8·DC + 0.2·ML`
reproduced read-only via rolling Elo). Sample: **n = 356** (128 WC + 228 non-WC), the same matched set as 3G.
- `blend_wdl(prod, mkt, α)` = `(1−α)·prod + α·mkt` (α=0 ⇒ production identity; tested).
- `reweight_grid_to_wdl(flat, target)` — **parity-tested equal to production `_reweight_flat_to_wdl`**
  (proves the scoreline-grid integration path; preserves within-region scoreline + total-goal shape).
- `regime_alpha` prototype — more market weight where the model is **less certain** (entropy-scaled, cap 0.6).
- 8 unit tests pass (α=0 identity, normalisation/convexity, regime bounds+monotonicity, cap enforcement,
  **reweight parity vs production**, reweight hits target W/D/L). Full suite **639 passed**.

## Offline evaluation (RPS lower=better; Δ vs production; 95% bootstrap CI)
| Method | RPS | NLL | Brier | acc | ECE | mean conf | ΔRPS vs prod [CI] | beats prod? |
|---|---|---|---|---|---|---|---|---|
| production (α=0) | 0.2116 | 1.0075 | — | — | 0.070 | 0.474 | 0.0000 | — |
| **blend α=0.25** | 0.2012 | 0.9771 | | | 0.094 | 0.488 | **−0.0103 [−0.0133,−0.0075]** | **YES** |
| **blend α=0.40** | 0.1963 | 0.9626 | | | 0.069 | 0.500 | **−0.0153 [−0.0199,−0.0108]** | **YES** |
| **blend α=0.60** | 0.1912 | 0.9474 | | | **0.058** | 0.517 | **−0.0203 [−0.0271,−0.0137]** | **YES** |
| blend regime (cap 0.6) | 0.1917 | 0.9489 | | | 0.065 | 0.515 | −0.0199 [−0.0264,−0.0135] | YES |
| market-only (α=1.0, **ORACLE ref**) | 0.1861 | 0.9319 | | | 0.050 | 0.558 | −0.0254 [−0.0362,−0.0148] | (ref) |

By segment (α=0.6 and regime, both **beyond noise**): **WC** ΔRPS −0.027 [−0.041,−0.012] (n=128);
**non-WC** −0.017 [−0.024,−0.010] (n=228).

## Reading the prototype
1. **Every capped blend beats production beyond noise** on RPS **and** NLL — even the most conservative
   **α=0.25 (75% model)**. So an identity-preserving blend captures real, significant accuracy.
2. **α=0.60 captures ~80% of the market gain** (RPS 0.1912 vs market-only 0.1861) while keeping **40% model
   voice**, and is **better calibrated than production** (ECE 0.058 vs 0.070).
3. **Calibration nuance (honest):** a *small* blend (α=0.25) slightly **worsens** ECE (0.094 vs 0.070) —
   mixing two distributions can de-calibrate — before higher α recovers (0.40 ≈ prod) and improves (0.60).
   So if accuracy+calibration are both targets, **moderate α (0.4–0.6) dominates a tiny α.**
4. **Regime-aware ≈ fixed α=0.6 here** — international-tournament matches are mostly high-entropy, so the
   entropy-scaled α saturates near the cap for most fixtures. The regime prototype shows **no advantage over
   fixed-α on this balanced sample**; it would differentiate only on a more varied set (incl. lopsided
   games) and needs OOS tuning. **Not yet proven valuable.**
5. **Market-only (α=1.0) remains the best reference** — but it is an **ORACLE REFERENCE only, rejected for
   production** (bookmaker wrapper; destroys identity).

## Champion / tournament guardrail — PROXY only (full test MISSING)
Match-level **confidence proxy**: mean max-prob rises production **0.474** → α=0.6 **0.517** → market **0.558**.
The blend **sharpens** match W/D/L by ~+0.04 confidence at α=0.6 → a **modest but real champion
RE-CONCENTRATION risk** (the exact thing the ×0.55 temperature was added to control).
**What is missing (cannot be tested from these match-level datasets):** the FULL guardrail needs the **100k
tournament Monte-Carlo run with blended per-match W/D/L on a reconstructed WC bracket**, then comparing
**champion top-3 concentration, entropy, and champion-Brier vs the frozen baseline** (and confirming the
×0.55 temperature philosophy still holds, e.g. apply temperature post-blend or cap α). That harness
(bracket/group wiring + MC over blended probs) is **not built** — it is the gating deliverable before
shadow/production. **Until it passes, the blend is lab-only.**

## Live shadow-logger (design + schema only; no active logger)
`outputs/research/phase_3i_market_model_lab/shadow_log_schema.json` — proposed per-fixture record (The Odds
API primary, Sportmonks fallback; **no scheduler, no production calls, no serving**):
`fixture_id, kickoff_utc, provider, snapshot_ts_utc (≤ kickoff−15min), n_books (≥3), market_wdl,
production_wdl, alpha, alpha_policy, blended_wdl, freshness_min, fallback_reason
(none|stale|missing|low_coverage|provider_down|name_unmapped), served=false`.

## Answers to the brief
1. Prototype built: **yes** (module + driver + 8 tests). 2. Sample size: **356**. 3. Fixed-α results: table
above. 4. **Any capped α beats production beyond noise?** **YES — α=0.25/0.40/0.60 + regime, all beyond
noise.** 5. **Market-only best as reference?** **Yes** (oracle, rejected for prod). 6. **Champion guardrail:**
**PROXY shows modest sharpening/re-concentration risk; FULL guardrail UNTESTABLE here — MC-over-bracket
harness is missing.** 7. Files: see header + HANDOFF/NEXT_STEP. 8. No production files changed. 9. No secrets
printed/committed (no API used).

## Final recommendation: **READY_FOR_SHADOW_MODE** (gated on the champion-MC harness)
The blend is real, significant, identity-preserving (capped α), and better-calibrated at moderate α — strong
enough to move toward **live shadow mode** (log model/market/blend/actual on WC2026; serve nothing). **But**
two gates must clear first, in this order:
1. **Build + pass the champion-MC guardrail harness** (the missing piece) — if the blend over-concentrates
   champions, cap α / apply temperature post-blend until it stays in band. *(This is strictly required before
   shadow serving any blended tournament number.)*
2. **Yorian's identity + provider/cost decisions** (market-informed vs independent; Sportmonks-paid vs Odds
   API).
It is **not** READY_FOR_PRODUCTION_IMPLEMENTATION (champion guardrail untested, regime-α unproven, live
shadow not yet run, 48-team name map incomplete). Model math remains FROZEN; nothing integrated.
