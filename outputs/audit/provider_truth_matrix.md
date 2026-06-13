# Provider Truth Matrix — WC2026 (2026-06-13)

Sources probed: TheStatsAPI, API-Football (Free), OpenFootball, TheSportsDB, local manual

Score: 0=unavailable, 1=blocked/requires paid, 2=partial, 3=works

| Field | TheStatsAPI | API-Football | OpenFootball | TheSportsDB | Local Manual |
|---|---|---|---|---|---|
| WC2026 schedule | 0 (KEY_REVOKED) | **3** (date-bypass) | **3** (JSON file) | 0 (null) | **3** (manual) |
| Completed results | 0 (KEY_REVOKED) | **3** (date-bypass) | **3** (within hours) | 0 (null) | **3** (manual) |
| Live score / minute | 0 (KEY_REVOKED) | **3** (live=all, filter league=1) | 0 (no live) | 0 (null) | 0 (no live) |
| Goal events / scorers | 0 (KEY_REVOKED) | **3** (events endpoint) | 2 (post-match only) | 0 (null) | 2 (manual update) |
| Cards | 0 (KEY_REVOKED) | **3** (events endpoint) | 0 | 0 | 0 |
| Substitutions | 0 (KEY_REVOKED) | **3** (events endpoint) | 0 | 0 | 0 |
| Lineups (startXI) | 0 (KEY_REVOKED) | **3** (lineups endpoint) | 0 | 0 | 0 |
| Formation + coach | 0 (KEY_REVOKED) | **3** (lineups endpoint) | 0 | 0 | 0 |
| Shots (on/off target) | 0 (KEY_REVOKED) | **3** (statistics endpoint) | 0 | 0 | 0 |
| Possession % | 0 (KEY_REVOKED) | **3** (statistics endpoint) | 0 | 0 | 0 |
| Corners, fouls, offsides | 0 (KEY_REVOKED) | **3** (statistics endpoint) | 0 | 0 | 0 |
| Per-player stats | 0 (KEY_REVOKED) | **3** (players endpoint) | 0 | 0 | 0 |
| xG | 0 (KEY_REVOKED) | 0 (not in API) | 0 | 0 | 0 |
| Odds (live) | 0 (KEY_REVOKED) | 1 (blocked Free) | 0 | 0 | 0 |
| Injuries / suspensions | 0 (KEY_REVOKED) | 1 (blocked Free) | 0 | 0 | 2 (manual) |
| Standings | 0 (KEY_REVOKED) | 1 (blocked Free) | 2 (computed from results) | 0 | **3** (computed) |
| Historical data (pre-2026) | 0 (KEY_REVOKED) | 2 (seasons 2022-2024 on Free) | **3** (CSV files) | 0 | **3** (results.csv) |
| Rate limit | 30/min (if active) | 100/day (Free) | GitHub CDN | 500/day | N/A |
| Cost | Trial expired | **Free** | **Free/open** | Free (key 123) | **Free** |
| Real-time | Yes (if active) | **Yes** | No (~1-12h lag) | Unknown | No |
| Production suitability | ❌ Key revoked | ✅ Quality B | ⚠️ Fallback only | ❌ WC2026 null | ⚠️ Emergency |

## Notes

- **API-Football Free via date-bypass**: `fixtures?date=YYYY-MM-DD` (no season/league params) returns WC2026 fixtures with all detail endpoints working. **This was not known before this probe.**
- **TheStatsAPI**: Health endpoint works. All data endpoints 403 KEY_REVOKED. If key refreshed, would add xG (shotmap) — unique field not available elsewhere.
- **OpenFootball**: Reliable for final scores and scorers. No live capability. Used as fallback for matches >3 days old (outside API-Football free window).
- **TheSportsDB**: WC2026 returns null on free key (123). Effectively useless for current data.
- **xG gap**: No free provider has xG. TheStatsAPI (shotmap endpoint) would close this gap if key is refreshed.
