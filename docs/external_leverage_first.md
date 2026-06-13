# External Leverage Audit — WC2026 Quant Model

> Rule: before building anything custom, check if a free, reliable, auditable external source exists.
> Each candidate passes or fails an 8-point filter before integration.

## Filter Criteria

1. **Improves the model?** Adds real predictive signal vs current approximation
2. **Free / low-friction?** No key required or free tier sufficient
3. **Coverage?** ≥ 40/48 WC teams or 80+ historical matches
4. **Reproducible locally?** Can re-fetch deterministically
5. **Stable?** Not likely to break or disappear
6. **Reduces an approximation?** Replaces a hardcoded fallback with real data
7. **Auditable?** Can verify outputs against known ground truth
8. **Avoids fragile custom code?** Replaces bespoke parser/scraper

---

## 1. statsbombpy (StatsBomb Open Data)

| Attribute | Value |
|-----------|-------|
| **Need** | Shot events, xG, pressures, passes per match (WC2022, WC2018) |
| **Source** | `pip install statsbombpy` + StatsBomb open-data GitHub |
| **Free** | ✅ Completely free, no key |
| **Coverage** | 64 matches WC2022 + 64 WC2018 → 30/48 WC2026 teams covered |
| **Quality** | Gold standard for football event data; xG models validated |
| **Friction** | Low — single import, downloads on first call |
| **Integration** | Already implemented in `statsbomb_loader.py`; not installed locally |
| **Decision** | ✅ **INTEGRATE** — install: `pip install statsbombpy` |
| **Why** | Provides real ppda, shot_quality, press_intensity (only correct xG source available) |
| **Blocker** | 18/48 teams not covered (teams absent from WC2018/2022); use Elo-based defaults |

---

## 2. eloratings.net (World Football Elo Ratings)

| Attribute | Value |
|-----------|-------|
| **Need** | National team Elo ratings, momentum indicators |
| **Source** | https://www.eloratings.net/World.tsv (public TSV) |
| **Free** | ✅ Public, no key |
| **Coverage** | 244 teams, all 48 WC2026 teams present |
| **Quality** | 60+ years of data; widely used in academic football modelling |
| **Friction** | Very low — single HTTP fetch, 244-row TSV |
| **Integration** | Already implemented in `elo_engine.py`; cached in `data/elo_raw_cache.tsv` |
| **Decision** | ✅ **INTEGRATED** — already in production |
| **Why** | Only free source with 60-year historical ELO per national team |
| **Limitation** | `elo_wc2022_approx = elo_current - d_2yr` is an approximation (±50-100 pts error) |

---

## 3. openfootball / worldcup.json

| Attribute | Value |
|-----------|-------|
| **Need** | Historical WC fixture results (scores, dates) for MLE calibration |
| **Source** | https://github.com/openfootball/world-cup |
| **Free** | ✅ MIT license |
| **Coverage** | WC1930-2022 results, all matches |
| **Quality** | Community-maintained; cross-checkable against Wikipedia |
| **Friction** | Medium — JSON parsing required, teams named inconsistently across years |
| **Integration** | Not implemented yet — needed for MLE calibration (P1) |
| **Decision** | ✅ **USE FOR P1 MLE** — highest value unlock; enables replacing analyst priors with estimated parameters |
| **Why** | 23 tournaments × ~48 matches = ~500 matches for parameter estimation |

---

## 4. football-data.org

| Attribute | Value |
|-----------|-------|
| **Need** | Live scores, recent results, player stats |
| **Source** | football-data.org API, tier 0 free |
| **Free** | ✅ Free tier: 10 calls/min, limited competitions |
| **Coverage** | Does NOT cover national team friendlies reliably; focuses on club leagues |
| **Quality** | Good for club, poor for national teams |
| **Friction** | API key required (free registration) |
| **Integration** | Not needed |
| **Decision** | ❌ **REFUSE** — poor national team coverage, adds complexity |
| **Why** | Our pipeline uses eloratings.net for national form; this adds nothing |

---

## 5. API-Football (RapidAPI)

| Attribute | Value |
|-----------|-------|
| **Need** | Real-time match events, lineups, squad fitness |
| **Source** | api-football.com via RapidAPI |
| **Free** | ⚠️ 100 requests/day free tier |
| **Coverage** | International matches covered |
| **Quality** | High; professional data provider |
| **Friction** | API key required; 100/day severely limits backfill |
| **Integration** | Would replace manual form_history.csv updates |
| **Decision** | ⚠️ **MONITOR** — only integrate if ODDS_API_KEY equivalent is provided |
| **Why** | 100 calls/day insufficient for historical backfill (WC2022 alone = 128 calls for full events) |

---

