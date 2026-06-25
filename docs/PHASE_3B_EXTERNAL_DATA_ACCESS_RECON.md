# Phase 3B — External Data Access Recon & Safe Smoke Tests

> **Offline recon only.** No production model/app/data/config change, no betting execution, no scraping
> behind login, no quota-rotation. Keys loaded ONLY from `.env.yorian` (gitignored, never committed);
> **key values never printed and scrubbed from every saved sample** (verified by an automated leak scan).
> Research files: `scripts/research/smoke_external_data_sources.py`,
> `outputs/research/phase_3b_external_data/`. ~1 minimal request per provider.

## Secret hygiene (confirmed)
- `.env.yorian` exists, is **git-ignored** (`.env.*` + explicit line) and **not tracked**.
- Automated scan: **no key value appears** in any file under `outputs/research/`, `scripts/research/`, `docs/`.
- `.env.example` updated with the provider key **names only** (placeholders, no secrets).
- The 4 keys are present in `.env.yorian` (lengths: 32 / 32 / 64 / 60). **TheOdds.io key was NOT
  transmitted anywhere** (provider identity unconfirmed — see below).

## Provider capability matrix
| Provider | Auth | HTTP | Endpoint probed | Fields confirmed | Plan / quota | Useful family | Recommendation |
|---|---|---|---|---|---|---|---|
| **The Odds API** (the-odds-api.com) | ✅ OK | 200 | `GET /v4/sports` | active, description, group, has_outrights, key, title | **500 req/mo free**, 0 used | **Pre-match/live ODDS**; 15 soccer markets incl. **World Cup** outrights | **RESEARCH → READY (live odds)** |
| **Sportmonks** (api.sportmonks.com/v3/football) | ✅ OK | 200 | `GET /v3/football/leagues` | id, name, country_id, sub_type, type, category, active, last_played_at… | **Pro — trial until 2026-07-09**, ~53k req/hr | Rich football: leagues now; fixtures/lineups/events/stats/**xG** plan-dependent (not yet probed) | **READY_FOR_FEATURE_LAB (time-boxed)** |
| **API-Football** (api-sports.io) | ❌ FAIL | 403 / empty | `GET /status` direct + RapidAPI | — | — | rejected on **both** direct (`x-apisports-key`) and RapidAPI (`x-rapidapi-key`) hosts | **WATCHLIST (verify key)** |
| **TheOdds.io** | ⚠️ NOT TESTED | unreachable | keyless probe of literal domain | — | — | literal `theodds.io` times out; identity ambiguous (vs odds-api.io / theoddsapi.com) | **WATCHLIST/KILL (confirm provider)** |

*Auth + reachability were smoke-tested. Deeper coverage (historical depth, xG, lineups, injuries) was
**not** probed to conserve requests and avoid hallucinating endpoints — marked UNKNOWN below.*

## Per-provider detail
### 1. The Odds API — ✅ authenticates
- Free tier: **500 requests/month**, 0 used. `/v4/sports` lists **15 soccer markets including the FIFA
  World Cup** (outrights). Confirms pre-match & live **odds** are accessible now.
- **UNKNOWN / not smoke-tested:** event-level odds payload shape; **historical odds** — on this provider
  historical is a **paid add-on** (per provider docs), so free tier ≈ current/upcoming only.

### 2. Sportmonks — ✅ authenticates, strongest immediate breadth
- **Pro plan, trialing until 2026-07-09** (~2 weeks), ~53k requests/hour remaining — generous.
- `/v3/football/leagues` returns rich entities. Sportmonks v3 *can* expose fixtures, lineups, events,
  statistics, predictions and (on higher tiers) xG — but **entitlements are plan-dependent and were NOT
  probed**. Trial is time-boxed → probe the high-value endpoints before it expires.

### 3. API-Football — ❌ key rejected
- Direct `v3.football.api-sports.io/status` returned an empty `response`; RapidAPI host returned **403**.
- Likely causes: key belongs to a different API-Sports product, is expired, or needs a host I didn't try.
- **Not probed further** (avoid burning requests / spraying the key). Needs Yorian to confirm from the
  provider dashboard which host/product the key is for.

### 4. TheOdds.io — ⚠️ unverified, key deliberately withheld
- The literal domain `theodds.io` / `api.theodds.io` **times out**; web search shows the name collides
  with `the-odds-api.com`, `odds-api.io`, and `theoddsapi.com` — **genuinely ambiguous**.
- To avoid leaking the 64-char key to the wrong third party, **the key was not sent to any host.**
- Needs Yorian to confirm the exact base URL + auth method; then a 1-request smoke test can run.

## Missing-data list
- **Historical odds time-series** (needed to OOS-validate any market feature, per Phase 3A): The Odds API
  free = current only (**historical = paid**); Sportmonks odds = **plan-dependent, unconfirmed**. ⇒ still
  cannot backtest market features historically without paid/confirmed access.
- **Lineups / injuries / xG / expected lineups:** not smoke-tested; Sportmonks Pro trial *may* include —
  requires a targeted endpoint probe (next action).
- **API-Football data:** blocked until the key is verified.
- **TheOdds.io data:** blocked until the provider identity/base URL is confirmed.
- **WC2026-only repo snapshots** (`style_metrics`, `teams`, `h2h`, `market_odds_sample`): still no
  historical time-series — APIs don't change that for *past* matches unless historical endpoints are paid.

## Comparison to Phase 3A
- Phase 3A: only the in-repo `results.csv` was robust enough for OOS testing; the high-total lever and any
  market feature were **blocked for lack of historical data**.
- Phase 3B update: external APIs **do** unlock data — **live odds** (The Odds API) and **broad football
  data** (Sportmonks trial). **But:** the specific gap 3A needed — *historical* totals/odds for OOS
  backtesting — remains blocked on free tiers. Live odds are usable **prospectively** (going forward),
  not for backtesting past matches. So 3B enables *future-facing* features and *prospective* validation,
  not retroactive OOS proof of the high-total lever.

## Recommendations (per provider)
- **The Odds API → RESEARCH (READY for LIVE odds only).** Use live/upcoming odds as a prospective market
  anchor; historical OOS backtesting needs the paid historical add-on (a separate cost decision).
- **Sportmonks → READY_FOR_FEATURE_LAB, but TIME-BOXED (trial ends 2026-07-09).** Highest breadth. Next
  action: minimal targeted probes of fixtures / lineups / xG / historical depth before the trial expires.
- **API-Football → WATCHLIST.** Verify the key/product in the provider dashboard; re-smoke-test once fixed.
- **TheOdds.io → WATCHLIST/KILL.** Confirm the actual provider + base URL with Yorian; key withheld until then.

## Exact next action
Before the **Sportmonks trial expires (2026-07-09)**, run a second minimal recon (≤6 requests) probing
the high-value Sportmonks endpoints — fixtures (historical depth), lineups, injuries, statistics/xG, and
odds entitlement — to fill the UNKNOWN rows. In parallel, ask Yorian to (a) confirm the API-Football key's
product/host and (b) confirm what "TheOdds.io" actually is. **No integration, no production change** until
a provider clears a feature-lab evidence test.
