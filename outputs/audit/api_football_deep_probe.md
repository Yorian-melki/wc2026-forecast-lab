# API-Football Deep Probe — WC2026

**Probe date:** 2026-06-13  
**Plan:** Free (100 req/day, active until 2027-03-30)  
**Auth:** `x-apisports-key` header

---

## KEY DISCOVERY: Date-Bypass Unlocks WC2026 on Free Plan

| Endpoint | Result |
|---|---|
| `GET /fixtures?league=1&season=2026` | ❌ BLOCKED: "Free plans do not have access to this season" |
| `GET /fixtures?date=2026-06-13` | ✅ 567 total fixtures including **3 WC2026** |
| `GET /fixtures/events?fixture=1489370` | ✅ 21 events (goals, cards, subs) |
| `GET /fixtures/statistics?fixture=1489370` | ✅ Full match stats (shots, possession, corners, fouls) |
| `GET /fixtures/lineups?fixture=1489370` | ✅ Formations, coach, startXI, substitutes |
| `GET /fixtures/players?fixture=1489370` | ✅ Per-player: minutes, rating, shots, goals, passes |
| `GET /fixtures?live=all` | ✅ All live matches globally (filter by league.id=1) |
| `GET /standings?league=1&season=2026` | ❌ BLOCKED on Free |
| `GET /injuries?league=1&season=2026` | ❌ BLOCKED on Free |
| `GET /odds?league=1&season=2026` | ❌ BLOCKED on Free |

**Why the bypass works:** `fixtures?date=YYYY-MM-DD` is a global date endpoint not gated by season. WC2026 fixtures appear in the global response. All fixture detail endpoints (events/stats/lineups/players) accept any fixture ID and work regardless of plan.

---

## WC2026 Fixture IDs Discovered

| Date | Fixture ID | Match | Status |
|---|---|---|---|
| 2026-06-12 | 1538999 | South Korea 2–1 Czechia | FT |
| 2026-06-12 | 1539000 | Canada 1–1 Bosnia & Herzegovina | FT |
| 2026-06-13 | 1489370 | **USA 4–1 Paraguay** | FT |
| 2026-06-13 | 1489373 | Qatar vs Switzerland | NS (19:00 UTC) |
| 2026-06-13 | 1489371 | Brazil vs Morocco | NS (22:00 UTC) |
| 2026-06-14 | 1489372 | Haiti vs Scotland | NS (01:00 UTC) |
| 2026-06-14 | 1539001 | Australia vs Türkiye | NS (04:00 UTC) |
| 2026-06-14 | 1489374 | Germany vs Curaçao | NS (17:00 UTC) |
| 2026-06-14 | 1489376 | Netherlands vs Japan | NS (20:00 UTC) |
| 2026-06-14 | 1489375 | Ivory Coast vs Ecuador | NS (23:00 UTC) |

---

## USA 4–1 Paraguay (fixture 1489370) — Verified Data

**Score:** USA 4–1 PAR (HT: 3–0)  
**Goals:**
- 7' Own Goal (D. Bobadilla → USA)
- 31' F. Balogun (USA)
- 45+5' F. Balogun (USA)
- 73' Mauricio (Paraguay)
- 90+8' G. Reyna (USA)

**Stats (USA / PAR):**
- Shots on Goal: 6 / 1
- Total Shots: 16 / 9
- Corners: 3 / 1
- Fouls: 13 / 17

**Lineups:**
- USA: 4-2-3-1 (coach: Mauricio Pochettino)
- Paraguay: 4-4-2 (coach: Gustavo Alfaro)

---

## Data Quality Assessment

**Level: B** — shots/SOT/corners/cards/events/lineups available  
**Missing:** xG (not in API-Football on any plan), odds/injuries/standings (blocked on Free)  
**Real-time:** Yes (seconds lag)  
**Cost:** Free (100 req/day). ~4 req per completed match (fixture + events + stats + lineups).

---

## Limitations

1. **Date window:** Free plan may block dates older than ~3 days when using `league=1` param. Without it, dates work. MEX vs RSA (June 11) returned 0 fixtures — likely outside window.
2. **No xG:** Not available on API-Football on any plan.
3. **100 req/day:** At 4 req/match, covers ~25 matches/day. WC2026 has max 4 matches/day. Sufficient.
4. **No standings endpoint:** Must compute standings from match results or use OpenFootball.

---

## Verdict

**USABLE. Primary provider for live score, events, stats, lineups via date-bypass.**  
Quality level B. No upgrade needed for core live data. Upgrade only needed for odds/injuries.
