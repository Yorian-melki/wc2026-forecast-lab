# Provider Architecture Decision — WC2026 (2026-06-13)

## Decision Summary

| Data Need | Provider | Method | Quality |
|---|---|---|---|
| Schedule | API-Football | `fixtures?date=YYYY-MM-DD` | B |
| Live score | API-Football | `fixtures?live=all` + filter | B |
| Completed results | API-Football + OpenFootball | Date-bypass + fallback | B/C |
| Match stats | API-Football | `fixtures/statistics` | B |
| Lineups | API-Football | `fixtures/lineups` | B |
| Goal events | API-Football | `fixtures/events` | B |
| xG | **NONE** | Proxy from shots (labeled PROXY) | D |
| Odds | **NONE** | Not available free | — |
| Injuries | Manual only | `key_injuries` in live.json | D |
| Historical | OpenFootball + results.csv | Static | C |

## Why API-Football Is Now Primary (Not OpenFootball)

**Before this probe session:** We assumed API-Football Free plan blocked WC2026 entirely. Router used OpenFootball as primary (quality C).

**After probe:** `GET /fixtures?date=YYYY-MM-DD` (no `league` or `season` params) returns WC2026 fixtures. All detail endpoints (events, statistics, lineups, players) work for any fixture ID on Free plan. This is a **date-bypass** that sidesteps the season paywall.

**Verified on live WC2026 data:**
- KOR 2-1 CZE: 3 goals confirmed
- CAN 1-1 BIH: 2 goals confirmed  
- USA 4-1 PAR: 5 goals, 21 events, full stats + lineups confirmed

## Open Gaps

1. **xG** — No free source. TheStatsAPI `/football/matches/{id}/shotmap` would provide this, but KEY_REVOKED. Refreshing that key is the single highest-impact action.

2. **Odds** — Not available on any active free plan.

3. **Injuries** — Manual tracking only.

4. **Standings** — Must be computed from match results (standings endpoint blocked on API-Football Free).

5. **June 11 matches** — API-Football free window covers ~last 3 days. MEX vs RSA (June 11) is kept from OpenFootball.

## Action Items (Priority Order)

1. **HIGH**: Refresh TheStatsAPI key → gain xG (shotmap endpoint)
2. **MEDIUM**: Cache fixture IDs daily to minimize API calls (100/day limit)
3. **LOW**: Upgrade API-Football to Starter if odds become needed
