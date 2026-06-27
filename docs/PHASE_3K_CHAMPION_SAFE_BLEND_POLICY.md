# Phase 3K — Champion-Safe Market-Blend Policy

> **Offline lab only.** No production model/app/data/config change, no integration, no UI, no API/secrets,
> no shadow serving. Files: `src/wc2026/experimental/market_temperature.py`,
> `scripts/research/champion_safe_blend_policy.py`, `tests/test_market_temperature.py`,
> `outputs/research/phase_3k_champion_safe_blend/`. 645 suite passes; production untouched.

## 1. The policy (formalised)
Applied to the **W/D/L probabilities** (NOT the scoreline grid — the grid is then reweighted to this
tempered W/D/L via the production `_reweight_flat_to_wdl`, preserving scoreline/total-goal shape):
1. **blend:** `w = (1−α)·production + α·market`  (identity-preserving; α ≤ 0.6; α=1.0 rejected)
2. **temper:** `q = wᔆ / Σ wᔆ`  (S<1 flattens = champion-safe; S=1 = no temper)
Normalisation and class order (home/draw/away) preserved (6 unit tests). `S` is fit per α by
**match-confidence-restore**: choose S so the blended W/D/L's mean confidence returns to the baseline model's
(0.469) — i.e. keep the market's *directional* re-ranking, drop its extra *sharpness* (which over-concentrates
champions). A scalar S grid {0.70, 0.80, 0.90} maps the frontier.

## 2–3. Grid (match-level on 356 real fixtures · champion on the 3J synthetic bracket, N=15k)
Baseline: production RPS **0.2130**, market RPS 0.1861; champion top-3 **0.517**, entropy **3.64**, 14 teams ≥1%.
| α | S mode | S | match RPS | ΔRPS vs prod | gain retained | champ top-3 | Δtop-3 | champ entropy | safe | **PASS** |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.25 | none | 1.00 | 0.2020 | −0.0109 | 100% | 0.569 | +0.051 | 3.42 | ✗ | **FAIL** |
| 0.25 | **match_conf** | 0.903 | 0.2039 | −0.0091 | **83%** | 0.530 | +0.013 | 3.58 | ✓ | **PASS** |
| 0.25 | S=0.80 | 0.80 | 0.2063 | −0.0067 | 61% | 0.487 | −0.030 | 3.77 | ✓ | PASS |
| 0.40 | none | 1.00 | 0.1968 | −0.0162 | 100% | 0.601 | +0.084 | 3.28 | ✗ | **FAIL** |
| 0.40 | **match_conf** | 0.834 | 0.2005 | −0.0124 | **77%** | 0.529 | +0.012 | 3.59 | ✓ | **PASS** |
| 0.40 | S=0.80 | 0.80 | 0.2015 | −0.0115 | 71% | 0.517 | −0.001 | 3.66 | ✓ | PASS |
| 0.40 | S=0.90 | 0.90 | 0.1989 | −0.0141 | 87% | 0.567 | +0.050 | 3.43 | ✗ | FAIL |
| 0.60 | none | 1.00 | 0.1915 | −0.0215 | 100% | 0.637 | +0.120 | 3.10 | ✗ | **FAIL** |
| 0.60 | **match_conf** | 0.746 | 0.1976 | −0.0153 | **71%** | 0.526 | +0.009 | 3.61 | ✓ | **PASS** |
| 0.60 | S=0.70 | 0.70 | 0.1992 | −0.0138 | 64% | 0.507 | −0.010 | 3.70 | ✓ | PASS |
| 0.60 | S=0.80 | 0.80 | 0.1960 | −0.0170 | 79% | 0.561 | +0.043 | 3.45 | ✗ | FAIL |

## 4. Pass/fail criteria
A policy PASSES only if: **match RPS beats production beyond bootstrap noise** AND champion **top-3 share rises
≤ 2pp**, **entropy drops ≤ 0.10 bits**, **top-1 rises ≤ 2pp** vs baseline — and **α ≤ 0.6** (α=1.0 excluded).
Result: **naive (S=1) fails at every α; the `match_conf_restore` policy passes at every α**, and the scalar
grid confirms a clean frontier (too-high S re-introduces over-concentration).

## 5. Selected champion-safe candidate policies
| Tier | Policy | match RPS | gain retained | champ top-3 (base 0.517) | entropy (base 3.64) |
|---|---|---|---|---|---|
| **Conservative** | α=0.25, S=0.903 | 0.2039 | **83%** | 0.530 (+1.3pp) | 3.58 |
| **Balanced** | α=0.40, S=0.834 | 0.2005 | **77%** | 0.529 (+1.2pp) | 3.59 |
| **Aggressive** | α=0.60, S=0.746 | 0.1976 | **71%** | 0.526 (+0.9pp) | 3.61 |
All three **beat production beyond noise** at the match level and keep champion concentration within ~1pp of
baseline (all 14 teams retain ≥1% title chances). The `match_conf_restore` rule generalises across α.

## 6–8. Answers to the brief
1. Policies tested: naive + match_conf_restore + scalar S {0.70/0.80/0.90} across α {0.25/0.40/0.60} (15 cells).
2. **Best safe conservative:** α=0.25, S=0.903 — RPS 0.2039, 83% gain, champion-safe.
3. **Best safe balanced:** α=0.40, S=0.834 — RPS 0.2005, 77% gain.
4. **Best safe aggressive:** α=0.60, S=0.746 — RPS 0.1976, 71% gain.
5. **Match-level gain retained:** 71–83% of the naive-blend RPS gain (all beyond noise vs production).
6. **Champion concentration:** restored to ≈ baseline (top-3 +0.9…+1.3pp; entropy within 0.06 bits; 14 teams ≥1%).
7. **Safe enough for shadow mode?** The policy passes the **synthetic-proxy** guardrail, but champion safety is
   validated only against a *sharpening proxy* — **not** real per-matchup odds. Per the project's discipline,
   that is **not** sufficient to claim shadow-readiness.
8. No production model/app/data/config changed. 9. No secrets (no API).

## What live-shadow data is needed before shadow mode
- **Real per-matchup pre-match 1X2 odds for an actual resolving bracket** (the proxy must be replaced by real
  odds as the tournament plays out).
- **Real champion-Brier vs the actual champion** (not computable offline; n=2 WCs).
- **Re-tune S on real data** and on the **exact 48-team WC2026 format** (this lab used a 32-team synthetic bracket).
Shadow mode is itself the *collection* step for these — and it serves nothing, so it is the safe way to obtain
them. But entry to shadow remains a separate, explicitly-approved step.

## Final recommendation: **READY_FOR_MODEL_LAB_ONLY** (policy now defined & proxy-validated)
A **champion-safe market-blend policy now exists and is characterised**: blend (α≤0.6) then temper to baseline
sharpness (`match_conf_restore`), capturing **71–83% of the match-level market gain** while holding champion
concentration within ~1pp of the frozen baseline. This is a real upgrade over Phase 3J (where the naive blend
failed). But because champion safety is validated only under **synthetic-proxy** assumptions, the recommendation
**stays READY_FOR_MODEL_LAB_ONLY** — not shadow, not production. **Recommended balanced policy for any future
shadow design: α=0.40, S≈0.83.** Model math remains FROZEN; nothing integrated; α=1.0 remains rejected.
