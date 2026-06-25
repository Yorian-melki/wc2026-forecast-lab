"""Phase 3C — OFFLINE Sportmonks v3 capability probe (READ-ONLY, no production touch).

Minimal, intentional requests (one per capability cluster), IDs chained from real responses (no wild
guessing). SECRET-SAFE: SPORTMONKS_TOKEN loaded only from .env.yorian; never printed; scrubbed from
every saved sample (incl. Sportmonks pagination URLs that echo the token). No integration, no crawl.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/probe_sportmonks_capabilities.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3c_sportmonks_probe"
BASE = "https://api.sportmonks.com/v3/football"
TIMEOUT = 20


def token() -> str:
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if line.startswith("SPORTMONKS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


TOK = token()


def scrub(obj):
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, str):
        if TOK and TOK in obj:
            return "***REDACTED***"
        if "api_token=" in obj:           # belt-and-braces for echoed URLs
            return obj.split("api_token=")[0] + "api_token=***REDACTED***"
    return obj


def fields_of(x):
    if isinstance(x, dict):
        return sorted(x.keys())
    if isinstance(x, list) and x:
        return fields_of(x[0])
    return []


def get(path, params=None):
    """GET {BASE}{path}; return (status, json_or_text, rate_limit, subscription_plan, error_msg)."""
    p = dict(params or {}); p["api_token"] = TOK
    try:
        r = requests.get(BASE + path, params=p, timeout=TIMEOUT)
    except Exception as e:
        return "ERR", {}, None, None, f"{type(e).__name__}: {str(e)[:100]}"
    try:
        body = r.json()
    except Exception:
        return r.status_code, {}, None, None, r.text[:120]
    rl = body.get("rate_limit") if isinstance(body, dict) else None
    subs = body.get("subscription") if isinstance(body, dict) else None
    plan = None
    if isinstance(subs, list) and subs:
        plans = subs[0].get("plans") if isinstance(subs[0], dict) else None
        if isinstance(plans, list) and plans:
            plan = plans[0].get("plan")
    err = body.get("message") if isinstance(body, dict) and not body.get("data") else None
    return r.status_code, body, rl, plan, err


def _trim(o, limit=25):
    """Cap long lists so saved samples stay small but remain VALID json."""
    if isinstance(o, dict):
        return {k: _trim(v, limit) for k, v in o.items()}
    if isinstance(o, list):
        return [_trim(v, limit) for v in o[:limit]]
    return o


def save(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(scrub(_trim(body)), indent=2))


def data_of(body):
    return body.get("data") if isinstance(body, dict) else None


def main():
    if not TOK:
        print("SPORTMONKS_TOKEN missing from .env.yorian"); return
    rows = []
    plan_seen = None

    def record(cap, path, status, body, rl, plan, err, relevance="", note=""):
        nonlocal plan_seen
        plan_seen = plan_seen or plan
        d = data_of(body)
        n = len(d) if isinstance(d, list) else (1 if d else 0)
        rows.append({
            "capability": cap, "endpoint": path,
            "auth": "ok" if (isinstance(status, int) and status == 200 and (d or n)) else f"FAIL {status}",
            "http": status, "fields": "|".join(fields_of(d)[:14]),
            "sample_n": n, "rate_remaining": (rl or {}).get("remaining") if rl else None,
            "note": (note or (err or ""))[:140], "relevance": relevance,
        })

    # 1) competitions: find World Cup / international coverage
    st, body, rl, plan, err = get("/leagues/search/World Cup", {"include": "seasons"})
    save("01_leagues_search_worldcup", body)
    leagues = data_of(body) or []
    wc = next((l for l in leagues if "world cup" in str(l.get("name", "")).lower()
               and "women" not in str(l.get("name", "")).lower()), leagues[0] if leagues else {})
    seasons = wc.get("seasons") or []
    record("1. competitions/leagues", "/leagues/search/World Cup?include=seasons", st, body, rl, plan, err,
           relevance=f"WC league id={wc.get('id')} name='{wc.get('name')}' · {len(seasons)} seasons (historical depth)")
    # pick a past, finished season (prefer 2022)
    season = None
    for s in seasons:
        if "2022" in str(s.get("name", "")):
            season = s; break
    season = season or (seasons[-1] if seasons else {})
    sid = season.get("id")

    # 2) fixtures (historical): season fixtures
    fid = None; team_ids = []
    if sid:
        st, body, rl, plan, err = get(f"/seasons/{sid}", {"include": "fixtures"})
        save("02_season_fixtures", body)
        fx = (data_of(body) or {}).get("fixtures") if isinstance(data_of(body), dict) else None
        fx = fx or []
        if fx:
            fid = fx[0].get("id")
        record("2. fixtures (historical)", f"/seasons/{sid}?include=fixtures", st, body, rl, plan, err,
               relevance=f"season '{season.get('name')}' has {len(fx)} fixtures (historical backtest source)")
    else:
        record("2. fixtures (historical)", "/seasons/{id}?include=fixtures", "SKIP", {}, None, None,
               "no season id resolved")

    # 3) fixture detail — lineups / events / statistics / referees / participants
    if fid:
        st, body, rl, plan, err = get(f"/fixtures/{fid}",
                                      {"include": "participants;scores;lineups;events;statistics;referees;formations"})
        save("03_fixture_core", body)
        d = data_of(body) or {}
        team_ids = [p.get("id") for p in (d.get("participants") or [])][:2]
        inc_present = [k for k in ("lineups", "events", "statistics", "referees", "formations", "participants")
                       if d.get(k)]
        record("3-4. lineups/events/stats/referee", f"/fixtures/{fid}?include=lineups;events;statistics;referees",
               st, body, rl, plan, err, relevance=f"includes returned: {inc_present}")

        # 5) xG / pressure (uncertain include names — let API confirm)
        st2, body2, rl2, _, err2 = get(f"/fixtures/{fid}", {"include": "xGFixture;pressure"})
        save("05_fixture_xg_pressure", body2)
        d2 = data_of(body2) or {}
        record("8. xG / pressure index", f"/fixtures/{fid}?include=xGFixture;pressure", st2, body2, rl2, None, err2,
               relevance=("xG/pressure includes returned" if (d2.get("xGFixture") or d2.get("xgfixture") or d2.get("pressure"))
                          else f"include error (valid names in note): {str(err2)[:90]}"))

        # 6) predictions + odds
        st3, body3, rl3, _, err3 = get(f"/fixtures/{fid}", {"include": "predictions;odds"})
        save("06_fixture_predictions_odds", body3)
        d3 = data_of(body3) or {}
        preds, odds = d3.get("predictions") or [], d3.get("odds") or []
        markets = sorted({o.get("market_description") or o.get("market_id") for o in odds})[:12] if odds else []
        record("7. odds / predictions", f"/fixtures/{fid}?include=predictions;odds", st3, body3, rl3, None, err3,
               relevance=f"predictions={len(preds)} odds_rows={len(odds)} markets={markets}")

    # 7) expected lineups (timing) — dedicated include on upcoming fixtures
    st, body, rl, _, err = get("/fixtures", {"include": "lineups", "filters": "lineupTypes:11",
                                             "per_page": 1})
    save("07_expected_lineups_probe", body)
    record("5. expected lineups", "/fixtures?include=lineups (type=expected)", st, body, rl, None, err,
           relevance="probe for expected-XI lineup type; confirm type_id mapping in docs")

    # 8) squads + injuries (sidelined)
    if team_ids and team_ids[0]:
        tid = team_ids[0]
        st, body, rl, _, err = get(f"/squads/teams/{tid}")
        save("08_squad", body)
        record("3. squads/players", f"/squads/teams/{tid}", st, body, rl, None, err,
               relevance="player/team metadata")
        st, body, rl, _, err = get(f"/teams/{tid}", {"include": "sidelined"})
        save("09_injuries_sidelined", body)
        d = data_of(body) or {}
        record("6. injuries/sidelined", f"/teams/{tid}?include=sidelined", st, body, rl, None, err,
               relevance=("sidelined returned" if d.get("sidelined") else "no sidelined data / not entitled"))

    # 9) news
    st, body, rl, _, err = get("/news/pre-match", {"per_page": 1})
    save("10_news", body)
    record("10. news", "/news/pre-match", st, body, rl, None, err,
           relevance=("news rows returned" if data_of(body) else f"check path: {str(err)[:80]}"))

    # write matrix
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "capability_matrix.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["capability", "endpoint", "auth", "http", "fields",
                                          "sample_n", "rate_remaining", "relevance", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Plan: {plan_seen}\n")
    for r in rows:
        print(f"[{r['capability']}] {r['auth']} (HTTP {r['http']}) {r['endpoint']}")
        print(f"    fields: {r['fields'][:120]}")
        print(f"    {r['relevance']}")
        if r["note"]:
            print(f"    note: {r['note']}")
    print(f"\nWrote {OUT}/capability_matrix.csv + sanitized samples.")


if __name__ == "__main__":
    main()
