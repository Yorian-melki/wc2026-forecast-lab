# Phase 10 — Final Extraction Report
**Date**: 2026-06-13  
**Session**: Maximum Extraction Mode (10-phase mission)

---

## What Was Actually Built (No Bullshit)

### The real before/after

**Before**: 1 provider (OpenFootball, Quality C). Scores only. No xG. No events. No lineups. Manual JSON.  
**After**: 3 live providers (Quality A system). xG on all completed matches. Events, lineups, standings, scorers.

---

## Provider Truth

| Provider | Status | Quality | Key Findings |
|---|---|---|---|
| **Highlightly BASIC** | ✅ LIVE | **A** | xG confirmed. `/statistics/{matchId}` returns Expected Goals. 14 stats fields per team. Venue, referee, weather in match detail. |
| **API-Football FREE** | ✅ LIVE | **B** | Date-bypass confirmed: `?date=YYYY-MM-DD` returns WC2026 on Free plan. Events, lineups, live score work. No xG. |
| **Football-data.org FREE** | ✅ LIVE | **B** | 12 groups, 48 teams, 104 fixtures, scorers. No xG, no events. Confirms scores only. |
| **TheStatsAPI** | ❌ REVOKED | **D** | KEY_REVOKED — subscription lapsed. Health endpoint works but all data endpoints return 403. Has xG shotmap when active. |
| **OpenFootball** | ✅ FALLBACK | **C** | Score/result only. Days behind. Used as historical fallback. |

---

## xG Numbers (All 4 Completed Matches, Source: Highlightly)

| Match | Score | Home xG | Away xG | Home BC | Away BC |
|---|---|---|---|---|---|
| MEX vs RSA | 2-0 | 1.46 | 0.07 | 2 | 0 |
| KOR vs CZE | 2-1 | 2.30 | 0.83 | 4 | 1 |
| CAN vs BIH | 1-1 | 1.23 | 0.96 | 2 | 2 |
| USA vs PAR | 4-1 | 1.42 | 0.54 | 4 | 1 |

xG confirms: MEX dominant vs RSA (1.46–0.07). USA result was high-scoring but not dominant by xG (1.42 vs 0.54 is a fair gap, not a blowout gap). KOR created the most (2.30 xG, 4 big chances vs CZE's 0.83). CAN–BIH genuinely close (1.23–0.96, BC 2–2).

---

## Score Cross-Verification

- **API-Football** + **Highlightly** + **Football-data.org** all confirm the same 4 scores.
- **Disagreements: ZERO**.
- These numbers are real.

---

## Top Scorers (Source: Football-data.org)

1. Folarin Balogun (USA) — 2 goals
2. Julián Quiñones (MEX) — 1 goal
3. Raúl Jiménez (MEX) — 1 goal
4. Ladislav Krejčí (CZE) — 1 goal
5. In-beom Hwang (KOR) — 1 goal + 1 assist
6. Cyle Larin (CAN) — 1 goal
7. Jovo Lukić (BIH) — 1 goal
8. Gio Reyna (USA) — 1 goal
9. Mauricio (PAR) — 1 goal

---

## Files Written

### data/live/ (17 files)
- `live_xg.json` — xG + Big Chances + Expected Assists for all 4 matches (source: Highlightly)
- `live_statistics_highlightly.json` — All 14 stats fields per team per match
- `live_events_highlightly.json` — Goals, cards, subs with player IDs (17–21 events per match)
- `live_goals.json` — 14 goals across 4 matches
- `live_cards.json` — 18 cards
- `live_substitutions.json` — 37 substitutions
- `live_lineups_highlightly.json` — Starting XI for all 4 matches
- `live_boxscores.json` — Full box scores
- `live_standings_fdo.json` — All 12 groups, 48 entries (source: FDO)
- `live_standings_highlightly.json` — Alternate standings source
- `live_scorers.json` — Top scorers with goals + assists (source: FDO)
- `live_fdo_completed.json` — FDO match records (score, group, stage)
- `live_highlights.json` — Clip list (empty — endpoint returns [] for past matches)
- `live_odds_highlightly.json` — Odds (empty — endpoint returns [] for past matches)
- `provider_disagreements.json` — 4/4 agreements, 0 disagreements
- `provider_status.json` — Operational registry for dashboard

### data/wc2026_live.json (enriched)
- data_quality: A
- xg_available: True, xg_source: highlightly
- All 4 completed matches enriched with xG, Big Chances
- top_scorers: 10 entries
- providers_confirmed: 3 providers

---

## Code Written

### New provider (complete rewrite)
- `src/wc2026/providers/highlightly.py` — Full rewrite from "NOT A DATA API" stub to working Quality A provider (480 lines)

### New providers (written this session, earlier)
- `src/wc2026/providers/football_data_org.py` — Full FDO provider
- `src/wc2026/providers/thestatsapi.py` — Full TSA provider (works when key is active)
- `src/wc2026/providers/api_football.py` — Full AF rewrite with date-bypass

### Tests
- `tests/test_highlightly_provider.py` — 40 tests (init, state parsing, normalize, xG extraction, error handling, status, completed filter)
- `tests/test_football_data_org_provider.py` — 14 tests
- `tests/test_thestatsapi_provider.py` — 18 tests

**Total test suite: 504 passed, 0 failed.**

---

## What's Missing (Honest)

1. **TheStatsAPI shotmap** — per-shot xG with x/y coordinates. Unavailable (KEY_REVOKED). Need to renew sub.
2. **Highlightly Odds** — endpoint returns `[]` for completed matches. Might work pre-match.
3. **Highlightly Highlights** — endpoint returns `[]`. Might be plan limitation or match timing.
4. **Standings integration into model** — Highlightly standings loaded but not yet used for group advancement probs.
5. **xG in Elo update** — xG data exists. Not yet fed back into the prediction model.
6. **Scorers in team profiles** — FDO scorers saved but not displayed on team detail page.

---

## Extraction Rate Estimate (Honest, Pessimistic)

| Provider | Max possible | What we extracted | % |
|---|---|---|---|
| Highlightly BASIC | xG, stats, events, lineups, venue, weather, odds, highlights, H2H, last-5 | xG, stats, events, lineups, venue, weather | ~65% |
| API-Football FREE | Live score, events, lineups, stats, fixture list | All of the above | ~90% |
| Football-data.org FREE | Fixtures, standings, teams, scorers | All of the above | ~95% |
| TheStatsAPI | All (when key works) | 0% (key revoked) | 0% |
| OpenFootball | Historical results | Scores only | ~30% |

**System-level**: ~70% of all possible available data extracted. Gap = TSA key revoked + Highlightly odds/highlights empty.
