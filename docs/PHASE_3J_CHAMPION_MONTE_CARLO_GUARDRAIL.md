# Phase 3J — Champion Monte-Carlo Guardrail (controlled synthetic; PARTIAL)

> **Offline lab only.** No production model/app/data/config change, no integration, no UI, no API/secrets.
> Files: `scripts/research/champion_market_guardrail.py`,
> `outputs/research/phase_3j_champion_guardrail/`. 639 suite passes; production untouched.

## 1. Feasibility — a FULL replay is NOT possible (stated honestly)
A real market-blended tournament replay is **infeasible**: market odds exist only for the **356 actual**
historical matches (3E/3G), never for the **hypothetical knockout matchups** a bracket MC generates.
Champion-Brier vs the actual champion is likewise **not computable** (n=2 real WCs + no market for
hypothetical matchups). The production MC (`tournament.py`) is also tightly coupled to the model object via
`simulate_knockout_match` per matchup, so it can't be driven by external per-matchup market W/D/L.

## 2. Method used — CONTROLLED SYNTHETIC guardrail (tests the concentration MECHANISM)
- Synthetic **32-team WC-style bracket** (top-32 WC2026 teams by Elo, snake-drawn into 8 groups of 4,
  top-2 → 16-team single-elim), N = 20,000 sims.
- Per-matchup **model W/D/L** from the production formula (`0.8·DC + 0.2·ML`, neutral) on the two teams' Elos.
- **Market = a SHARPENING PROXY:** power-temper the model by `T`, where **T = 1.672 is fit on the 356 real
  fixtures so the proxy reproduces the real market mean confidence (0.558)**. Validated: proxy-blend mean
  confidence by α = {0.25: 0.492, 0.40: 0.505, 0.60: 0.523} ≈ **real-blend {0.484, 0.497, 0.515}** — close.
- **Limitations (explicit):** the market is a *sharpening proxy*, not real per-matchup odds; the bracket is
  a 32-team synthetic, not the exact 48-team WC2026 format; champion-Brier is not computable. This tests the
  **concentration mechanism only** — it is a **PARTIAL** guardrail.

## 3–4. Champion concentration by α (synthetic bracket, N=20,000)
| Config | top-1 | top-3 share | entropy (bits) | gini | #teams ≥1% | Δtop-3 | Δentropy | verdict |
|---|---|---|---|---|---|---|---|---|
| production (α=0) | 0.242 | 0.519 | 3.64 | 0.71 | 14 | — | — | baseline |
| blend α=0.25 | 0.276 | 0.570 | 3.42 | 0.74 | 14 | **+0.051** | +0.23 | **FAIL** |
| blend α=0.40 | 0.288 | 0.595 | 3.29 | 0.77 | 12 | **+0.076** | +0.35 | **FAIL** |
| blend α=0.60 | 0.319 | 0.638 | 3.11 | 0.78 | 12 | **+0.119** | +0.53 | **FAIL** |
| market-only α=1.0 (oracle) | 0.368 | 0.706 | 2.81 | 0.80 | 10 | +0.187 | +0.83 | (ref, rejected) |
| **α=0.40 + re-temper** | 0.238 | 0.515 | 3.67 | 0.70 | 14 | −0.004 | −0.02 | **PASS** |
| **α=0.60 + re-temper** | 0.239 | 0.516 | 3.67 | 0.70 | 14 | −0.003 | −0.03 | **PASS** |

Acceptance rule: capped blend must not raise top-3 share by >5pp, drop entropy >0.30 bits, or raise top-1
>3pp vs baseline.

**Result: every NAIVE capped blend (α=0.25/0.40/0.60) FAILS** — champion concentration compounds through the
bracket. This is exactly the risk the ×0.55 temperature controls; the match-level proxy in Phase 3I
(confidence 0.474→0.517) **understated** it because concentration compounds over ~6 rounds.

## 5. A champion-safe path EXISTS — re-temper mitigation
Applying the ×0.55-temperature *philosophy* to the blend — **de-sharpen the blended W/D/L back to the
baseline model confidence** before the champion MC (fit `S`: α=0.40→S=0.794, α=0.60→S=0.718) — restores
champion concentration to baseline (**PASS**), keeping all 14 teams with ≥1% title chances.

**Crucial — does re-temper keep the match-level accuracy?** YES (match-level RPS on the 356):
| | production | blend 0.4 | **0.4+retemper** | blend 0.6 | **0.6+retemper** |
|---|---|---|---|---|---|
| RPS | 0.2130 | 0.1968 | **0.2016** | 0.1915 | **0.1985** |
So **0.6+retemper keeps ~73% of the naive RPS gain (0.1985 vs prod 0.213) AND passes the champion
guardrail.** Interpretation: the market's value splits into (a) **directional re-ranking** (which outcome is
favoured → keeps the RPS gain) and (b) extra **sharpness** (which over-concentrates champions). Re-tempering
removes (b) for the tournament MC while keeping (a).

## 6. Champion-Brier proxy
**Not computable** — no real per-matchup market for hypothetical matchups, and only n=2 real WCs. Stated as
missing; it can only be obtained from **live shadow data** as a real bracket resolves.

## 7. What is still missing (why this is PARTIAL)
- Real **per-matchup pre-match odds** for an actual resolving bracket (only available live).
- A real **champion-Brier** vs actual champion.
- Tuning `S`/`α` on real (not proxy) data; testing on the exact 48-team WC2026 format.
These are obtainable only via **live shadow mode** — which is therefore the *data-collection* step, not a
validated pass.

## Answers to the brief
1. Bracket replay feasible? **No** (no market for hypothetical matchups). 2. Method: **controlled synthetic
bracket + sharpening proxy**. 3. Concentration by α: table above. 4. **α=0.60 PASSES? NO** (naive fails).
5. **α=0.40 / 0.25? NO** — all naive capped blends fail; **only the re-temper variants pass.** 6.
Champion-Brier: **not computable** (stated). 7. Files: see header + HANDOFF/NEXT_STEP. 8. No production
files changed. 9. No secrets (no API).

## Final recommendation: **READY_FOR_MODEL_LAB_ONLY** (downgrade from 3I's gated shadow)
The Phase 3I match-level result stands, but the champion guardrail **fails for the naive blend** — shipping
it (even to shadow as a tournament number) would break the champion-calibration philosophy. A **champion-safe
mitigation exists** (re-temper the blend to baseline sharpness; keeps ~73% of the accuracy gain), but it is
tuned on a *proxy* and unvalidated against real per-matchup odds. Therefore:
- **Keep it in the Model Lab.** Next lab step: develop the **re-temper / "blend-then-champion-temperature"**
  policy and add it to the prototype (so the match-level gain is captured while champion concentration is
  held in band).
- **Do NOT advance to shadow serving of any blended tournament/champion number** until the re-temper policy is
  validated — and the only way to fully validate the champion side is live shadow data collection, which is a
  later, explicitly-approved step.
- Market-only (α=1.0) remains an oracle reference, rejected. Model math stays FROZEN; nothing integrated.
