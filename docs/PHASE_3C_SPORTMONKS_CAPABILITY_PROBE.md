# Phase 3C — Sportmonks v3 Deep Capability Probe

> **Offline recon only.** No production model/app/data/config change, no integration, no crawl.
> `SPORTMONKS_TOKEN` loaded only from `.env.yorian`; **never printed; scrubbed from all saved samples**
> (incl. Sportmonks pagination URLs that echo the token) — leak scan clean. Plan confirmed:
> **Pro — trialing until 2026-07-09**, ~53k requests/hour. Research files: `scripts/research/
> probe_sportmonks_capabilities.py`, `outputs/research/phase_3c_sportmonks_probe/`. ~10 intentional
> requests; IDs chained from real responses (no endpoint guessing — failures recorded, not re-sprayed).

## Capability matrix
| # | Capability | Endpoint | HTTP | Confirmed? | Historical OOS? | Live/pre-match? | Feature family | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Competitions/leagues | `/leagues/search/World Cup?include=seasons` | 200 | ✅ **WC id=732 (cup_international, 6 seasons)**; CAF WC Qualifiers 711 (7); Club WC 3412; U20 1364; Women 1369 | yes | yes | tournament structure | **READY** |
| 2 | Fixtures (historical) | `/seasons/{id}?include=fixtures` | 200 | ✅ sampled season = 158 fixtures | yes | yes | match-data backbone | **READY** |
| 3 | Squads/players | `/squads/teams/{id}` | 200 | ✅ player_id, jersey, position, captain, start/end | yes | yes | squad metadata | **READY** |
| 4 | Lineups (confirmed) | `/fixtures/{id}?include=lineups;formations` | 200 | ✅ returned on a 2022 fixture (+ formations) | yes | yes | lineup/rotation | **READY_FOR_FEATURE_LAB** |
| 5 | Events / statistics | `/fixtures/{id}?include=events;statistics` | 200 | ✅ returned | yes | yes | shots/cards/possession | **RESEARCH** |
| 6 | Referees | `/fixtures/{id}?include=referees` | 200 | ✅ returned | yes | yes | referee/discipline | **RESEARCH** |
| 7 | **Odds (historical)** | `/fixtures/{id}?include=odds` | 200 | ✅✅ **3,748 odds rows**; markets incl. **Fulltime Result (1X2), Goals Over/Under (totals), Asian Handicap, Odd/Even**; fields incl. `probability`, `winning` (settlement), `bookmaker_id`, `handicap`, `total` | **YES** | yes | **market-implied features / market anchor** | **READY_FOR_FEATURE_LAB** |
| 8 | Predictions | `/fixtures/{id}?include=predictions` | 200 | ✅ type_ids 33/231/237/240 present | yes | yes | benchmark / ensemble | **RESEARCH** |
| 9 | xG / pressure index | `/fixtures/{id}?include=xGFixture;pressure` | 200 | ⚠️ **entitled (accepted, no error) but EMPTY for the 2022 international fixture** | unclear | unclear | xG features | **RESEARCH (coverage kill-test)** |
| 10 | Expected lineups | `/fixtures?include=lineups` (type filter) | 200 | ⚠️ not isolated — needs lineup `type_id` mapping | n/a (forward) | maybe | pre-match XI | **RESEARCH** |
| 11 | Injuries/sidelined | `/teams/{id}?include=sidelined` | 200 | ⚠️ include accepted but **empty** (entitlement vs no-current-injury unclear) | unclear | maybe | availability | **WATCHLIST** |
| 12 | News | `/news/pre-match` | 200 | ✅ rows (fixture_id, league_id, title, type) | partial | yes | text/sentiment (low priority) | **WATCHLIST** |
| — | Rate limit / plan | every response `rate_limit` + `subscription` | — | ✅ Pro trial → 2026-07-09, ~53k/hr | — | — | — | — |

## The headline finding
**Sportmonks exposes HISTORICAL ODDS** (1X2 + Over/Under totals + Asian Handicap, with implied
`probability` and `winning`/settlement) for past fixtures — **3,748 odds rows on a single 2022 match.**
This is the exact thing Phase 3A and 3B found blocked: The Odds API's historical is paywalled and the
repo had no historical odds series. Sportmonks' trial **unblocks retroactive OOS backtesting of
market-implied features** — the market anchor that Phase 2G wanted and the totals signal Phase 3A
couldn't build. Plus the FIFA **World Cup tournament (league 732) has 6 historical seasons**, and
fixtures carry **confirmed lineups, events, statistics, referees** historically.

## What supports historical OOS testing (confirmed on a 2022 fixture)
Odds (1X2/O-U/AH), fixtures, lineups, events, statistics, referees, squads — all returned for a past
match ⇒ usable to **build features and validate them out-of-sample** against the frozen model.

## Forward-only / live-only or low-value
- **Expected lineups** — inherently pre-match (forward); availability/timing not yet isolated.
- **News** — mostly current; low model-signal priority.
- **Injuries/sidelined** — leans forward; sampled empty.

## Blocked / unclear (precise, not hand-waved)
- **xG / pressure index:** the includes are *entitled* (HTTP 200, no error) but returned **empty for the
  sampled 2022 international fixture**. Likely cause: xG coverage is sparse for international/older matches
  (not a wrong call). **Unconfirmed for WC/international** — the single most important open question.
- **Expected lineups:** needs the lineup `type_id` mapping (confirmed vs expected) from docs.
- **Injuries/sidelined:** empty — can't tell entitlement from "no current injuries" without a team that
  has known sidelined players.

## Exact next step before the trial expires (2026-07-09)
One small, decisive probe (≤6 requests):
1. **xG coverage kill-test** — request xG on (a) a recent top-club-league fixture (to prove the
   include/endpoint returns data at all) and (b) 2–3 **WC league-732** fixtures (to estimate
   *international* xG coverage). This resolves "entitled-but-sparse vs wrong-access".
2. **Historical-odds depth** — confirm odds exist across the 6 WC-732 seasons (not just one fixture).
3. **Expected-lineups type_id** + **injuries entitlement** on a current fixture/team with known injuries.

Then the highest-value real experiment (separate, explicitly-approved): build an **offline market-implied
feature** from Sportmonks historical odds for international/WC fixtures and test whether it beats the
frozen baseline OOS — finally unblocking the market-anchor path. **No integration until it clears that test.**

## Recommendation summary
- **READY_FOR_FEATURE_LAB:** historical **odds** (strongest), **lineups**, fixtures/leagues, squads.
- **RESEARCH:** statistics, referees, predictions, **xG (pending coverage kill-test)**, expected lineups.
- **WATCHLIST:** injuries/sidelined, news.
- **Trial is time-boxed (≈2 weeks).** Prioritise the xG-coverage + historical-odds-depth probe now, since
  those decide whether the two biggest potential features (xG, market anchor) are real for WC2026.
