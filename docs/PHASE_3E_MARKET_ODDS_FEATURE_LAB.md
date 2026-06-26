# Phase 3E — Sportmonks Historical Market-Odds Feature Lab

> **Offline research only.** No production model/app/data/config change, no integration, no betting.
> `SPORTMONKS_TOKEN` from `.env.yorian` only; **never printed; scrubbed from samples** (leak scan clean).
> Settlement (`winning`) used **only** as a leakage diagnostic, never as a feature. Model math FROZEN —
> the baseline is a read-only reproduction. Files: `scripts/research/sportmonks_market_odds_feature_lab.py`,
> `outputs/research/phase_3e_market_odds_feature_lab/{market_odds_dataset.csv, market_feature_results.csv,
> market_feature_report.json}`.

## Frozen offline dataset (captured before trial expiry 2026-07-09)
Bounded extract of WC league-732 odds — **188 fixtures**:
| Season | Fixtures (finished) | Usable 1X2 | With O/U totals |
|---|---|---|---|
| 2018 | 64 | **64** | 64 |
| 2022 | 64 | **64** | 64 |
| 2026 | 60 | **0** (1X2 not populated for the ongoing tournament) | 60 |
| **Usable for W/D/L** | | **128 (2018+2022)** | |

Schema (confirmed, not assumed): Fulltime Result = `market_id 1` (labels `1`/`X`/`2`), Goals Over/Under
= `80` (`total` = line), Asian Handicap = `6` (diagnostic only). Per row: `value` (decimal odds),
`bookmaker_id` (≈15 books per fixture for 1X2), `latest_bookmaker_update` (pre-match timestamp),
`winning` (settlement — diagnostic only).

**Market probabilities:** 1X2 = **median-bookmaker no-vig** (per label, median of `1/decimal_odds` across
books, then the 3 outcomes normalised to sum 1). O/U = no-vig at the line closest to 2.5. Asian Handicap
left as diagnostic (not transformed).

## Leakage checks (all pass)
- **Settlement/`winning` is NEVER a feature** — it lives only in a diagnostic column.
- **Timestamps:** `latest_bookmaker_update` is the last *pre-match* bookmaker update (e.g. `2018-06-20
  19:45:52` for a tournament-period fixture) → pre-match closing line. Exact snapshot timing can't be
  guaranteed last-second-safe, but it is the pre-match Fulltime Result market, not in-play.
- **No future data** in feature construction; outcome used only for scoring.

## Results — market vs FROZEN model, out-of-sample, with bootstrap CIs
Per-match proper scores; baseline = the frozen Elo→Dixon-Coles model reproduced read-only (rolling Elo on
martj42, joined to WC fixtures by date + normalised team names; 128/128 matched). Δ = market − model
(negative = market better); 95% bootstrap CI over matches.

| Segment | n | model RPS | market RPS | ΔRPS [95% CI] | model NLL | market NLL | ΔNLL [95% CI] | acc model→market | blend* α |
|---|---|---|---|---|---|---|---|---|---|
| **2018** | 64 | 0.2358 | 0.1967 | **−0.039 [−0.071, −0.007]** ✓ | 1.057 | 0.942 | **−0.115 [−0.213, −0.011]** ✓ | 46.9% → 56.2% | 1.0 |
| **2022** | 64 | 0.2324 | 0.2072 | −0.025 [−0.062, +0.013] ✗ | 1.069 | 0.998 | −0.071 [−0.188, +0.051] ✗ | 48.4% → 53.1% | 0.9 |
| **Pooled 2018+2022** | **128** | 0.2341 | 0.2020 | **−0.032 [−0.056, −0.007]** ✓ | 1.063 | 0.970 | **−0.093 [−0.169, −0.012]** ✓ | 47.7% → 54.7% | **1.0** |

Brier (pooled): model 0.641 → market 0.570. **Best blend = α=1.0 (pure market)** on the pooled set — i.e.
the frozen model adds essentially nothing on top of the market for these WC matches.

