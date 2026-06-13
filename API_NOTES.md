# API WAR CHEST — WC2026

## TheStatsAPI

Docs for AI:
https://api.thestatsapi.com/llms.txt

Dashboard shows:
- Plan: Growth trial
- Trial limit: 50,000 requests
- Growth plan: 500,000 requests/month
- Current usage: 1 / 50,000
- Rate limit shown: 30 req/min during trial, Growth says 300 req/min after upgrade

Key env:
THESTATSAPI_KEY is in .env

Critical competition IDs:
- FIFA World Cup: comp_6107
- World Championship Qual. AFC: comp_8973
- World Championship Qual. CAF: comp_5720
- World Championship Qual. CONCACAF: comp_0836
- World Championship Qual. CONMEBOL: comp_4682
- World Championship Qual. OFC: comp_7363
- World Championship Qual. UEFA: comp_2954
- International Friendly Games: comp_29967
- UEFA Nations League: comp_574977
- Copa América: comp_5749
- EURO: comp_2949
- Africa Cup of Nations: comp_1554
- CONCACAF Gold Cup: comp_1376
- MLS: comp_9799
- Premier League: comp_3039
- LaLiga: comp_8814
- Serie A: comp_5840
- Bundesliga: comp_4643
- Ligue 1: comp_0256
- Champions League: comp_3498
- Europa League: comp_7739
- Conference League: comp_408698

Required tests:
- Read llms.txt first.
- Discover exact endpoint paths from llms.txt, do not guess.
- Test FIFA World Cup comp_6107.
- Test fixtures.
- Test results.
- Test live matches.
- Test match statistics.
- Test xG.
- Test player stats.
- Test team stats.
- Test odds if included.
- Test lineups.
- Test injuries/suspensions if documented.
- Save raw JSON responses.

Do not mark TheStatsAPI failed until:
1. llms.txt has been read;
2. exact documented endpoint has been tested;
3. exact auth header has been tested;
4. exact error body has been saved.

## API-Football / API-Sports

Key env:
API_FOOTBALL_KEY in .env
API_FOOTBALL_HOST=v3.football.api-sports.io

Known:
- World Cup league id = 1
- Seasons available: 2010, 2014, 2018, 2022, 2026

Required tests:
- /status
- /leagues?id=1
- /fixtures?league=1&season=2026
- /fixtures?live=all
- /fixtures/events?fixture=<fixture_id>
- /fixtures/statistics?fixture=<fixture_id>
- /fixtures/lineups?fixture=<fixture_id>
- /injuries?league=1&season=2026
- /odds?league=1&season=2026

If WC2026 is blocked on Free, write exact provider error and exact paid plan required.

## OpenFootball

Use as fallback only:
- Schedule/results
- No xG
- No in-play stats
- No lineups
- No injuries
- No odds

Known:
- worldcup.json has 104 matches
- current completed matches include MEX 2-0 RSA, KOR 2-1 CZE, CAN 1-1 BIH

## Free / historical sources

StatsBomb Open Data:
- Use for event data, pressing, shot quality, possession chains, lineups where available.
- Not live WC2026.

martj42 international_results:
- Use for historical match results 1872-present.
- Use for rolling Elo and tournament backtests.

soccerdata:
- Use for ClubElo, FBref, ESPN, WhoScored/Sofascore/Understat where feasible.
- Not official live truth.

ClubElo / EloRatings:
- Use as external sanity check against internal Elo.

football-data.org:
- Test only if easy.
- Not primary unless TheStatsAPI/API-Football fail.
