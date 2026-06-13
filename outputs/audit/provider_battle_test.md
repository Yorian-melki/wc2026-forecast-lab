# Provider Battle Test — WC2026

Generated: 2026-06-13 05:10 UTC

## Decision

- **Primary live provider**: `thesportsdb` (score: 15.0/100)
- **Secondary fallback**: `openfootball`
- **Metadata**: TheSportsDB
- **Highlights**: none
- **Live data currently fresh**: False

## Provider Scores

| Provider | Auth | Score | live_score | in_play_stats | xG | events | odds | historical |
|---|---|---|---|---|---|---|---|---|
| api_football | ✅ | **5.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| thestatsapi | ❌ | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| highlightly | ❌ | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| thesportsdb | ✅ | **15.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 10.0 |
| openfootball | ✅ | **15.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 10.0 |
| local_manual | ✅ | **5.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Fields Available by Provider

| Field | api_football | thestatsapi | highlightly | thesportsdb | openfootball | local_manual |
|---|---|---|---|---|---|---|
| date | | | | | ✓ | ✓ |
| fixtures_basic | | | | ✓ | ✓ | |
| group | | | | | ✓ | ✓ |
| injuries | | | | | | ✓ |
| notes | | | | | | ✓ |
| score | | | | | ✓ | ✓ |
| scorers | | | | | | ✓ |
| standings | | | | | | ✓ |

## Missing Fields (no provider covers)

- ❌ **xG** — NOT covered by any available provider/plan
- ❌ **lineups** — NOT covered by any available provider/plan
- ❌ **odds** — NOT covered by any available provider/plan
- ❌ **events** — NOT covered by any available provider/plan
- ⚠️ **injuries** — single-source only: local_manual
- ❌ **live_score** — NOT covered by any available provider/plan
- ❌ **in_play_stats** — NOT covered by any available provider/plan

## Manual Actions Required

- ⚠️ API-Football: WC2026 competition not found. Check dashboard at api-sports.io — 'International Tournaments' may need enabling. Also confirm your plan covers WC2026 season=2026.
- ❌ TheStatsAPI: Auth failed. Verify THESTATSAPI_KEY in .env is correct.