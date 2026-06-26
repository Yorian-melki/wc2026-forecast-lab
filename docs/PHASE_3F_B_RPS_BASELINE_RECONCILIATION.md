# Phase 3F-B — RPS Comparability / Baseline Reconciliation

> **Offline reconciliation only.** No production/app/data/config change, no API calls (reused local
> martj42 + params + ML pickle + the frozen 3E dataset, read-only). Purpose: explain why Phase 3F's
> production RPS ≈ **0.2338** on WC2018+2022 differs from prior audits (~0.180 live-48, ~0.193 historical),
> and decide whether READY_FOR_MODEL_LAB survives. Files: `scripts/research/rps_baseline_reconciliation.py`,
> `outputs/research/phase_3f_market_vs_production/rps_reconciliation.json`.

## 1. Do the RPS formulas match across phases? — YES (identical)
All four use the same ordered-3-category RPS, normalised by 2:
`sum((cumsum(p) − cumsum(obs))²) / 2`.
- Phase 1B live audit: `scorecard.py::_rps_ordered` → `s / 2.0`.
- Phase 2D: `exp_objective_ceiling.py::rps_ordered` → `… / 2.0`.
- Phase 3E: `sportmonks_market_odds_feature_lab.py::rps_rows` → `… / 2.0`.
- Phase 3F: `market_vs_full_production_baseline.py::rps_rows` → `… / 2.0`.
**No formula difference.**

## 2. Does the class order match? — YES
Every script uses **home / draw / away = 0 / 1 / 2**, with `outcome = 0 if home>away else (1 if eq else 2)`
and probability vectors ordered `[home, draw, away]`. The market probs are `[p_home, p_draw, p_away]`.
**No class-order mismatch.**

## 3. Is the Phase 3F production reconstruction valid? — YES (independently confirmed, no bug)
Decisive check: recomputed the full production W/D/L (`0.8·DC + 0.2·ML`, rolling Elo) for the exact same
128 fixtures using **martj42's native home/away orientation** (no Sportmonks join). Result:
**native RPS = 0.2338 — identical to Phase 3F's 0.2338.** Since ordered RPS is invariant under a
*consistent* home↔away relabel, this proves Phase 3F's join/orientation is correct. **No orientation bug.**

## 4–6. Why is production RPS 0.2338? — DATASET DIFFICULTY, not a bug
Same pipeline, same formula, across dataset segments:
| Segment | n | full-prod RPS | uniform-⅓ RPS | model acc |
|---|---|---|---|---|
| ALL competitive 2010-2025 | 10,555 | **0.1905** | 0.2413 | 0.585 |
| non-WC competitive | 6,863 | 0.1967 | 0.2409 | 0.571 |
| All "World Cup" matches (incl. **qualifiers**) | 3,692 | **0.1789** | 0.2420 | 0.613 |
| WC **final tournament** 2018+2022 (all) | 228 | 0.2138 | 0.2449 | 0.557 |
| **WC odds-subset (= Phase 3F's 128)** | 128 | **0.2338** | 0.2413 | 0.492 |

**Reconciliation of the prior numbers:**
- **~0.193 "historical/objective audit"** = the **full competitive set** → reproduced **0.1905/0.1929** (dc).
  Exactly matches Phase 2D (0.1929). ✓
- **~0.180 "live-48 snapshot"** ≈ the **WC-incl-qualifiers** difficulty (0.1789). WC *qualifiers* are full of
  strong-vs-minnow mismatches → easy → low RPS; the live WC2026 group stage is similarly mixed. ✓
- **0.2338 (Phase 3F)** = **WC final-tournament matches only**, and specifically the odds-bearing subset.
  These are balanced, neutral-site, top-team games — genuinely the **hardest** to forecast. The full WC
  final-tournament set (n=228) is 0.2138; the 128 odds-subset is a bit harder still (0.2338), because
  bookmaker-rich fixtures skew toward marquee/knockout/balanced games.

**The model is functioning correctly:** on the 128 it still **beats the uniform-⅓ baseline (0.2338 < 0.2413)** —
but only barely. That is the honest story: on WC *final-tournament* matches the Elo→DC→ML model has **very
little skill** (≈ coin-flip), which is exactly why a sharp market looks so much better there.

**Verdict: 0.2338 is NOT a bug, NOT a formula difference, NOT a reconstruction error.** It is a harder,
non-comparable sample. The earlier 0.18/0.19 figures came from easier/different samples (live WC2026 group,
or the full historical set incl. friendlies/qualifiers).

## 5. Does the market improvement still survive?
**Yes.** The Phase 3F comparison was always **apples-to-apples** — same 128 fixtures, same RPS formula, same
class order, validated orientation. The absolute-level discrepancy with *other* datasets never touched the
*within-128* delta. On the same 128: market RPS ≈ 0.202–0.208 vs production 0.2338 (and market beats the
uniform-⅓ 0.2413 far more decisively than the model does). Phase 3F's bootstrap CI on (market − production)
excluded 0 on the pooled set. The signal stands.

## 6. Does READY_FOR_MODEL_LAB remain valid? — YES (preserved), with a sharpened caveat
No downgrade. The 0.2338 is explained and the comparison is sound. **Added honesty:** the market's edge is
amplified by the fact that the production model is **near-uniform on WC final-tournament matches**
(0.2338 vs 0.2413). So part of "market beats model here" is "the model is weak on exactly these hard,
balanced games." This makes the market case real but also underlines:
- the **2-WC small-n** limit (generalization test = Phase 3G remains the gate),
- the **identity** constraint (don't dissolve the model into odds),
- that any integration should target precisely the regime where the model is weakest (balanced top-team
  matches), with a champion-calibration guardrail.

**Bottom line:** formulas match, class order matches, reconstruction is valid (0.2338 reproduced two
independent ways), 0.2338 is dataset difficulty not a bug, the market improvement survives, and
READY_FOR_MODEL_LAB stands — conditional on Phase 3G generalization, as already stated.
