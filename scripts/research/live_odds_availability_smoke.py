"""Phase 3H-A — OFFLINE live WC2026 1X2 odds availability smoke test (READ-ONLY, minimal requests).

Determines which provider can supply UPCOMING/pre-match WC2026 1X2 (h2h) odds: Sportmonks, The Odds API,
TheStatsAPI. SECRET-SAFE: keys are read ONLY by directly parsing .env.yorian (NOT os.getenv, so an old
exported key cannot be picked up); never printed; scrubbed from every saved sample. No betting, no crawl,
~2 requests per provider. No production change, no integration.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/live_odds_availability_smoke.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3h_live_odds_availability"
TIMEOUT = 20


def keys_from_yorian() -> dict:
    """Parse keys ONLY from .env.yorian (never os.getenv — avoids any old exported key)."""
    k = {}
    for l in ENV.read_text().splitlines():
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            n, v = l.split("=", 1)
            k[n.strip()] = v.strip().strip('"').strip("'")
    return k


KEYS = keys_from_yorian()
SECRETS = [v for v in KEYS.values() if v and len(v) >= 8]


def scrub(o):
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    if isinstance(o, str):
        for s in SECRETS:
            if s and s in o:
                return "***REDACTED***"
        if "api_token=" in o or "apiKey=" in o:
            return o.split("?")[0] + "?***REDACTED***"
    return o


def save(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(scrub(body), indent=2)[:6000])


def fields(x):
    if isinstance(x, dict):
        return sorted(x.keys())
    if isinstance(x, list) and x:
        return fields(x[0])
    return []


def sportmonks(rows):
    tok = KEYS.get("SPORTMONKS_TOKEN", "")
    today = dt.date.today().isoformat()
    end = (dt.date.today() + dt.timedelta(days=21)).isoformat()
    reqs = 0
    # upcoming WC732 fixtures + Fulltime Result (market 1) odds
    r = requests.get(f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{end}",
                     params={"api_token": tok, "filters": "fixtureLeagues:732;markets:1",
                             "include": "participants;odds", "per_page": 50}, timeout=TIMEOUT)
    reqs += 1
    body = r.json() if r.ok else {}
    fx = body.get("data") or []
    with_1x2 = sum(1 for f in fx if any(o.get("market_id") == 1 for o in (f.get("odds") or [])))
    save("sportmonks_live", body)
    rows.append({"provider": "Sportmonks", "auth": "ok" if r.ok else f"FAIL {r.status_code}",
                 "endpoint": "GET /fixtures/between (league 732, markets:1)", "http": r.status_code,
                 "upcoming_wc_fixtures": len(fx), "fixtures_with_1x2": with_1x2,
                 "fields": "|".join(fields(fx)[:10]), "requests": reqs,
                 "verdict": "READY_FOR_LIVE_ODDS_FEED" if with_1x2 else "WATCHLIST (upcoming 1X2 EMPTY — confirms 3E/3G)"})


def the_odds_api(rows):
    key = KEYS.get("THE_ODDS_API_KEY", "")
    reqs = 0
    r = requests.get("https://api.the-odds-api.com/v4/sports/", params={"apiKey": key}, timeout=TIMEOUT)
    reqs += 1
    sports = r.json() if r.ok else []
    wc = next((s.get("key") for s in sports if isinstance(s, dict)
               and "world_cup" in str(s.get("key", "")).lower() and "soccer" in str(s.get("key", ""))
               and "women" not in str(s.get("key", "")).lower()), None)
    events, with_h2h, quota = 0, 0, {}
    if wc:
        r2 = requests.get(f"https://api.the-odds-api.com/v4/sports/{wc}/odds",
                          params={"apiKey": key, "regions": "eu", "markets": "h2h", "oddsFormat": "decimal"},
                          timeout=TIMEOUT)
        reqs += 1
        ev = r2.json() if r2.ok else []
        events = len(ev) if isinstance(ev, list) else 0
        with_h2h = sum(1 for e in ev if isinstance(e, dict) and (e[0].get("markets") if False else any(
            m.get("key") == "h2h" for bk in e.get("bookmakers", []) for m in bk.get("markets", [])))) if isinstance(ev, list) else 0
        quota = {h: r2.headers.get(h) for h in ("x-requests-remaining", "x-requests-used")}
        save("the_odds_api_wc", ev if isinstance(ev, list) else {})
    rows.append({"provider": "The Odds API", "auth": "ok" if r.ok else f"FAIL {r.status_code}",
                 "endpoint": f"GET /v4/sports + /sports/{wc}/odds?markets=h2h", "http": r.status_code,
                 "upcoming_wc_fixtures": events, "fixtures_with_1x2": with_h2h,
                 "fields": f"wc_key={wc} quota={quota}", "requests": reqs,
                 "verdict": "READY_FOR_LIVE_ODDS_FEED" if with_h2h else (
                     "WATCHLIST (WC key present, no upcoming h2h events now)" if wc else "WATCHLIST (no WC market listed now)")})


def thestatsapi(rows):
    key = KEYS.get("THESTATSAPI_KEY", "")
    base = "https://api.thestatsapi.com/api"
    hdr = {"Authorization": f"Bearer {key}"}
    reqs = 0

    def g(ep, params=None):
        nonlocal reqs
        reqs += 1
        try:
            r = requests.get(f"{base}/{ep}", headers=hdr, params=params or {}, timeout=TIMEOUT)
            return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})
        except Exception as e:
            return "ERR", {"_e": str(e)[:80]}

    st, comp = g("football/competitions/comp_6107")   # auth test on WC competition
    auth_ok = st == 200 and (comp.get("data") or comp.get("id") or comp.get("name"))
    # upcoming matches (try a near-future window; inspect statuses)
    today = dt.date.today().isoformat()
    end = (dt.date.today() + dt.timedelta(days=21)).isoformat()
    st2, m = g("football/matches", {"competition_id": "comp_6107", "date_from": today, "date_to": end, "per_page": 20})
    matches = m.get("data") or m.get("matches") or (m if isinstance(m, list) else [])
    statuses = sorted({str(x.get("status")) for x in matches if isinstance(x, dict)})[:6] if isinstance(matches, list) else []
    # try odds on first upcoming match
    has_1x2 = False; odds_fields = []
    if isinstance(matches, list) and matches:
        mid = matches[0].get("id") or matches[0].get("match_id")
        if mid:
            st3, od = g(f"football/matches/{mid}/odds")
            odv = od.get("data") or od
            odds_fields = fields(odv)[:10]
            txt = json.dumps(od).lower()
            has_1x2 = any(w in txt for w in ('"1x2"', "home_win", "match_winner", "moneyline", "fulltime"))
            save("thestatsapi_odds", od)
    save("thestatsapi_comp", comp)
    rows.append({"provider": "TheStatsAPI", "auth": "ok" if auth_ok else f"FAIL {st}",
                 "endpoint": "GET football/competitions/comp_6107 + /matches + /matches/{id}/odds",
                 "http": st, "upcoming_wc_fixtures": len(matches) if isinstance(matches, list) else 0,
                 "fixtures_with_1x2": int(has_1x2),
                 "fields": f"match_statuses={statuses} odds_fields={odds_fields}", "requests": reqs,
                 "verdict": "READY_FOR_LIVE_ODDS_FEED" if has_1x2 else (
                     "WATCHLIST (auth ok; pre-match 1X2 not confirmed)" if auth_ok else "KILL (auth failed)")})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Keys from .env.yorian (values hidden):")
    for n in ("SPORTMONKS_TOKEN", "THE_ODDS_API_KEY", "THESTATSAPI_KEY"):
        print(f"  {n}: {'present' if KEYS.get(n) else 'MISSING'}")
    rows = []
    for fn in (sportmonks, the_odds_api, thestatsapi):
        try:
            fn(rows)
        except Exception as e:
            rows.append({"provider": fn.__name__, "auth": f"ERR {type(e).__name__}", "endpoint": "-",
                         "http": "-", "upcoming_wc_fixtures": 0, "fixtures_with_1x2": 0,
                         "fields": str(e)[:90], "requests": 0, "verdict": "ERROR"})
    with (OUT / "live_odds_provider_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("\n=== LIVE WC2026 1X2 ODDS AVAILABILITY ===")
    for r in rows:
        print(f"\n[{r['provider']}] auth {r['auth']} (HTTP {r['http']}) · {r['requests']} req"
              f"\n  endpoint: {r['endpoint']}\n  upcoming WC fixtures: {r['upcoming_wc_fixtures']} · with 1X2/h2h: {r['fixtures_with_1x2']}"
              f"\n  {r['fields']}\n  -> {r['verdict']}")
    print(f"\nWrote {OUT}/live_odds_provider_matrix.csv + sanitized samples.")


if __name__ == "__main__":
    main()
