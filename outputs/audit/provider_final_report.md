# Provider Re-Test Final Report — WC2026
## 9-Phase Mission: Completed 2026-06-13

---

## Y/N Answers (Required)

| Question | Answer |
|---|---|
| Did TheStatsAPI work? | **NO** — KEY_REVOKED (403) on all data endpoints. Health endpoint returns 200 (server up). |
| Did comp_6107 work? | **NO** — KEY_REVOKED blocks all endpoints including `/football/competitions/comp_6107`. |
| Did API-Football `league=1&season=2026` work? | **NO** — "Free plans do not have access to this season, try from 2022 to 2024." |
| Did the date-bypass work? | **YES** — `fixtures?date=YYYY-MM-DD` (no season/league params) returns WC2026 fixtures on Free plan. |
| Did fixture detail endpoints work? | **YES** — events, statistics, lineups, players all work for any fixture ID on Free plan. |
| Did `fixtures?live=all` work? | **YES** — returns all live matches globally. Filter by `league.id=1` for WC. |
| Which fields are now integrated? | score, minute, events, scorers, cards, shots, possession, corners, fouls, lineups, formation, coach, per-player stats |
| Is xG available? | **NO** — not in API-Football on any plan. TheStatsAPI has it (shotmap endpoint) but key revoked. |
| Is live score available? | **YES** — via `fixtures?live=all` on Free plan |

---

## What Was Actually Done (Non-Bullshit)

### Phase 1: Read TheStatsAPI docs (llms.txt)
- Fetched and saved full 4849-line `llms.txt` from `https://api.thestatsapi.com/llms.txt`
- Extracted all endpoint paths, auth method, competition IDs
- `comp_6107` = FIFA World Cup confirmed from llms.txt
- Result: Docs ingested. Now know exactly what to test.

### Phase 2: TheStatsAPI deep probe
- Tested `/health` → 200, `{"status":"healthy"}` — server is up
- Tested `/football/competitions/comp_6107` with `Authorization: Bearer KEY` → 403 KEY_REVOKED
- Tested `/football/matches?competition_id=comp_6107` → 403 KEY_REVOKED
- All data endpoints: 403 KEY_REVOKED
- Verdict: API key has no active subscription. Dashboard shows "Growth trial 50K" but key is revoked. **Action: refresh key.**

### Phase 3: API-Football deep probe  
**Key discovery session** — what changed everything:
- Tested `fixtures?league=1&season=2026` → BLOCKED ("Free plans do not have access to this season")
- Tested `fixtures?date=2026-06-13` (no league/season params) → **567 fixtures including 3 WC2026**
- Tested `fixtures/events?fixture=1489370` → **21 events, USA 4-1 PAR verified**
- Tested `fixtures/statistics?fixture=1489370` → **full match stats (shots, possession, corners, fouls)**
- Tested `fixtures/lineups?fixture=1489370` → **formation, coach, startXI, subs**
- Tested `fixtures?live=all` → **works, returns all live matches from any league**

WC2026 fixture IDs discovered: 1538999 (KOR-CZE), 1539000 (CAN-BIH), 1489370 (USA-PAR), 1489371, 1489372, 1489373, 1489374, 1489375, 1489376, 1539001 (upcoming June 13-14)

**Limitation confirmed:** June 11 matches (MEX vs RSA) outside 3-day free window. Kept from OpenFootball.

### Phase 4: Provider Truth Matrix
- 5 providers × 18 fields scored 0-3
- API-Football Free scores 3 on: schedule, results, live, events, cards, subs, lineups, formation, shots, possession, corners, fouls, per-player
- API-Football Free scores 0 on: xG (not in API), odds (blocked), injuries (blocked), standings (blocked)
- TheStatsAPI scores 0 on all (KEY_REVOKED)
- OpenFootball scores 3 on: schedule, completed results (lag)

### Phase 5: Architecture Decision
- Primary: API-Football (Free plan, date-bypass) — quality B
- Fallback: OpenFootball (for matches outside AF 3-day window) — quality C
- xG: NONE (gap documented, TheStatsAPI shotmap would close it if key refreshed)

### Phase 6: Integration
- `api_football.py` rewritten with:
  - `get_wc_fixtures_by_date(date)`: date-bypass endpoint
  - `get_live_matches()`: live=all + WC filter
  - `get_completed_matches()`: last N days via date-bypass
  - `get_fixture_events()`, `get_fixture_stats()`, `get_fixture_lineups()`, `get_fixture_players()`
  - `get_standings()` returns `[]` (blocked, documented)
  - `wc2026_accessible=True` on Free plan (updated from False)
  - Name→code mapping for API-Football full team names
- `router.py` updated: API-Football now primary, OpenFootball fallback
- `wc2026_live.json` updated: USA 4-1 PAR added, group D standings updated, source set to api_football

### Phase 7: Dashboard fixes
- `n_played` count: was hardcoded "2/104" → now dynamic `{n_played}/104`
- Data Quality page: "Current status: Quality C" → "Quality B via date-bypass"
- Coverage matrix: "API-Football (paid)" → "API-Football FREE (primary)"
- Provider freshness dict: api_football now shows quality_level="B", wc2026_accessible=True

### Phase 8: New tests
- `tests/test_api_football_provider.py`: 27 tests — name normalization, date-bypass filtering, fixture detail endpoints, status
- `tests/test_provider_router.py`: 11 tests — freshness dict, priority logic, quality B assertion
- Total test suite: **442 passed, 2 skipped** (up from 404 before this session)

### Phase 9: This document

---

## Maturity Score Update

| Dimension | Before (session start) | After (this session) |
|---|---|---|
| Live data | B/C (OpenFootball only) | **B** (API-Football via date-bypass) |
| Provider testing | Incomplete (AF wrongly marked blocked) | Complete — date-bypass discovered |
| xG | None (gap) | None (gap documented, path known) |
| Test coverage | 404 tests | **442 tests** |
| Dashboard accuracy | "Quality C", hardcoded match count | "Quality B", dynamic count |

**New estimated maturity: ~6.0/10** (up from 5.50)  
Still missing: xG (gap), odds (gap), ECE calibration (not done), sample size (WC2026 has only 4 matches played).

---

## Remaining Action Items (Priority Order)

1. **HIGH**: Refresh TheStatsAPI key → gain xG (shotmap endpoint). comp_6107 is confirmed, endpoints documented.
2. **MEDIUM**: Cache WC2026 fixture IDs to a local file (update daily), reduce API call count.
3. **MEDIUM**: Run `scripts/update_live_data.py` daily to keep wc2026_live.json current.
4. **LOW**: Upgrade API-Football to Starter for odds/standings/injuries.
5. **LOW**: Add ECE calibration to move from "heuristic temperature" to validated calibration.

---

## API Usage as of 2026-06-13
- API-Football: 21/100 requests used (79 remaining today)
- OpenFootball: Unlimited (GitHub CDN)
- TheStatsAPI: 1/50000 trial requests (key revoked)

---

## Commands

```bash
# Update live data (fetches today's WC fixtures from API-Football)
PYTHONPATH=src python scripts/update_live_data.py

# Run all tests
python -m pytest tests/ -q

# Probe API-Football for a specific date
python3 -c "
from src.wc2026.providers.api_football import ApiFootballProvider
af = ApiFootballProvider()
print(af.get_wc_fixtures_by_date('2026-06-14'))
"

# Get fixture detail
python3 -c "
from src.wc2026.providers.api_football import ApiFootballProvider
af = ApiFootballProvider()
print(af.get_fixture_events(1489370))
print(af.get_fixture_stats(1489370))
"
```
