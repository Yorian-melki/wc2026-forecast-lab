# Phase 3D — Sportmonks Coverage Closure Probe

> **Offline recon only.** No production model/app/data/config change, no integration, no crawl.
> `SPORTMONKS_TOKEN` from `.env.yorian` only; **never printed; scrubbed from all samples** (leak scan
> clean). 6 intentional requests, IDs chained from responses. Research: `scripts/research/
> probe_sportmonks_coverage_closure.py`, `outputs/research/phase_3d_sportmonks_coverage_closure/`.

## Closes every Phase 3C UNKNOWN — and upgrades the picture
| Data family | Endpoint/include | HTTP | Non-empty | WC historical | Club historical | Pre-match/live | OOS backtest | Priority |
|---|---|---|---|---|---|---|---|---|
| **xG / expected (club)** | `/fixtures/between(club)?include=xGFixture;statistics` | 200 | ✅ **5/5 fixtures** | — | ✅ yes | yes | ✅ yes | **READY** |
| **xG / expected (WC)** | `/fixtures/{wc2018}?include=xGFixture` | 200 | ✅ **20 metric rows** | ✅ **2018 confirmed** | — | maybe | ✅ yes | **READY** |
| Pressure index | same include | 200 | ❌ empty on WC fixture | no | unknown | maybe | no | **WATCHLIST** |
| **WC odds presence** | `/leagues/732?include=seasons.fixtures` (`has_odds`) | 200 | ✅ | **2018 ✓, 2022 ✓, 2026 ✓** (2006/2010/2014 ✗) | — | yes | ✅ yes | **READY** |
| **WC odds markets** | `/fixtures/{wc2018}?include=odds` | 200 | ✅ **819 rows** | ✅ from 2018 | — | yes | ✅ yes | **READY** |
| **Injuries / sidelined** | `/teams/{id}?include=sidelined.player` | 200 | ✅ **6 rows** | reconstructable (dates) | ✅ yes | yes | ✅ yes | **RESEARCH** |
| Expected lineups | `/core/types` (Lineup type_id=11) | 200 | partial | n/a | n/a | forward-only | no | **RESEARCH (low)** |

## Task-by-task findings
1–2. **xG / pressure — CONFIRMED (this corrects Phase 3C).** The `xGFixture` include returns non-empty
   per-participant metric rows for **5/5 recent club fixtures** AND for a **WC-732 2018 fixture (20 rows:
   `{type_id, participant_id, data.value, location}`)**. Phase 3C's "empty" was the specific *CAF
   qualifier/older* fixture sampled — not a coverage gap for WC finals. **Pressure index** was empty on
   the WC fixture (likely recent-club-only) → WATCHLIST. *(Minor follow-up: confirm which `type_id` is the
   expected-goals float vs other metrics; the data family itself is available.)*
3–4. **Odds across the 6 WC-732 seasons (minimal sampling):**
   - 2006 / 2010 / 2014 → **no odds** (0 of 64 sampled fixtures `has_odds`).
   - **2018 → 64/64**, **2022 → 64/64**, **2026 → 76/104** (current tournament, fills as it plays).
   - On the oldest odds-bearing fixture (**2018**, 819 odds rows): markets include **Fulltime Result (1X2),
     Goals Over/Under (totals), Asian Handicap (+1st-half AH)**, with **implied `probability`** and
     **`winning` (settlement)** fields. ⇒ all required market families + probability + settlement confirmed
     back to **2018**. Net: **3 World Cups of odds (2018, 2022, 2026)**.
5. **Expected lineups:** `Lineup` is `type_id=11`; the expected-XI is a distinct, **forward-only** lineup
   type not isolated here (the `/core/types` endpoint paginates ~25/page; not fully scanned). Low priority
   for a *historical* OOS model — useful only prospectively for live WC2026 pre-match.
6. **Injuries / sidelined — CONFIRMED.** `/teams/{id}?include=sidelined.player` returned **6 rows** with
   `category, start_date, end_date, games_missed, player_id, season_id, type_id`. The 3C empty was a team
   with no current sidelined entries. Start/end dates make it **historically reconstructable** (who was out
   for a given past fixture) → usable for availability features in OOS tests.

## Answers to the closure questions
1. **xG/pressure:** xG ✅ confirmed for **club (5/5) and WC (2018)**; pressure index ❌ empty on WC (WATCHLIST).
2. **Odds across WC-732:** ✅ **2018/2022/2026**; ❌ 2006/2010/2014. Markets 1X2 + O/U + Asian Handicap +
   implied probability + settlement confirmed from **2018**.
3. **Expected lineups:** include works (Lineup type=11); expected-XI is forward-only, not isolated → low priority.
4. **Injuries/sidelined:** ✅ confirmed with dates + games_missed (historically reconstructable).

## What is now unblocked for OFFLINE OOS feature work
- **Market-implied features** from historical odds — international/WC matches **2018→present** (1X2 / totals /
  Asian Handicap, with implied probability). *Caveat:* at the **tournament/champion** level this is only
  ~3 WCs (small n, same limit noted in 2D/3A); at the **match (W/D/L, totals)** level there is a large
  international sample since 2018.
- **xG features** (club + WC 2018+) and **injuries/availability** (reconstructable from sidelined windows).

## Recommendation for the next phase
The market-odds path that Phase 2G/3A wanted is **genuinely unblocked** (historical odds with settlement
since 2018). Recommended next (separate, explicitly-approved — **not started here**): **Phase 3E — offline
market-implied feature experiment.** Build, from Sportmonks historical odds (international/WC 2018+), a
market-implied W/D/L (and totals) feature, de-vig it, and test **out-of-sample whether it beats the frozen
baseline** (and whether it adds over the production Elo→DC→ML model) — mirroring the Phase 3A harness with
a champion-calibration guardrail. Decide READY_FOR_MODEL_LAB only if it clears. **No integration, no
production change** until then. The Sportmonks trial expires **2026-07-09**, so capturing a frozen
historical-odds research fixture (offline file, no production data mutation) before then is prudent.
