"""Phase 3D — OFFLINE Sportmonks coverage-closure probe (READ-ONLY, ≤6 intentional requests).

Closes the Phase 3C UNKNOWNs: xG/pressure (club vs WC), odds across the 6 WC-732 seasons, expected
lineups, injuries/sidelined. SECRET-SAFE: token only from .env.yorian; never printed; scrubbed from
every saved sample (incl. echoed pagination URLs). No integration, no crawl.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/probe_sportmonks_coverage_closure.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3d_sportmonks_coverage_closure"
FB = "https://api.sportmonks.com/v3/football"
CORE = "https://api.sportmonks.com/v3/core"
TIMEOUT = 25
TOP_LEAGUES = "8,564,82"   # EPL, La Liga, Bundesliga (Sportmonks ids)


def token():
    for line in ENV.read_text().splitlines():
        if line.strip().startswith("SPORTMONKS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


TOK = token()


def scrub(o):
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    if isinstance(o, str):
        if TOK and TOK in o:
            return "***REDACTED***"
        if "api_token=" in o:
            return o.split("api_token=")[0] + "api_token=***REDACTED***"
    return o


def trim(o, n=20):
    if isinstance(o, dict):
        return {k: trim(v, n) for k, v in o.items()}
    if isinstance(o, list):
        return [trim(v, n) for v in o[:n]]
    return o


def save(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(scrub(trim(body)), indent=2))


def get(base, path, params=None):
    p = dict(params or {}); p["api_token"] = TOK
    try:
        r = requests.get(base + path, params=p, timeout=TIMEOUT)
        body = r.json()
        return r.status_code, body
    except Exception as e:
        return "ERR", {"_error": f"{type(e).__name__}: {str(e)[:100]}"}


def data(b):
    return b.get("data") if isinstance(b, dict) else None


def main():
    if not TOK:
        print("token missing"); return
    rows = []

    def row(fam, ep, status, nonempty, wc, club, prematch, oos, prio, note=""):
        rows.append(dict(data_family=fam, endpoint=ep, http=status, nonempty=nonempty,
                         wc_historical=wc, club_historical=club, prematch_live=prematch,
                         oos_backtest=oos, feature_lab_priority=prio, next_action=note))

    # ---- 1) type mapping: expected-lineup / xg / pressure ids ----
    st, b = get(CORE, "/types", {"per_page": 1000})
    save("01_core_types", b)
    types = data(b) or []
    def find(kw):
        return [(t.get("id"), t.get("name"), t.get("developer_name")) for t in types
                if kw in (str(t.get("name", "")) + str(t.get("developer_name", ""))).lower()]
    lineup_types = find("lineup")
    xg_types = find("expected goal") + find("xg")
    pressure_types = find("pressure")
    print(f"[types] page returned {len(types)} types")
    print(f"  lineup types: {lineup_types[:8]}")
    print(f"  xG types: {xg_types[:8]}")
    print(f"  pressure types: {pressure_types[:8]}")
    row("expected-lineup type map", "/core/types", st, bool(lineup_types), "n/a", "n/a",
        "forward only", "no", "RESEARCH",
        f"lineup type_ids: {[t[0] for t in lineup_types][:6]}")

    # ---- 2) WC-732 seasons + fixtures (has_odds per season) ----
    st, b = get(FB, "/leagues/732", {"include": "seasons.fixtures"})
    save("02_wc732_seasons_fixtures", b)
    league = data(b) or {}
    seasons = league.get("seasons") or []
    season_odds = []
    oldest_fid = None; oldest_name = None
    for s in sorted(seasons, key=lambda x: str(x.get("name", ""))):
        fx = s.get("fixtures") or []
        has = sum(1 for f in fx if f.get("has_odds"))
        season_odds.append((s.get("name"), s.get("id"), len(fx), has))
        if has and oldest_fid is None:
            cand = next((f for f in fx if f.get("has_odds")), None)
            if cand:
                oldest_fid, oldest_name = cand.get("id"), s.get("name")
    print(f"\n[WC-732] {len(seasons)} seasons; per-season (name,id,#fixtures_sampled,#has_odds):")
    for so in season_odds:
        print("  ", so)
    row("WC odds presence (has_odds)", "/leagues/732?include=seasons.fixtures", st,
        any(h for *_, h in season_odds), "yes" if any(h for *_, h in season_odds) else "no", "n/a",
        "yes", "yes", "READY",
        f"seasons w/ odds: {[ (n,h) for n,_,_,h in season_odds ]}")

    # ---- 3) odds markets on oldest WC fixture that has odds ----
    if oldest_fid:
        st, b = get(FB, f"/fixtures/{oldest_fid}", {"include": "odds"})
        save("03_wc_oldest_odds", b)
        odds = (data(b) or {}).get("odds") or []
        markets = sorted({o.get("market_description") for o in odds})
        relevant = [m for m in markets if any(w in str(m).lower() for w in
                    ("fulltime result", "over/under", "asian handicap", "match winner", "3-way"))]
        has_prob = any("probability" in o for o in odds)
        has_settle = any("winning" in o for o in odds)
        print(f"\n[oldest WC odds] season {oldest_name} fixture {oldest_fid}: {len(odds)} rows; "
              f"relevant markets {relevant[:8]}; probability={has_prob} winning={has_settle}")
        row("WC odds markets (historical)", f"/fixtures/{oldest_fid}?include=odds", st, bool(odds),
            "yes", "n/a", "yes", "yes", "READY",
            f"markets={relevant[:6]} prob={has_prob} settle={has_settle} season={oldest_name}")

    # ---- 4) xG on a recent CLUB fixture (prove include returns data) ----
    club_team = None
    st, b = get(FB, "/fixtures/between/2026-03-01/2026-05-26",
                {"filters": f"fixtureLeagues:{TOP_LEAGUES}", "include": "xGFixture;statistics;participants",
                 "per_page": 5})
    save("04_club_xg", b)
    fx = data(b) or []
    club_xg_nonempty = False
    for f in fx:
        xg = f.get("xgfixture") or f.get("xGFixture")
        if xg:
            club_xg_nonempty = True
        if f.get("participants"):
            club_team = f["participants"][0].get("id")
    stat_types = sorted({(s.get("type_id")) for f in fx for s in (f.get("statistics") or [])})[:15]
    print(f"\n[club xG] {len(fx)} recent club fixtures; xGFixture non-empty={club_xg_nonempty}; "
          f"stat type_ids sample={stat_types}")
    row("xG / pressure (club)", "/fixtures/between(club)?include=xGFixture;statistics", st,
        club_xg_nonempty, "n/a", "yes" if club_xg_nonempty else "unknown", "yes",
        "yes" if club_xg_nonempty else "unknown", "RESEARCH" if club_xg_nonempty else "WATCHLIST",
        f"club xGFixture {'returns data' if club_xg_nonempty else 'EMPTY — wrong include or no club xG'}")

    # ---- 5) xG/pressure on a WC-732 fixture ----
    if oldest_fid:
        st, b = get(FB, f"/fixtures/{oldest_fid}", {"include": "xGFixture;pressure;statistics"})
        save("05_wc_xg", b)
        d = data(b) or {}
        wc_xg = bool(d.get("xgfixture") or d.get("xGFixture"))
        wc_pressure = bool(d.get("pressure"))
        wc_stats = bool(d.get("statistics"))
        print(f"\n[WC xG] fixture {oldest_fid}: xG non-empty={wc_xg} pressure={wc_pressure} stats={wc_stats}")
        row("xG / pressure (WC)", f"/fixtures/{oldest_fid}?include=xGFixture;pressure;statistics", st,
            (wc_xg or wc_pressure), "yes" if (wc_xg or wc_pressure) else "no (empty)", "n/a",
            "maybe", "yes" if wc_xg else "no", "RESEARCH" if wc_xg else "KILL(for WC xG)",
            f"WC xG={wc_xg} pressure={wc_pressure} stats_present={wc_stats}")

    # ---- 6) injuries / sidelined on a current club team ----
    if club_team:
        st, b = get(FB, f"/teams/{club_team}", {"include": "sidelined.player"})
        save("06_injuries", b)
        d = data(b) or {}
        sl = d.get("sidelined") or []
        print(f"\n[injuries] team {club_team}: sidelined rows={len(sl)} "
              f"(include accepted={'_error' not in b}) fields={sorted(sl[0].keys()) if sl else 'none'}")
        row("injuries / sidelined", f"/teams/{club_team}?include=sidelined", st, bool(sl),
            "unknown", "yes" if sl else "unknown", "yes", "maybe",
            "RESEARCH" if sl else "WATCHLIST",
            f"sidelined rows={len(sl)} (empty=>no current injuries or entitlement)")

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "coverage_matrix.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {OUT}/coverage_matrix.csv + sanitized samples.")


if __name__ == "__main__":
    main()
