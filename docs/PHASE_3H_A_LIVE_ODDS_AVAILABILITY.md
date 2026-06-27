# Phase 3H-A — Live WC2026 1X2 Odds Availability Smoke Test

> **Offline smoke test only.** No production model/app/data/config change, no integration, no betting.
> Keys read **only by directly parsing `.env.yorian`** (NOT `os.getenv` — so an old exported key can't be
> picked up); never printed; scrubbed from samples (leak scan clean). ~2 requests/provider. Files:
> `scripts/research/live_odds_availability_smoke.py`, `outputs/research/phase_3h_live_odds_availability/`.

## Secret hygiene + old-key search
- `.env.yorian` is **git-ignored** ✓. The three required var names are present: `SPORTMONKS_TOKEN`,
  `THE_ODDS_API_KEY`, `THESTATSAPI_KEY` (values never printed).
- **Old TheStatsAPI key locations found (reported, not printed):** **`.env` (repo root) holds a DIFFERENT /
  old `THESTATSAPI_KEY` value** (len 37) than `.env.yorian` (len 37) — **treated as invalid; not used.**
  `~/.secrets/*.env` hold no TheStatsAPI value. Tracked files (`.env.example`, `render.yaml`, docs,
  `scripts/*`, `src/wc2026/providers/thestatsapi.py`, tests) reference the **name only** — no committed key
  value (verified). **Only the `.env.yorian` value was used**, parsed directly from the file.

## Provider matrix
| Provider | Auth | HTTP | Endpoint | Upcoming WC fixtures | With 1X2 / h2h | Requests | Verdict |
|---|---|---|---|---|---|---|---|
| **The Odds API** | ✅ ok | 200 | `/v4/sports` + `/sports/soccer_fifa_world_cup/odds?markets=h2h` | **15** | **15 / 15** | 2 | **READY_FOR_LIVE_ODDS_FEED** |
| **Sportmonks** | ✅ ok | 200 | `/fixtures/between (league 732, markets:1)` | 41 | **19 / 41** | 1 | **READY_FOR_LIVE_ODDS_FEED** |
| **TheStatsAPI** | ✅ ok | 200 | `competitions/comp_6107` + `matches` + `matches/{id}/odds` | 20 (status `scheduled`) | **0** | 3 | **WATCHLIST** (pre-match odds N/A) |

## Per-provider detail
### The Odds API — ✅ best live 1X2 source
`soccer_fifa_world_cup` market is live; **15 upcoming WC events, ALL 15 carry `h2h` (= 3-way 1X2)** odds
with decimal prices. Quota: 499/500 remaining (1 used). Purpose-built odds API → cleanest live pre-match
1X2 feed. **READY_FOR_LIVE_ODDS_FEED.**

### Sportmonks — ✅ also works (and we already have its historical pipeline)
`/fixtures/between` for league 732 over the next 21 days returns **41 upcoming fixtures; 19 carry Fulltime
Result (market 1) odds** (the nearer-dated ones). **This resolves the Phase 3E/3G concern:** pre-match 1X2
**does exist for UPCOMING WC2026 fixtures** — the earlier "empty" was on *completed/settled* 2026 fixtures
(odds dropped post-settlement in that tier), which doesn't affect live serving (you snapshot pre-match).
**READY_FOR_LIVE_ODDS_FEED.**

### TheStatsAPI — ⚠️ auth ok, but no pre-match odds
Auth succeeds on `comp_6107` with the **`.env.yorian`** key. 20 upcoming WC matches (status `scheduled`),
but `matches/{id}/odds` returns **404 `NOT_FOUND` "Odds not found for this match"** for a scheduled match —
consistent with the provider being **finished-match odds only** (per its own description). Pre-match 1X2
**not available**. **WATCHLIST** (usable for post-match odds/xG later, not for the live pre-match feed).

## Answers to the brief
1. **Authenticated:** all three (Sportmonks, The Odds API, TheStatsAPI).
2. **Upcoming WC2026 fixtures:** all three list them (Odds API 15, Sportmonks 41, TheStatsAPI 20).
3. **Usable 1X2 odds:** **The Odds API (15/15 h2h)** and **Sportmonks (19/41 market-1)**. TheStatsAPI: none.
4. **Sportmonks live WC2026 odds:** **USABLE** for upcoming fixtures (19/41 with 1X2) — *not* empty for
   pre-match (the 3E/3G empties were completed-fixture artifacts).
5. **The Odds API:** **USABLE** — cleanest dedicated live 1X2 feed.
6. **TheStatsAPI:** **not usable** for pre-match 1X2 (odds are finished-match only; 404 on scheduled).
7. **Old TheStatsAPI key locations:** yes — `.env` (repo root) has a different/old value; not used. Only
   `.env.yorian` used.
8. Files changed: see header + HANDOFF/NEXT_STEP. 9. No production files changed. 10. No secrets printed/committed.

## The binding gate is CLEARED
The Phase 3G blocker — *can we get live WC2026 pre-match 1X2 odds?* — is resolved: **two independent
providers (The Odds API + Sportmonks) can supply them now.** The Odds API is the cleanest dedicated feed
(but small free quota, 500/mo); Sportmonks doubles as feed + the existing historical pipeline.

## Recommended next phase
Proceed to **Phase 3H-B — Integration DESIGN ONLY** (no code/integration): design the market-informed,
identity-preserving, **regime-aware** W/D/L anchor/blend with a champion-calibration guardrail, now that a
live 1X2 feed exists. Design must specify: primary feed (The Odds API or Sportmonks) + fallback, snapshot
timing (last pre-match), de-vig + aggregation rule, blend policy (down-weight where the model is already
strong, e.g. Euro/European sides), and the champion-MC re-validation. **No production change.**