## Honest reading
- **Market odds beat the frozen model out-of-sample, beyond bootstrap noise, on the pooled 128-match WC
  set** — on RPS, NLL, Brier, and accuracy. 2018 alone is significant on both proper scores; 2022 alone is
  directionally the same but **within noise** (n=64). This is the **first clear, proper-score-backed
  improvement candidate** in the whole 2x/3x series.
- **Why it's real, not leaky:** these are pre-match closing lines; no settlement is used as a feature.
  Closing odds are *legitimately* sharper than an Elo-only goal model — they price lineups, late money and
  match context the frozen model never sees. Beating a goal model with the closing line is expected; the
  finding is that the gap is **large** (~14% relative RPS, +7pp accuracy) and **significant** on WC matches.
- **Small-n caveat (explicit):** 128 matches = **two World Cups**. Pooled RPS/NLL clear the noise bar, but
  this is still two tournaments; per-WC 2022 does not individually clear it. Treat as a strong lead, not a
  settled law.
- **Baseline caveat:** the reproduced baseline is **Elo→DC**, *not* the full production W/D/L
  (Elo→DC→**ML@0.20**). The market's edge is large enough that it almost certainly survives the ML layer,
  but the decisive next test must use the *full* production W/D/L.
- **Identity caveat:** "using the market" = anchoring to bookmaker consensus. The product's stated identity
  is an *independent* probabilistic forecast ("probabilities, not predictions"). Any integration should be a
  **market-informed anchor/blend with a champion-calibration guardrail**, not replacing the model with odds.

## Answers to the brief
1. **Fixtures with usable 1X2:** 128 (2018: 64, 2022: 64). 2026: 0 (1X2 not populated for the live tournament).
2. **Fixtures with usable totals (O/U):** 188 (all seasons).
3. **Odds timestamps pre-match safe?** Yes — `latest_bookmaker_update` is the last pre-match update; pre-match
   Fulltime Result market, not in-play. Exact closing-instant not guaranteed, but pre-match-safe.
4. **Market-only vs frozen model:** market clearly better — pooled RPS 0.202 vs 0.234, NLL 0.970 vs 1.063,
   acc 54.7% vs 47.7%.
5. **Best blend:** α=1.0 (pure market) pooled; α=0.9 for 2022 — the model contributes ~nothing on top.
6. **Survives proper-score evidence?** **Yes** on the pooled set (RPS & NLL bootstrap CIs exclude 0); not
   individually for 2022.
7. **Files changed:** see header (3 outputs + script + this doc + HANDOFF/NEXT_STEP). No production files.
8. **Production untouched:** `src/wc2026/`, `app.py`, `data/`, `configs/` byte-identical (model math frozen).
9. **Secrets:** token never printed or committed; leak scan clean; `.env.yorian` gitignored.
10. **Recommendation:** **READY_FOR_MODEL_LAB** (with conditions, below).

## Recommendation: READY_FOR_MODEL_LAB — with hard conditions
Market-implied W/D/L is the first candidate to beat the frozen production baseline on proper scores beyond
noise. Promote to a **Model-Lab evaluation phase** (separate, explicitly approved — **not started here**)
that must:
1. compare market / blend against the **FULL production W/D/L (Elo→DC→ML@0.20)**, not just Elo→DC;
2. evaluate on a **larger international sample** (all international matches 2018+ with Sportmonks odds, not
   only 2 WCs) to escape the n=128 limit;
3. enforce a **champion-calibration guardrail** (W/D/L feeds the Monte-Carlo tournament);
4. integrate as a **market-informed anchor/blend** preserving the independent-forecast identity;
5. confirm **live pre-match odds availability** for WC2026 going forward (Sportmonks live or The Odds API).
No integration, no production change until those clear. The frozen 188-fixture dataset is now captured
offline, so the WC2018/2022 odds are preserved regardless of the 2026-07-09 trial expiry.
