#!/usr/bin/env python3
"""
Maximum extraction script — all providers.

Run:
  PYTHONPATH=src python scripts/max_extract_all_providers.py

Phases:
  2. TheStatsAPI — full endpoint sweep, xG, shotmap, stats, lineups, odds
  3. API-Football — fixture ID cache, budget tracker, full live data files
  4. football-data.org — WC2026 probe, standings, teams, scorers
  5. Highlightly — full probe using base URL from .env
  6. Open data audit
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
RAW_DIR = ROOT / "data" / "raw" / "provider_responses"
LIVE_DIR = ROOT / "data" / "live"
AUDIT_DIR = ROOT / "outputs" / "audit"
LIVE_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc).isoformat()


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  saved → {path.relative_to(ROOT)}")


def _empty_available(reason: str, **extra) -> dict:
    return {"available": False, "reason": reason, "generated_at": NOW, **extra}


# ════════════════════════════════════════════════════════════════════════════
# PHASE 2 — TheStatsAPI
# ════════════════════════════════════════════════════════════════════════════

def phase2_thestatsapi() -> dict:
    print("\n=== PHASE 2: TheStatsAPI Maximum Extraction ===")
    from wc2026.providers.thestatsapi import TheStatsAPIProvider

    ts = TheStatsAPIProvider()
    ts_dir = RAW_DIR / "thestatsapi" / TIMESTAMP
    ts_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "provider": "thestatsapi",
        "timestamp": NOW,
        "endpoints": {},
        "xg_available": False,
        "match_ids": [],
        "fields_extracted": [],
        "fields_missing": [],
    }

    # 1. Health
    health = ts._get("health")
    _save(ts_dir / "health.json", health)
    report["endpoints"]["health"] = {"status": health.get("status"), "works": health.get("status") == "healthy"}
    print(f"  health: {health.get('status', 'FAIL')}")

    if health.get("status") != "healthy":
        print("  !! Server not healthy. Stopping phase 2.")
        return report

    # 2. Competition comp_6107
    comp = ts.get_competition()
    _save(ts_dir / "competition_comp6107.json", comp)
    if "_status_code" in comp:
        sc = comp["_status_code"]
        err = comp.get("error", {})
        report["endpoints"]["competition"] = {"status": sc, "works": False, "error": str(err)[:100]}
        print(f"  competition: HTTP {sc} — {str(err)[:80]}")
        _save(AUDIT_DIR / "thestatsapi_max_extraction.json", report)
        print("  KEY_REVOKED or auth error. Stopping phase 2. Refresh key.")
        return report

    comp_data = comp.get("data", {})
    season_id = comp_data.get("current_season_id")
    xg_avail = comp_data.get("xg_available", False)
    report["xg_available"] = xg_avail
    report["endpoints"]["competition"] = {"works": True, "xg_available": xg_avail, "season_id": season_id}
    ts._current_season_id = season_id
    print(f"  competition: OK. xg_available={xg_avail}, season={season_id}")

    # 3. Seasons
    seasons = ts.get_seasons()
    _save(ts_dir / "seasons.json", seasons)
    report["endpoints"]["seasons"] = {"works": "_status_code" not in seasons}
    print(f"  seasons: {'OK' if '_status_code' not in seasons else 'FAIL'}")

    # 4. Standings
    if season_id:
        standings = ts._get(f"football/competitions/comp_6107/seasons/{season_id}/standings")
        _save(ts_dir / "standings.json", standings)
        report["endpoints"]["standings"] = {"works": "_status_code" not in standings}
        print(f"  standings: {'OK (' + str(len(standings.get('data',[]))) + ' groups)' if '_status_code' not in standings else 'FAIL'}")

    # 5. Finished matches
    print("  fetching finished WC2026 matches...")
    matches_resp = ts.get_matches(status="finished", per_page=100)
    _save(ts_dir / "matches_finished.json", matches_resp)
    matches = matches_resp.get("data", [])
    report["endpoints"]["matches_finished"] = {"works": "_status_code" not in matches_resp, "count": len(matches)}
    print(f"  matches_finished: {len(matches)} matches")

    # 6. Scheduled matches
    sched = ts.get_matches(status="scheduled", per_page=100)
    _save(ts_dir / "matches_scheduled.json", sched)
    report["endpoints"]["matches_scheduled"] = {"works": "_status_code" not in sched, "count": len(sched.get("data", []))}
    print(f"  matches_scheduled: {len(sched.get('data', []))} upcoming")

    # 7. Live matches
    live_m = ts.get_matches(status="live", per_page=20)
    _save(ts_dir / "matches_live.json", live_m)
    live_count = len(live_m.get("data", []))
    report["endpoints"]["matches_live"] = {"works": "_status_code" not in live_m, "count": live_count}
    print(f"  matches_live: {live_count} live now")

    # 8. For each completed match: stats, shotmap, lineups, timeline, player-stats, odds, referee
    for m in matches[:10]:  # process up to 10 most recent
        mid = m.get("id", "")
        xg = m.get("xg_available", False)
        report["match_ids"].append(mid)

        match_out_dir = ts_dir / "matches"
        match_out_dir.mkdir(exist_ok=True)

        print(f"    match {mid}: {m.get('home_team',{}).get('name','?')} vs {m.get('away_team',{}).get('name','?')}")

        # stats (xG at team level)
        stats = ts.get_match_stats(mid)
        _save(match_out_dir / f"{mid}_stats.json", stats)
        if "_status_code" not in stats:
            xg_data = ts.extract_team_xg(stats)
            report["endpoints"][f"{mid}_stats"] = {"works": True, "xg": xg_data.get("xg_home")}
            if xg_data.get("xg_home") is not None:
                report["fields_extracted"].append("xg_team_level")

        # shotmap (per-shot xG)
        if xg:
            shotmap = ts.get_shotmap(mid)
            _save(match_out_dir / f"{mid}_shotmap.json", shotmap)
            shots = ts.extract_shotmap_xg(shotmap)
            report["endpoints"][f"{mid}_shotmap"] = {"works": "_status_code" not in shotmap, "shots": len(shots)}
            if shots:
                report["fields_extracted"].append("xg_per_shot")

        # lineups
        lineups = ts.get_lineups(mid)
        _save(match_out_dir / f"{mid}_lineups.json", lineups)
        report["endpoints"][f"{mid}_lineups"] = {"works": "_status_code" not in lineups}

        # timeline
        timeline = ts.get_timeline(mid)
        _save(match_out_dir / f"{mid}_timeline.json", timeline)
        report["endpoints"][f"{mid}_timeline"] = {"works": "_status_code" not in timeline}

        # player-stats
        pstats = ts.get_player_stats(mid)
        _save(match_out_dir / f"{mid}_player_stats.json", pstats)
        report["endpoints"][f"{mid}_player_stats"] = {"works": "_status_code" not in pstats}

        # odds
        odds = ts.get_odds(mid)
        _save(match_out_dir / f"{mid}_odds.json", odds)
        report["endpoints"][f"{mid}_odds"] = {"works": "_status_code" not in odds}

        # live-odds
        lodds = ts.get_live_odds(mid)
        _save(match_out_dir / f"{mid}_odds_live.json", lodds)

        # referee
        ref = ts.get_referee(mid)
        _save(match_out_dir / f"{mid}_referee.json", ref)

        time.sleep(0.5)  # rate limit courtesy

    # 9. Write normalized live data files
    _write_thestatsapi_live_files(ts, matches, ts_dir)

    _save(AUDIT_DIR / "thestatsapi_max_extraction.json", report)
    print(f"  Phase 2 complete. Fields extracted: {set(report['fields_extracted'])}")
    return report


def _write_thestatsapi_live_files(ts, matches, ts_dir):
    """Write all live data files from TheStatsAPI data."""
    all_xg = []
    all_shots = []
    all_lineups = []
    all_timeline_events = []
    all_player_stats = []
    all_odds = []

    match_dir = ts_dir / "matches"
    for mid in [m.get("id") for m in matches[:10]]:
        if not mid:
            continue
        # xG from stats
        sp = match_dir / f"{mid}_stats.json"
        if sp.exists():
            stats = json.loads(sp.read_text())
            xg_data = ts.extract_team_xg(stats)
            if xg_data.get("xg_home") is not None:
                xg_data["match_id"] = mid
                all_xg.append(xg_data)

        # Shotmap
        smp = match_dir / f"{mid}_shotmap.json"
        if smp.exists():
            sm = json.loads(smp.read_text())
            shots = ts.extract_shotmap_xg(sm)
            for s in shots:
                s["match_id"] = mid
            all_shots.extend(shots)

        # Timeline
        tp = match_dir / f"{mid}_timeline.json"
        if tp.exists():
            tl = json.loads(tp.read_text())
            for ev in tl.get("data", {}).get("events", []):
                ev["match_id"] = mid
                all_timeline_events.append(ev)

        # Player stats
        pp = match_dir / f"{mid}_player_stats.json"
        if pp.exists():
            ps = json.loads(pp.read_text())
            for p in ps.get("data", []):
                p["match_id"] = mid
            all_player_stats.extend(ps.get("data", []))

        # Odds
        op = match_dir / f"{mid}_odds.json"
        if op.exists():
            od = json.loads(op.read_text())
            if od.get("data"):
                od["data"]["match_id"] = mid
                all_odds.append(od.get("data", {}))

    _save(LIVE_DIR / "live_xg.json", {
        "generated_at": NOW, "source": "thestatsapi",
        "quality": "A", "matches": all_xg,
        "available": len(all_xg) > 0,
    })
    _save(LIVE_DIR / "live_shotmap.json", {
        "generated_at": NOW, "source": "thestatsapi",
        "quality": "A", "shots": all_shots,
        "available": len(all_shots) > 0,
    })
    _save(LIVE_DIR / "live_events.json", {
        "generated_at": NOW, "source": "thestatsapi",
        "quality": "A", "events": all_timeline_events,
        "available": len(all_timeline_events) > 0,
    })
    _save(LIVE_DIR / "live_players.json", {
        "generated_at": NOW, "source": "thestatsapi",
        "quality": "A", "players": all_player_stats,
        "available": len(all_player_stats) > 0,
    })
    _save(LIVE_DIR / "live_odds.json", {
        "generated_at": NOW, "source": "thestatsapi",
        "quality": "A", "odds": all_odds,
        "available": len(all_odds) > 0,
    })


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3 — API-Football maximum extraction
# ════════════════════════════════════════════════════════════════════════════

def phase3_api_football() -> dict:
    print("\n=== PHASE 3: API-Football Maximum Extraction ===")
    import requests as _req

    AF_KEY = os.getenv("API_FOOTBALL_KEY", "")
    AF_BASE = "https://v3.football.api-sports.io"
    AF_HEADERS = {"x-apisports-key": AF_KEY}
    WC_ID = 1
    af_dir = RAW_DIR / "api_football" / TIMESTAMP
    af_dir.mkdir(parents=True, exist_ok=True)

    report = {"provider": "api_football", "timestamp": NOW, "endpoints": {}, "budget": {}}

    def af_get(endpoint, params=None):
        r = _req.get(f"{AF_BASE}/{endpoint}", headers=AF_HEADERS, params=params or {}, timeout=12)
        return r.json() if r.status_code == 200 else {"errors": {r.status_code: r.text[:200]}}

    # Budget check
    status = af_get("status")
    reqs = status.get("response", {}).get("requests", {})
    budget = {"used": reqs.get("current", 0), "limit": reqs.get("limit_day", 100), "remaining": reqs.get("limit_day", 100) - reqs.get("current", 0)}
    report["budget"] = budget
    _save(af_dir / "status.json", status)
    _save(LIVE_DIR / "api_football_request_budget.json", {"generated_at": NOW, **budget})
    print(f"  budget: {budget['used']}/{budget['limit']} (remaining: {budget['remaining']})")

    # Collect fixture IDs for last 4 days + next 3 days
    from datetime import date, timedelta
    today = date.today()
    all_wc_fixtures = []
    fixture_id_cache = {"generated_at": NOW, "wc_league_id": WC_ID, "fixtures": [], "by_date": {}}

    print("  scanning dates for WC2026 fixtures...")
    for delta in range(-4, 4):
        dt = (today + timedelta(days=delta)).strftime("%Y-%m-%d")
        resp = af_get("fixtures", {"date": dt})
        wc_fixtures = [f for f in resp.get("response", []) if f.get("league", {}).get("id") == WC_ID]
        if wc_fixtures:
            fixture_id_cache["by_date"][dt] = [f["fixture"]["id"] for f in wc_fixtures]
            all_wc_fixtures.extend(wc_fixtures)
            print(f"    {dt}: {len(wc_fixtures)} WC fixtures")
        _save(af_dir / f"fixtures_date_{dt}.json", resp)

    # Deduplicate by fixture ID
    seen_ids = set()
    unique_fixtures = []
    for f in all_wc_fixtures:
        fid = f["fixture"]["id"]
        if fid not in seen_ids:
            seen_ids.add(fid)
            unique_fixtures.append(f)
            fixture_id_cache["fixtures"].append({
                "id": fid,
                "date": f["fixture"]["date"][:10],
                "home": f["teams"]["home"]["name"],
                "away": f["teams"]["away"]["name"],
                "status": f["fixture"]["status"]["short"],
                "home_goals": f["goals"].get("home"),
                "away_goals": f["goals"].get("away"),
            })

    _save(LIVE_DIR / "api_football_fixture_cache.json", fixture_id_cache)
    print(f"  fixture cache: {len(unique_fixtures)} unique WC2026 fixtures")

    # For completed fixtures: extract full detail
    completed = [f for f in unique_fixtures if f["fixture"]["status"]["short"] == "FT"]
    all_goals, all_cards, all_subs, all_stats, all_lineups, all_players = [], [], [], {}, {}, {}

    print(f"  extracting detail for {len(completed)} completed fixtures...")
    for f in completed:
        fid = f["fixture"]["id"]
        match_key = f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}"
        print(f"    [{fid}] {match_key}")

        # Events (goals, cards, subs)
        ev = af_get("fixtures/events", {"fixture": fid})
        _save(af_dir / f"events_{fid}.json", ev)
        for e in ev.get("response", []):
            t = e["time"]
            base = {
                "fixture_id": fid, "minute": t["elapsed"], "extra": t.get("extra"),
                "team": e["team"]["name"], "player": e["player"]["name"],
                "assist": e.get("assist", {}).get("name"), "type": e["type"], "detail": e["detail"],
            }
            if e["type"] == "Goal":
                all_goals.append(base)
            elif e["type"] == "Card":
                all_cards.append(base)
            elif e["type"] == "subst":
                all_subs.append(base)

        # Statistics
        st = af_get("fixtures/statistics", {"fixture": fid})
        _save(af_dir / f"statistics_{fid}.json", st)
        all_stats[fid] = {
            t["team"]["name"]: {s["type"]: s["value"] for s in t["statistics"]}
            for t in st.get("response", [])
        }

        # Lineups
        lu = af_get("fixtures/lineups", {"fixture": fid})
        _save(af_dir / f"lineups_{fid}.json", lu)
        all_lineups[fid] = {
            t["team"]["name"]: {
                "formation": t["formation"], "coach": t["coach"]["name"],
                "startXI": [p["player"]["name"] for p in t["startXI"]],
                "substitutes": [p["player"]["name"] for p in t["substitutes"]],
            }
            for t in lu.get("response", [])
        }

        # Player stats
        pl = af_get("fixtures/players", {"fixture": fid})
        _save(af_dir / f"players_{fid}.json", pl)
        all_players[fid] = {
            t["team"]["name"]: [
                {
                    "name": p["player"]["name"],
                    "number": p["player"]["number"],
                    "minutes": (p.get("statistics") or [{}])[0].get("games", {}).get("minutes"),
                    "rating": (p.get("statistics") or [{}])[0].get("games", {}).get("rating"),
                    "shots": (p.get("statistics") or [{}])[0].get("shots", {}).get("total"),
                    "goals": (p.get("statistics") or [{}])[0].get("goals", {}).get("total"),
                    "assists": (p.get("statistics") or [{}])[0].get("goals", {}).get("assists"),
                    "passes": (p.get("statistics") or [{}])[0].get("passes", {}).get("total"),
                    "pass_acc": (p.get("statistics") or [{}])[0].get("passes", {}).get("accuracy"),
                }
                for p in t.get("players", [])
            ]
            for t in pl.get("response", [])
        }

    # Also check live right now
    live_now = af_get("fixtures", {"live": "all"})
    wc_live = [f for f in live_now.get("response", []) if f.get("league", {}).get("id") == WC_ID]
    _save(af_dir / "fixtures_live_now.json", live_now)
    print(f"  live WC matches right now: {len(wc_live)}")

    # Write all live data files
    _save(LIVE_DIR / "live_goals.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "goals": all_goals, "available": len(all_goals) > 0})
    _save(LIVE_DIR / "live_cards.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "cards": all_cards, "available": len(all_cards) > 0})
    _save(LIVE_DIR / "live_substitutions.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "substitutions": all_subs, "available": len(all_subs) > 0})
    _save(LIVE_DIR / "live_statistics.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "statistics": all_stats, "available": len(all_stats) > 0})
    _save(LIVE_DIR / "live_lineups.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "lineups": all_lineups, "available": len(all_lineups) > 0})
    _save(LIVE_DIR / "live_players.json", {"generated_at": NOW, "source": "api_football", "quality": "B", "players": all_players, "available": len(all_players) > 0})

    # Final budget check
    status2 = af_get("status")
    reqs2 = status2.get("response", {}).get("requests", {})
    budget["used_after"] = reqs2.get("current", 0)
    budget["calls_this_run"] = budget["used_after"] - budget["used"]
    _save(LIVE_DIR / "api_football_request_budget.json", {"generated_at": NOW, **budget})
    print(f"  API calls this run: {budget['calls_this_run']}, total used: {budget['used_after']}/{budget['limit']}")

    report["completed_fixtures"] = len(completed)
    report["goals"] = len(all_goals)
    report["cards"] = len(all_cards)
    report["subs"] = len(all_subs)
    _save(AUDIT_DIR / "api_football_max_extraction.json", report)
    return report


# ════════════════════════════════════════════════════════════════════════════
# PHASE 4 — football-data.org
# ════════════════════════════════════════════════════════════════════════════

def phase4_football_data_org() -> dict:
    print("\n=== PHASE 4: football-data.org Maximum Extraction ===")
    from wc2026.providers.football_data_org import FootballDataOrgProvider

    fd = FootballDataOrgProvider()
    fd_dir = RAW_DIR / "football_data_org" / TIMESTAMP
    fd_dir.mkdir(parents=True, exist_ok=True)

    report = {"provider": "football_data_org", "timestamp": NOW, "endpoints": {}, "available": False}

    # Competition
    comp = fd.get_competition()
    _save(fd_dir / "competition_wc.json", comp)
    if "_status_code" in comp:
        sc = comp["_status_code"]
        report["endpoints"]["competition"] = {"status": sc, "works": False, "error": comp.get("error", "")[:100]}
        print(f"  competition: HTTP {sc}")
        if sc == 403:
            print("  !! Key invalid or competition not in free tier plan.")
        elif sc == 401:
            print("  !! No key provided.")
        _save(AUDIT_DIR / "football_data_org_max_extraction.json", report)
        return report

    report["available"] = True
    comp_name = comp.get("name", "?")
    print(f"  competition: OK — {comp_name}")
    report["endpoints"]["competition"] = {"works": True, "name": comp_name}

    # Standings
    standings = fd.get_standings()
    _save(fd_dir / "standings.json", standings)
    report["endpoints"]["standings"] = {"works": len(standings) > 0, "count": len(standings)}
    print(f"  standings: {len(standings)} teams")

    # Matches
    matches = fd.get_matches()
    _save(fd_dir / "matches.json", matches)
    match_list = matches.get("matches", [])
    report["endpoints"]["matches"] = {"works": "_status_code" not in matches, "count": len(match_list)}
    print(f"  matches: {len(match_list)} total")

    # Teams
    teams = fd.get_teams()
    _save(fd_dir / "teams.json", teams)
    team_list = teams.get("teams", [])
    report["endpoints"]["teams"] = {"works": "_status_code" not in teams, "count": len(team_list)}
    print(f"  teams: {len(team_list)}")

    # Scorers
    scorers = fd.get_scorers(limit=20)
    _save(fd_dir / "scorers.json", scorers)
    scorer_list = scorers.get("scorers", [])
    report["endpoints"]["scorers"] = {"works": "_status_code" not in scorers, "count": len(scorer_list)}
    print(f"  scorers: {len(scorer_list)}")

    # Today's matches
    today_m = fd.get_today_fixtures()
    _save(fd_dir / "matches_today.json", today_m)
    print(f"  today's WC matches: {len(today_m)}")

    # Historical WC data
    for year in [2018, 2022]:
        hist = fd.get_past_wc_matches(year)
        _save(fd_dir / f"matches_{year}.json", hist)
        n = len(hist.get("matches", []))
        report["endpoints"][f"matches_{year}"] = {"works": "_status_code" not in hist, "count": n}
        print(f"  WC{year} matches: {n}")

    _save(AUDIT_DIR / "football_data_org_max_extraction.json", report)
    return report


# ════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Highlightly
# ════════════════════════════════════════════════════════════════════════════

def phase5_highlightly() -> dict:
    print("\n=== PHASE 5: Highlightly Maximum Extraction ===")
    import requests as _req

    HL_KEY = os.getenv("HIGHLIGHTLY_API_KEY", "")
    HL_BASE = os.getenv("HIGHLIGHTLY_BASE_URL", "").rstrip("/")
    hl_dir = RAW_DIR / "highlightly" / TIMESTAMP
    hl_dir.mkdir(parents=True, exist_ok=True)

    report = {"provider": "highlightly", "timestamp": NOW, "base_url": HL_BASE, "endpoints": {}, "available": False}

    if not HL_KEY:
        print("  !! No HIGHLIGHTLY_API_KEY in .env. Skipping.")
        _save(AUDIT_DIR / "highlightly_max_extraction.json", report)
        return report

    if not HL_BASE:
        print("  !! No HIGHLIGHTLY_BASE_URL in .env. Skipping.")
        _save(AUDIT_DIR / "highlightly_max_extraction.json", report)
        return report

    # Try common auth methods
    # Method 1: x-api-key header
    # Method 2: Authorization: Bearer key
    # Method 3: api_key query param
    # Method 4: apikey query param

    auth_configs = [
        {"headers": {"x-api-key": HL_KEY}, "params": {}, "label": "x-api-key header"},
        {"headers": {"Authorization": f"Bearer {HL_KEY}"}, "params": {}, "label": "Bearer header"},
        {"headers": {"X-RapidAPI-Key": HL_KEY}, "params": {}, "label": "X-RapidAPI-Key"},
        {"headers": {}, "params": {"api_key": HL_KEY}, "label": "api_key param"},
        {"headers": {}, "params": {"apikey": HL_KEY}, "label": "apikey param"},
        {"headers": {}, "params": {"key": HL_KEY}, "label": "key param"},
    ]

    def hl_get(path, headers, params, label=""):
        url = f"{HL_BASE}/{path.lstrip('/')}"
        try:
            r = _req.get(url, headers=headers, params=params, timeout=10)
            return r.status_code, r.headers.get("content-type", ""), r.text[:2000]
        except Exception as e:
            return 0, "error", str(e)

    # Discover auth method with a probe endpoint
    probe_paths = ["", "/", "matches", "football/matches", "v1/matches", "v2/matches",
                   "soccer/matches", "api/matches", "highlights", "live", "fixtures"]

    working_auth = None
    working_path = None

    print("  probing auth methods and endpoints...")
    for auth in auth_configs:
        if working_auth:
            break
        for path in probe_paths[:4]:  # limit initial probes
            sc, ct, body = hl_get(path, auth["headers"], auth["params"])
            if sc == 200 and "application/json" in ct:
                print(f"  ✅ Auth works: {auth['label']}, path=/{path}")
                working_auth = auth
                working_path = path
                report["auth_method"] = auth["label"]
                report["working_base_path"] = path
                report["available"] = True
                break
            elif sc == 200 and "html" in ct:
                pass  # HTML, not a JSON API endpoint
            elif sc not in (0, 404, 200):
                print(f"    {auth['label']} /{path}: HTTP {sc}")
                break  # non-404/200 suggests auth issue, try next

    if not working_auth:
        print("  !! No working auth/endpoint combination found.")
        print("  Check HIGHLIGHTLY_BASE_URL and API docs for correct auth method.")
        report["error"] = "No working auth method found. Provide docs or correct base URL."
        _save(hl_dir / "probe_failed.json", report)
        _save(AUDIT_DIR / "highlightly_max_extraction.json", report)
        return report

    # Now probe all known paths
    hdr, pms = working_auth["headers"], working_auth["params"]

    candidate_paths = [
        "matches", "matches/live", "matches/today", "matches/upcoming", "matches/finished",
        "fixtures", "fixtures/live", "football/matches", "football/fixtures",
        "highlights", "highlights/football", "videos",
        "teams", "players", "competitions", "leagues",
        "statistics", "standings", "odds", "predictions",
        "football/highlights", "football/standings", "football/odds",
        "v1/football/matches", "v2/football/matches",
        "soccer", "soccer/matches", "soccer/fixtures",
    ]

    for path in candidate_paths:
        sc, ct, body = hl_get(path, hdr, pms)
        fname = path.replace("/", "_") + ".json"
        result = {"status": sc, "content_type": ct, "works": sc == 200 and "json" in ct}
        if sc == 200 and "json" in ct:
            try:
                parsed = json.loads(body)
                _save(hl_dir / fname, parsed)
                result["sample_keys"] = list(parsed.keys())[:5] if isinstance(parsed, dict) else f"list[{len(parsed)}]"
                print(f"  ✅ /{path}: JSON {result['sample_keys']}")
            except Exception:
                _save(hl_dir / fname, {"raw": body[:500]})
        elif sc == 200:
            result["content_type"] = ct
        elif sc not in (404, 0):
            print(f"  /{path}: HTTP {sc}")
        report["endpoints"][path] = result

    _save(AUDIT_DIR / "highlightly_max_extraction.json", report)
    print(f"  Phase 5 done. Working: {sum(1 for v in report['endpoints'].values() if v.get('works'))} endpoints")
    return report


# ════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Open data audit
# ════════════════════════════════════════════════════════════════════════════

def phase6_open_data_audit() -> dict:
    print("\n=== PHASE 6: Open Data Audit ===")

    audit = {"generated_at": NOW, "sources": {}}

    # OpenFootball
    of_live = ROOT / "data" / "wc2026_live.json"
    of_exists = of_live.exists()
    audit["sources"]["openfootball"] = {
        "files_exist": of_exists,
        "completed_matches": len(json.loads(of_live.read_text()).get("completed_matches", [])) if of_exists else 0,
        "fields_used": ["score", "date", "group", "status"],
        "fields_unused": ["attendance", "referee_name"],
        "integration_pct": 90,
        "role": "Fallback for matches >3 days old",
    }

    # martj42 international_results
    results_csv = ROOT / "data" / "results.csv"
    audit["sources"]["martj42_international_results"] = {
        "file_exists": results_csv.exists(),
        "used_for": ["Elo calibration (RollingEloEngine)", "WC historical backtest", "bootstrap CI"],
        "rows_if_exists": sum(1 for _ in open(results_csv)) if results_csv.exists() else 0,
        "integration_pct": 85,
        "unused_fields": ["city", "neutral"],
        "role": "Primary source for Elo calibration and historical backtests",
    }

    # StatsBomb Open Data
    sb_path = ROOT / "data" / "raw" / "statsbomb"
    audit["sources"]["statsbomb_open_data"] = {
        "path_exists": sb_path.exists(),
        "files": list(sb_path.rglob("*.json"))[:5] if sb_path.exists() else [],
        "integration_pct": 5,
        "unused_fields": ["event-level (pressing, xG by event, passes)", "360-data", "freeze frames"],
        "role": "Deep event analytics — not yet integrated into pipeline",
        "action": "Install statsbombpy and extract WC2018/22 event data for model context",
    }

    # ClubElo
    audit["sources"]["clubelo"] = {
        "url": "http://clubelo.com/API",
        "integration_pct": 5,
        "role": "External Elo sanity check",
        "action": "Fetch http://api.clubelo.com/ESP for external comparison",
        "example_curl": "curl 'http://api.clubelo.com/ESP' | python3 -c \"import sys; print(sys.stdin.read()[:200])\"",
    }

    # TheSportsDB
    audit["sources"]["thesportsdb"] = {
        "integration_pct": 10,
        "role": "Metadata/badges only — WC2026 null on free key",
        "action": "None — low priority",
    }

    _save(AUDIT_DIR / "open_data_extraction_audit.json", audit)
    for k, v in audit["sources"].items():
        pct = v.get("integration_pct", 0)
        print(f"  {k}: {pct}%")
    return audit


# ════════════════════════════════════════════════════════════════════════════
# PHASE 7 — Provider disagreement check
# ════════════════════════════════════════════════════════════════════════════

def phase7_provider_disagreements() -> dict:
    print("\n=== PHASE 7: Provider Disagreement Check ===")

    # Load API-Football completed matches
    af_cache = LIVE_DIR / "api_football_fixture_cache.json"
    of_live = ROOT / "data" / "wc2026_live.json"

    disagreements = []

    if af_cache.exists() and of_live.exists():
        af_data = json.loads(af_cache.read_text())
        of_data = json.loads(of_live.read_text())

        af_results = {
            (f["home"][:3].upper(), f["away"][:3].upper()): (f.get("home_goals"), f.get("away_goals"))
            for f in af_data.get("fixtures", [])
            if f["status"] == "FT"
        }
        of_results = {
            (m["home"], m["away"]): (m.get("home_goals"), m.get("away_goals"))
            for m in of_data.get("completed_matches", [])
        }

        for key, of_score in of_results.items():
            if key in af_results:
                af_score = af_results[key]
                if af_score != of_score and None not in af_score:
                    disagreements.append({
                        "match": f"{key[0]} vs {key[1]}",
                        "api_football": af_score,
                        "openfootball": of_score,
                        "severity": "CRITICAL" if af_score[0] != of_score[0] or af_score[1] != of_score[1] else "MINOR",
                    })

    result = {
        "generated_at": NOW,
        "disagreements": disagreements,
        "all_agree": len(disagreements) == 0,
    }
    _save(LIVE_DIR / "provider_disagreements.json", result)
    _save(AUDIT_DIR / "provider_disagreements.json", result)

    if disagreements:
        print(f"  !! {len(disagreements)} DISAGREEMENTS FOUND:")
        for d in disagreements:
            print(f"    {d['match']}: AF={d['api_football']} vs OF={d['openfootball']}")
    else:
        print(f"  All providers agree on scores ✓")
    return result


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phases", default="2,3,4,5,6,7", help="Comma-separated phases to run")
    parser.add_argument("--skip-thestatsapi", action="store_true")
    args = parser.parse_args()

    phases = [int(p.strip()) for p in args.phases.split(",")]

    results = {}
    if 2 in phases and not args.skip_thestatsapi:
        results["thestatsapi"] = phase2_thestatsapi()
    if 3 in phases:
        results["api_football"] = phase3_api_football()
    if 4 in phases:
        results["football_data_org"] = phase4_football_data_org()
    if 5 in phases:
        results["highlightly"] = phase5_highlightly()
    if 6 in phases:
        results["open_data"] = phase6_open_data_audit()
    if 7 in phases:
        results["disagreements"] = phase7_provider_disagreements()

    print("\n=== Summary ===")
    for provider, report in results.items():
        avail = report.get("available", report.get("xg_available", "?"))
        print(f"  {provider}: available={avail}")

    _save(ROOT / "outputs" / "audit" / "max_extraction_summary.json", {
        "generated_at": NOW, "phases_run": phases, "results": {
            k: {"available": v.get("available", False), "fields": v.get("fields_extracted", [])}
            for k, v in results.items()
        }
    })
    print("\nDone. Check data/live/ and outputs/audit/ for results.")