## 6. The Odds API

| Attribute | Value |
|-----------|-------|
| **Need** | Real bookmaker odds for value bet detection |
| **Source** | api.the-odds-api.com/v4 |
| **Free** | ⚠️ Free tier: 500 requests/month; WC2026 = ~150 match + 20 outrights = feasible |
| **Coverage** | 20+ bookmakers including Pinnacle |
| **Quality** | Pinnacle closing line = gold standard for market efficiency |
| **Friction** | `ODDS_API_KEY` env var required |
| **Integration** | Already implemented in `odds/fetcher.py`; demo mode without key |
| **Decision** | ✅ **USE WHEN KEY AVAILABLE** — demo mode is fine for development |
| **Why** | Without real Pinnacle data, all value bet detection is a tautology |

---

## 7. Open-Meteo

| Attribute | Value |
|-----------|-------|
| **Need** | Match-day weather (temperature, humidity, precipitation) for venue-level conditions |
| **Source** | api.open-meteo.com — completely free, no key |
| **Free** | ✅ No key, CORS-friendly, 10k calls/day |
| **Coverage** | All 16 WC2026 host cities; historical and forecast |
| **Quality** | ERA5 reanalysis data; ±1°C accuracy |
| **Friction** | Very low — single HTTP GET with lat/lon/date |
| **Integration** | Not implemented yet; needed for P3 (weather features) |
| **Decision** | ✅ **INTEGRATE AT P3** — free signal for venue-level conditions |
| **Why** | Mexico City heat + altitude, Miami humidity, New York cold in June are real factors |

---

## 8. geopy / timezonefinder

| Attribute | Value |
|-----------|-------|
| **Need** | Geocoding venue cities to lat/lon; timezone detection for jet lag |
| **Source** | `pip install geopy timezonefinder` |
| **Free** | ✅ Free (uses public Nominatim geocoder) |
| **Coverage** | All 16 WC2026 venues |
| **Quality** | Standard; timezonefinder is accurate to ±seconds |
| **Friction** | Very low; no key needed |
| **Integration** | `jet_lag.py` currently has hardcoded UTC offsets; could auto-derive them |
| **Decision** | ⚠️ **DEFER** — `jet_lag.py` already has hardcoded correct UTC offsets; `geopy` adds no new data |
| **Why** | Not worth adding a dependency when the 16 venue offsets are already hardcoded correctly |

---

## 9. scipy.optimize for Dixon-Coles MLE

| Attribute | Value |
|-----------|-------|
| **Need** | Replace hardcoded analyst priors (attack=91) with MLE-estimated attack/defense strengths |
| **Source** | `scipy.optimize.minimize` — already installed (`scipy 1.17.0`) |
| **Free** | ✅ Already available |
| **Coverage** | Historical WC/qualifying data (via openfootball) |
| **Quality** | L-BFGS-B minimization of DC log-likelihood — correct statistical approach |
| **Friction** | Medium — need to write the likelihood function; 2-3 hours engineering |
| **Integration** | P1 priority — replaces all hardcoded attack/defense values |
| **Decision** | ✅ **INTEGRATE AT P1** — highest leverage change possible |
| **Why** | Turns "ESP attack=91 (opinion)" into "α_ESP=1.47±0.03 (estimated from 847 historical matches)" |

---

## 10. Existing Dixon-Coles Python Repos

| Candidate | URL | Assessment |
|-----------|-----|------------|
| `janvandeveld/dixon-coles` | GitHub | Minimal, educational only; not production-ready |
| `openfootball/dc-model` | Does not exist | — |
| `Torvaney/english-premier-league` | Club only | Wrong competition type |
| `tgolding/dixon-coles` | Old; scikit-learn 0.18 API | Unmaintained |

**Decision: ❌ Build our own** — the DC likelihood is 30 lines of Python; no maintained repo covers national team tournament data. Writing it on `scipy.optimize` with `openfootball` data is faster than adapting a stale repo.

---

## Priority Integration Order

| Priority | Source | Effort | Impact |
|----------|--------|--------|--------|
| Now | statsbombpy (reinstall) | 2 min | Re-enables real xG/ppda pipeline |
| P0 | Wire existing ppda/shot_quality to model | 1h | Real data already in CSV; just needs Team dataclass update |
| P1 | openfootball + scipy DC-MLE | 1-2 days | Eliminates analyst-prior attack/defense; fundamental quality jump |
| P1 | Closing Line Value (Pinnacle via Odds API) | 4h + API key | Validates whether the model has any betting edge |
| P3 | Open-Meteo weather features | 4h | Marginal gain; worthwhile for Mexico City/Dallas heat |
| Future | API-Football live results | Key required | Automates form_history.csv updates |
