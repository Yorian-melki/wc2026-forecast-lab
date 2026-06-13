#!/usr/bin/env python3
"""
Provider Battle Test — WC2026
Real API calls to all available providers.
Outputs: outputs/audit/provider_battle_test.json + .md + scorecard.csv + field_matrix.csv
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

OUT_AUDIT = ROOT / "outputs" / "audit"
OUT_RAW   = ROOT / "data" / "raw" / "provider_responses"
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
OUT_RAW_TS = OUT_RAW / TIMESTAMP
OUT_AUDIT.mkdir(parents=True, exist_ok=True)
OUT_RAW_TS.mkdir(parents=True, exist_ok=True)

API_FOOTBALL_KEY  = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
THESTATSAPI_KEY   = os.getenv("THESTATSAPI_KEY", "")
HIGHLIGHTLY_KEY   = os.getenv("HIGHLIGHTLY_API_KEY", "")
THESPORTSDB_KEY   = os.getenv("THESPORTSDB_API_KEY", "123")

# WC2026 fixture IDs to discover
WC2026_SEASON     = 2026
WC2026_NAME       = "FIFA World Cup"
TIMEOUT           = 12

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def save_raw(provider: str, endpoint: str, data: Any) -> Path:
    d = OUT_RAW_TS / provider
    d.mkdir(exist_ok=True)
    p = d / f"{endpoint}.json"
    p.write_text(json.dumps(data, indent=2, default=str))
    return p

def safe_get(url: str, headers: dict = None, params: dict = None, timeout: int = TIMEOUT) -> tuple[bool, Any, str]:
    try:
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)
        if r.status_code == 200:
            try:
                return True, r.json(), ""
            except Exception:
                return True, r.text, ""
        return False, None, f"HTTP {r.status_code}: {r.text[:300]}"
    except requests.Timeout:
        return False, None, "TIMEOUT"
    except Exception as e:
        return False, None, str(e)[:200]


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 1 — API-Football (api-sports.io)
# ─────────────────────────────────────────────────────────────────────────────
def test_api_football() -> dict:
    name = "api_football"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    if not API_FOOTBALL_KEY:
        result["errors"].append("API_FOOTBALL_KEY not set")
        result["auth_ok"] = False
        return result

    base = f"https://{API_FOOTBALL_HOST}"
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": API_FOOTBALL_HOST,
    }

    # 1. Status / auth check
    ok, data, err = safe_get(f"{base}/status", headers=headers)
    result["auth_ok"] = ok
    if ok and isinstance(data, dict):
        save_raw(name, "status", data)
        resp = data.get("response", {})
        result["plan"] = resp.get("subscription", {}).get("plan", "unknown")
        result["requests_remaining"] = resp.get("requests", {}).get("current")
        result["requests_limit"] = resp.get("requests", {}).get("limit_day")
        log(f"  Auth OK — plan: {result.get('plan')}, requests {result.get('requests_remaining')}/{result.get('requests_limit')}")
    else:
        result["errors"].append(f"auth: {err}")
        log(f"  Auth FAILED: {err}")
        return result

    # 2. Find WC2026 league
    ok, data, err = safe_get(f"{base}/leagues", headers=headers,
                              params={"name": "FIFA World Cup", "season": WC2026_SEASON})
    result["endpoint_results"]["leagues"] = ok
    league_id = None
    if ok and isinstance(data, dict):
        save_raw(name, "leagues_wc2026", data)
        leagues = data.get("response", [])
        if leagues:
            league_id = leagues[0].get("league", {}).get("id")
            result["wc2026_league_id"] = league_id
            log(f"  WC2026 league_id: {league_id}")
        else:
            # Try broader search
            ok2, data2, err2 = safe_get(f"{base}/leagues", headers=headers,
                                         params={"season": WC2026_SEASON, "type": "Cup"})
            if ok2 and isinstance(data2, dict):
                save_raw(name, "leagues_wc2026_broad", data2)
                for l in data2.get("response", []):
                    nm = l.get("league", {}).get("name", "")
                    if "World Cup" in nm or "FIFA" in nm:
                        league_id = l.get("league", {}).get("id")
                        result["wc2026_league_id"] = league_id
                        log(f"  WC2026 via broad search: {nm} id={league_id}")
                        break

    if not league_id:
        # Try with league id 1 (FIFA World Cup historically)
        for try_id in [1, 9, 30]:
            ok, data, err = safe_get(f"{base}/fixtures", headers=headers,
                                      params={"league": try_id, "season": WC2026_SEASON, "last": 5})
            if ok and isinstance(data, dict) and data.get("results", 0) > 0:
                league_id = try_id
                result["wc2026_league_id"] = league_id
                log(f"  Found WC2026 fixtures via league_id={try_id}")
                save_raw(name, f"fixtures_league_{try_id}", data)
                break

    # 3. Fixtures
    if league_id:
        ok, data, err = safe_get(f"{base}/fixtures", headers=headers,
                                  params={"league": league_id, "season": WC2026_SEASON, "last": 10})
        result["endpoint_results"]["fixtures"] = ok
        fixtures = []
        if ok and isinstance(data, dict):
            save_raw(name, "fixtures_recent", data)
            fixtures = data.get("response", [])
            result["fixtures_count"] = len(fixtures)
            result["fields_found"].extend(["fixtures_basic", "fixture_id", "date", "teams", "goals"])
            log(f"  Recent fixtures: {len(fixtures)}")

        # Live fixtures
        ok, data, err = safe_get(f"{base}/fixtures", headers=headers,
                                  params={"league": league_id, "season": WC2026_SEASON, "live": "all"})
        result["endpoint_results"]["live_fixtures"] = ok
        live_fixtures = []
        if ok and isinstance(data, dict):
            save_raw(name, "fixtures_live", data)
            live_fixtures = data.get("response", [])
            result["live_fixtures_count"] = len(live_fixtures)
            log(f"  Live fixtures: {len(live_fixtures)}")

        # Today's fixtures
        today = datetime.now().strftime("%Y-%m-%d")
        ok, data, err = safe_get(f"{base}/fixtures", headers=headers,
                                  params={"league": league_id, "season": WC2026_SEASON, "date": today})
        result["endpoint_results"]["today_fixtures"] = ok
        if ok and isinstance(data, dict):
            save_raw(name, "fixtures_today", data)
            today_fixt = data.get("response", [])
            result["today_fixtures_count"] = len(today_fixt)
            log(f"  Today's fixtures ({today}): {len(today_fixt)}")
            for f in today_fixt:
                h = f.get("teams", {}).get("home", {}).get("name", "")
                a = f.get("teams", {}).get("away", {}).get("name", "")
                status = f.get("fixture", {}).get("status", {}).get("short", "")
                score_h = f.get("goals", {}).get("home")
                score_a = f.get("goals", {}).get("away")
                minute  = f.get("fixture", {}).get("status", {}).get("elapsed")
                log(f"    {h} {score_h}–{score_a} {a} [{status}] min={minute}")
                result.setdefault("today_matches", []).append({
                    "home": h, "away": a, "status": status,
                    "score": f"{score_h}–{score_a}", "minute": minute,
                })

        # Stats for a fixture if available
        all_fixt = live_fixtures or fixtures
        if all_fixt:
            fixt_id = all_fixt[0].get("fixture", {}).get("id")
            ok, data, err = safe_get(f"{base}/fixtures/statistics", headers=headers,
                                      params={"fixture": fixt_id})
            result["endpoint_results"]["statistics"] = ok
            if ok and isinstance(data, dict):
                save_raw(name, "statistics_sample", data)
                stats = data.get("response", [])
                if stats:
                    stat_types = [s.get("type") for team in stats for s in team.get("statistics", [])]
                    result["stat_types_available"] = list(set(stat_types))
                    has_xg = any("xG" in str(t) or "Expected Goals" in str(t) for t in stat_types)
                    result["has_xg_in_stats"] = has_xg
                    log(f"  Stats for fixture {fixt_id}: {len(stat_types)} types, xG={has_xg}")
                    if has_xg:
                        result["fields_found"].append("xG")
                    result["fields_found"].extend(["possession", "shots", "shots_on_target", "corners", "fouls", "cards"])

            # Events
            ok, data, err = safe_get(f"{base}/fixtures/events", headers=headers,
                                      params={"fixture": fixt_id})
            result["endpoint_results"]["events"] = ok
            if ok and isinstance(data, dict):
                save_raw(name, "events_sample", data)
                evts = data.get("response", [])
                evt_types = list(set(e.get("type", "") for e in evts))
                result["event_types"] = evt_types
                result["events_count"] = len(evts)
                result["fields_found"].append("events")
                log(f"  Events for fixture {fixt_id}: {len(evts)} ({evt_types})")

            # Lineups
            ok, data, err = safe_get(f"{base}/fixtures/lineups", headers=headers,
                                      params={"fixture": fixt_id})
            result["endpoint_results"]["lineups"] = ok
            if ok and isinstance(data, dict):
                save_raw(name, "lineups_sample", data)
                lineups = data.get("response", [])
                result["has_lineups"] = len(lineups) > 0
                result["fields_found"].append("lineups")
                log(f"  Lineups: {len(lineups)} teams")

    # 4. Standings
    if league_id:
        ok, data, err = safe_get(f"{base}/standings", headers=headers,
                                  params={"league": league_id, "season": WC2026_SEASON})
        result["endpoint_results"]["standings"] = ok
        if ok and isinstance(data, dict):
            save_raw(name, "standings", data)
            standings = data.get("response", [])
            result["has_standings"] = len(standings) > 0
            if standings:
                result["fields_found"].append("standings")
            log(f"  Standings: {len(standings)} groups/entries")

    # 5. Odds
    if league_id and fixtures:
        fixt_id = fixtures[-1].get("fixture", {}).get("id")
        ok, data, err = safe_get(f"{base}/odds", headers=headers,
                                  params={"fixture": fixt_id})
        result["endpoint_results"]["odds"] = ok
        if ok and isinstance(data, dict):
            save_raw(name, "odds_sample", data)
            odds_data = data.get("response", [])
            result["has_odds"] = len(odds_data) > 0
            if odds_data:
                bookmakers = [b.get("bookmaker", {}).get("name") for o in odds_data for b in o.get("bookmakers", [])]
                result["bookmakers"] = list(set(bookmakers))[:5]
                result["fields_found"].append("odds")
            log(f"  Odds: {len(odds_data)} entries, bookmakers: {result.get('bookmakers', [])}")

    # 6. Injuries
    if league_id:
        ok, data, err = safe_get(f"{base}/injuries", headers=headers,
                                  params={"league": league_id, "season": WC2026_SEASON})
        result["endpoint_results"]["injuries"] = ok
        if ok and isinstance(data, dict):
            save_raw(name, "injuries", data)
            inj_count = len(data.get("response", []))
            result["injuries_count"] = inj_count
            if inj_count > 0:
                result["fields_found"].append("injuries")
            log(f"  Injuries: {inj_count}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 2 — TheStatsAPI
# ─────────────────────────────────────────────────────────────────────────────
def test_thestatsapi() -> dict:
    name = "thestatsapi"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    if not THESTATSAPI_KEY:
        result["errors"].append("THESTATSAPI_KEY not set")
        result["auth_ok"] = False
        return result

    base    = "https://api.thestatsapi.com/v1"
    headers = {"X-API-Key": THESTATSAPI_KEY}

    # 1. Test auth / competitions
    ok, data, err = safe_get(f"{base}/competitions", headers=headers)
    result["auth_ok"] = ok
    if not ok:
        result["errors"].append(f"auth: {err}")
        log(f"  Auth FAILED: {err}")
        # Try alternative base
        for alt_base in ["https://api.thestatsapi.com", "https://thestatsapi.com/api/v1"]:
            ok2, data2, err2 = safe_get(f"{alt_base}/competitions", headers=headers)
            if ok2:
                log(f"  OK with alt base: {alt_base}")
                base = alt_base
                data = data2
                result["auth_ok"] = True
                result["errors"] = []
                ok = True
                break
        if not ok:
            return result

    save_raw(name, "competitions", data)
    comps = data if isinstance(data, list) else data.get("data", data.get("competitions", []))
    result["competitions_count"] = len(comps) if isinstance(comps, list) else 0
    log(f"  Auth OK — competitions: {result['competitions_count']}")

    # Find WC2026
    wc_comp_id = None
    if isinstance(comps, list):
        for c in comps:
            name_c = str(c.get("name", "") or c.get("competition_name", "")).lower()
            if "world cup" in name_c or "fifa" in name_c:
                wc_comp_id = c.get("id") or c.get("competition_id") or c.get("competition_key")
                result["wc2026_comp_id"] = wc_comp_id
                log(f"  WC found: {c.get('name')} id={wc_comp_id}")
                break

    # 2. Seasons
    ok, data, err = safe_get(f"{base}/seasons", headers=headers,
                              params={"competition_id": wc_comp_id} if wc_comp_id else {})
    result["endpoint_results"]["seasons"] = ok
    if ok:
        save_raw(name, "seasons", data)
        seasons = data if isinstance(data, list) else data.get("data", [])
        result["seasons_count"] = len(seasons) if isinstance(seasons, list) else 0
        log(f"  Seasons: {result['seasons_count']}")

    # 3. Fixtures / matches today
    today = datetime.now().strftime("%Y-%m-%d")
    params_today = {"date": today}
    if wc_comp_id:
        params_today["competition_id"] = wc_comp_id
    ok, data, err = safe_get(f"{base}/fixtures", headers=headers, params=params_today)
    result["endpoint_results"]["fixtures_today"] = ok
    if ok:
        save_raw(name, "fixtures_today", data)
        fixes = data if isinstance(data, list) else data.get("data", data.get("fixtures", []))
        result["today_fixtures_count"] = len(fixes) if isinstance(fixes, list) else 0
        log(f"  Today fixtures: {result['today_fixtures_count']}")
        if isinstance(fixes, list):
            for f in fixes[:3]:
                h   = f.get("home_team", {}).get("name", "") or f.get("home_team_name", "")
                a   = f.get("away_team", {}).get("name", "") or f.get("away_team_name", "")
                sc  = f.get("score", "") or f"{f.get('home_score','')}–{f.get('away_score','')}"
                st  = f.get("status", "") or f.get("match_status", "")
                mn  = f.get("minute", "") or f.get("elapsed", "")
                log(f"    {h} {sc} {a} [{st}] min={mn}")

    # 4. Live matches
    ok, data, err = safe_get(f"{base}/fixtures/live", headers=headers)
    result["endpoint_results"]["live"] = ok
    if ok:
        save_raw(name, "fixtures_live", data)
        lives = data if isinstance(data, list) else data.get("data", [])
        result["live_count"] = len(lives) if isinstance(lives, list) else 0
        log(f"  Live matches: {result['live_count']}")

    # 5. Sample statistics
    ok, data, err = safe_get(f"{base}/statistics", headers=headers,
                              params={"date": today} if not wc_comp_id else {"competition_id": wc_comp_id, "date": today})
    result["endpoint_results"]["statistics"] = ok
    if ok and data:
        save_raw(name, "statistics_today", data)
        stats_sample = data if isinstance(data, list) else data.get("data", [])
        if isinstance(stats_sample, list) and stats_sample:
            sample = stats_sample[0]
            stat_keys = list(sample.keys())
            has_xg = any("xg" in k.lower() or "expected" in k.lower() for k in stat_keys)
            result["has_xg"] = has_xg
            result["stat_keys"] = stat_keys[:20]
            if has_xg:
                result["fields_found"].append("xG")
            log(f"  Stat keys: {stat_keys[:10]}, xG={has_xg}")

    # 6. Standings
    params_stand = {"season": WC2026_SEASON}
    if wc_comp_id:
        params_stand["competition_id"] = wc_comp_id
    ok, data, err = safe_get(f"{base}/standings", headers=headers, params=params_stand)
    result["endpoint_results"]["standings"] = ok
    if ok and data:
        save_raw(name, "standings", data)
        result["has_standings"] = bool(data.get("data") or isinstance(data, list))
        log(f"  Standings: {result['has_standings']}")

    # 7. Plan info
    ok, data, err = safe_get(f"{base}/status", headers=headers)
    if not ok:
        ok, data, err = safe_get(f"{base}/account", headers=headers)
    result["endpoint_results"]["status"] = ok
    if ok and data:
        save_raw(name, "status", data)
        result["plan"] = str(data.get("plan") or data.get("subscription") or "unknown")
        log(f"  Plan: {result['plan']}")

    if result.get("today_fixtures_count", 0) > 0:
        result["fields_found"].extend(["fixtures_basic", "live_score"])
    if result.get("has_standings"):
        result["fields_found"].append("standings")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 3 — Highlightly
# ─────────────────────────────────────────────────────────────────────────────
def test_highlightly() -> dict:
    name = "highlightly"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    if not HIGHLIGHTLY_KEY:
        result["errors"].append("HIGHLIGHTLY_API_KEY not set")
        result["auth_ok"] = False
        return result

    base    = "https://api.highlightly.net/v1"
    headers = {"X-Auth-Token": HIGHLIGHTLY_KEY}

    # Try different auth header names
    for auth_header in ["X-Auth-Token", "Authorization", "x-api-key", "api-key"]:
        h = {auth_header: HIGHLIGHTLY_KEY if auth_header != "Authorization" else f"Bearer {HIGHLIGHTLY_KEY}"}
        ok, data, err = safe_get(f"{base}/football/matches", headers=h,
                                  params={"date": datetime.now().strftime("%Y-%m-%d")})
        if ok:
            headers = h
            result["auth_header"] = auth_header
            log(f"  Auth OK with header: {auth_header}")
            break
    else:
        # Try alternative bases
        for alt_base in ["https://highlightly.net/api/v1", "https://api.highlightly.net"]:
            ok, data, err = safe_get(f"{alt_base}/football/matches", headers={"x-api-key": HIGHLIGHTLY_KEY},
                                      params={"date": datetime.now().strftime("%Y-%m-%d")})
            if ok:
                base = alt_base
                headers = {"x-api-key": HIGHLIGHTLY_KEY}
                result["auth_ok"] = True
                log(f"  Auth OK with alt base: {alt_base}")
                break
        else:
            result["auth_ok"] = False
            result["errors"].append(f"All auth attempts failed. Last: {err}")
            log(f"  Auth FAILED on all attempts")
            return result

    result["auth_ok"] = True
    save_raw(name, "matches_today", data)
    today_matches = data if isinstance(data, list) else data.get("data", data.get("matches", []))
    result["today_count"] = len(today_matches) if isinstance(today_matches, list) else 0
    log(f"  Today matches: {result['today_count']}")

    # Try to find highlights
    ok, data2, err = safe_get(f"{base}/football/highlights", headers=headers,
                               params={"date": datetime.now().strftime("%Y-%m-%d")})
    result["endpoint_results"]["highlights"] = ok
    if ok and data2:
        save_raw(name, "highlights_today", data2)
        hl = data2 if isinstance(data2, list) else data2.get("data", [])
        result["highlights_count"] = len(hl) if isinstance(hl, list) else 0
        log(f"  Highlights: {result['highlights_count']}")
        if result["highlights_count"] > 0:
            result["fields_found"].append("highlights")

    # Check coverage / competitions
    ok, data3, err = safe_get(f"{base}/football/competitions", headers=headers)
    result["endpoint_results"]["competitions"] = ok
    if ok and data3:
        save_raw(name, "competitions", data3)
        comps = data3 if isinstance(data3, list) else data3.get("data", [])
        result["competitions_count"] = len(comps) if isinstance(comps, list) else 0
        log(f"  Competitions covered: {result['competitions_count']}")
        if isinstance(comps, list):
            wc_covered = any("world" in str(c).lower() for c in comps)
            result["wc_covered"] = wc_covered
            log(f"  WC in coverage: {wc_covered}")

    if result.get("today_count", 0) > 0:
        result["fields_found"].append("fixtures_basic")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 4 — TheSportsDB
# ─────────────────────────────────────────────────────────────────────────────
def test_thesportsdb() -> dict:
    name = "thesportsdb"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    key = THESPORTSDB_KEY or "123"
    base = f"https://www.thesportsdb.com/api/v1/json/{key}"

    # 1. Today's events
    today = datetime.now().strftime("%Y-%m-%d")
    ok, data, err = safe_get(f"{base}/eventsday.php", params={"d": today, "s": "Soccer"})
    result["auth_ok"] = ok
    result["endpoint_results"]["events_today"] = ok
    if ok and data:
        save_raw(name, "events_today", data)
        evts = data.get("events") or []
        result["today_count"] = len(evts) if evts else 0
        log(f"  Today events: {result['today_count']}")
        if evts:
            result["fields_found"].append("fixtures_basic")
            for e in evts[:3]:
                h   = e.get("strHomeTeam", "")
                a   = e.get("strAwayTeam", "")
                sc  = f"{e.get('intHomeScore','')}–{e.get('intAwayScore','')}"
                st  = e.get("strStatus", "")
                log(f"    {h} {sc} {a} [{st}]")

    # 2. WC2026 league search
    ok, data, err = safe_get(f"{base}/searchleagues.php", params={"t": "FIFA World Cup"})
    result["endpoint_results"]["league_search"] = ok
    wc_league_id = None
    if ok and data:
        save_raw(name, "league_search_wc", data)
        leagues = data.get("leagues") or data.get("countrys") or []
        if leagues:
            for l in leagues:
                if "World Cup" in str(l.get("strLeague", "")) or "FIFA" in str(l.get("strLeague", "")):
                    wc_league_id = l.get("idLeague")
                    result["wc_league_id"] = wc_league_id
                    log(f"  WC league: {l.get('strLeague')} id={wc_league_id}")
                    break

    # 3. Recent WC events
    if wc_league_id:
        ok, data, err = safe_get(f"{base}/eventsnextleague.php", params={"id": wc_league_id})
        result["endpoint_results"]["next_events"] = ok
        if ok and data:
            save_raw(name, "wc_next_events", data)
            evts = data.get("events") or []
            result["wc_next_count"] = len(evts)
            log(f"  WC next events: {len(evts)}")

        ok, data, err = safe_get(f"{base}/eventspastleague.php", params={"id": wc_league_id})
        result["endpoint_results"]["past_events"] = ok
        if ok and data:
            save_raw(name, "wc_past_events", data)
            evts = data.get("events") or []
            result["wc_past_count"] = len(evts)
            log(f"  WC past events: {len(evts)}")
            if evts:
                e = evts[0]
                avail = [k for k in e if e[k]]
                result["fields_found"].append("fixtures_basic")
                log(f"  Sample event keys with data: {avail[:15]}")

    # 4. Team lookup
    ok, data, err = safe_get(f"{base}/searchteams.php", params={"t": "Brazil"})
    result["endpoint_results"]["team_search"] = ok
    if ok and data:
        save_raw(name, "team_search_brazil", data)
        teams = data.get("teams") or []
        if teams:
            t = teams[0]
            has_badge = bool(t.get("strTeamBadge") or t.get("strTeamLogo"))
            has_photo = bool(t.get("strTeamFanart1") or t.get("strTeamJersey"))
            result["has_team_badges"] = has_badge
            result["has_team_photos"] = has_photo
            if has_badge:
                result["fields_found"].append("team_metadata")
            log(f"  Team metadata: badge={has_badge}, photos={has_photo}")

    # 5. Live scores (requires paid plan)
    ok, data, err = safe_get(f"https://www.thesportsdb.com/api/v2/json/{key}/livescores.php",
                              params={"s": "Soccer"})
    result["endpoint_results"]["livescores"] = ok
    if ok and data:
        save_raw(name, "livescores", data)
        sc = data.get("livescores") or []
        result["live_count"] = len(sc)
        log(f"  Live scores (v2): {len(sc)}")
        if sc:
            result["fields_found"].append("live_score")
    else:
        result["livescores_error"] = err[:100] if err else "empty"
        log(f"  Live scores: FAILED ({err[:80] if err else 'empty'})")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 5 — OpenFootball fallback
# ─────────────────────────────────────────────────────────────────────────────
def test_openfootball() -> dict:
    name = "openfootball"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    url = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
    ok, data, err = safe_get(url)
    result["auth_ok"] = ok
    result["endpoint_results"]["worldcup_json"] = ok
    if ok:
        save_raw(name, "worldcup_2026", data)
        if isinstance(data, dict):
            rounds = data.get("rounds", [])
            all_matches = [m for r in rounds for m in r.get("matches", [])]
            completed = [m for m in all_matches if m.get("score")]
            result["total_matches"]   = len(all_matches)
            result["completed_matches"] = len(completed)
            result["fields_found"]    = ["fixtures_basic", "score", "date", "group"]
            log(f"  OK — total={len(all_matches)} completed={len(completed)}")
            if completed:
                m = completed[-1]
                log(f"  Last completed: {m.get('team1',{}).get('name')} {m.get('score',{}).get('ft','?')} {m.get('team2',{}).get('name')}")
                result["last_completed"] = {
                    "home": m.get("team1", {}).get("name", ""),
                    "away": m.get("team2", {}).get("name", ""),
                    "score": str(m.get("score", {}).get("ft", "?")),
                    "date": m.get("date", ""),
                }
    else:
        result["errors"].append(f"fetch failed: {err}")
        log(f"  FAILED: {err}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER 6 — Local manual fallback
# ─────────────────────────────────────────────────────────────────────────────
def test_local_manual() -> dict:
    name = "local_manual"
    log(f"=== Testing {name} ===")
    result: dict = {"provider": name, "endpoint_results": {}, "fields_found": [], "errors": []}

    live_path = ROOT / "data" / "wc2026_live.json"
    result["auth_ok"] = True  # local, always accessible
    result["endpoint_results"]["wc2026_live_json"] = live_path.exists()
    if live_path.exists():
        data = json.loads(live_path.read_text())
        result["last_updated"] = data.get("last_updated", "unknown")
        completed = data.get("completed_matches", [])
        result["completed_count"] = len(completed)
        result["fields_found"] = ["score", "date", "group", "scorers", "notes", "injuries", "standings"]
        log(f"  Local JSON: {len(completed)} completed, last_updated={result['last_updated']}")
        # Check staleness
        try:
            upd = datetime.strptime(result["last_updated"], "%Y-%m-%d")
            today = datetime.now()
            days_old = (today - upd).days
            result["days_stale"] = days_old
            log(f"  Staleness: {days_old} days old")
        except Exception:
            result["days_stale"] = 999
    else:
        result["errors"].append("data/wc2026_live.json not found")
        log("  MISSING")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "live_score":       0.20,
    "in_play_stats":    0.20,
    "xG":               0.15,
    "events_lineups":   0.15,
    "odds":             0.10,
    "historical":       0.10,
    "metadata":         0.05,
    "reliability":      0.05,
}

FIELDS_TO_CATEGORY = {
    "live_score":       ["live_score"],
    "in_play_stats":    ["possession", "shots", "shots_on_target", "corners", "fouls", "cards"],
    "xG":               ["xG"],
    "events_lineups":   ["events", "lineups"],
    "odds":             ["odds"],
    "historical":       ["fixtures_basic"],
    "metadata":         ["team_metadata", "highlights"],
    "reliability":      [],  # computed from auth_ok
}

def score_provider(result: dict) -> dict:
    fields = set(result.get("fields_found", []))
    auth   = result.get("auth_ok", False)
    errors = result.get("errors", [])
    score  = 0.0
    breakdown = {}

    for category, weight in SCORE_WEIGHTS.items():
        cat_fields  = FIELDS_TO_CATEGORY.get(category, [])
        if category == "reliability":
            cat_score = 1.0 if auth and len(errors) == 0 else (0.5 if auth else 0.0)
        elif category == "historical":
            cat_score = 1.0 if "fixtures_basic" in fields else 0.0
            if result.get("wc2026_league_id") or result.get("wc2026_comp_id"):
                cat_score = min(cat_score + 0.5, 1.0)
        else:
            matched = [f for f in cat_fields if f in fields]
            cat_score = len(matched) / max(len(cat_fields), 1) if cat_fields else 0.0
        breakdown[category] = round(cat_score * weight * 100, 2)
        score += cat_score * weight

    return {"total": round(score * 100, 1), "breakdown": breakdown}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("WC2026 Provider Battle Test — Real API Calls")
    log(f"Timestamp: {TIMESTAMP}")
    log("=" * 60)

    results = {}
    for probe_fn, key in [
        (test_api_football,  "api_football"),
        (test_thestatsapi,   "thestatsapi"),
        (test_highlightly,   "highlightly"),
        (test_thesportsdb,   "thesportsdb"),
        (test_openfootball,  "openfootball"),
        (test_local_manual,  "local_manual"),
    ]:
        try:
            res = probe_fn()
        except Exception as e:
            log(f"  ERROR in {key}: {e}")
            res = {"provider": key, "auth_ok": False,
                   "errors": [traceback.format_exc()[:500]], "fields_found": []}
        res["score"] = score_provider(res)
        results[key] = res
        time.sleep(0.5)

    # Determine primary decision
    sorted_prov = sorted(results.items(), key=lambda x: x[1]["score"]["total"], reverse=True)
    primary   = sorted_prov[0][0] if sorted_prov else "local_manual"
    secondary = sorted_prov[1][0] if len(sorted_prov) > 1 else "openfootball"

    decision = {
        "timestamp": TIMESTAMP,
        "primary_live_provider": primary,
        "secondary_fallback": secondary,
        "metadata_provider": "thesportsdb",
        "highlights_provider": "highlightly" if results.get("highlightly", {}).get("auth_ok") else "none",
        "primary_score": results[primary]["score"]["total"],
        "reasoning": {
            "api_football": "Real-time live data, stats, events, lineups — highest completeness if WC league accessible",
            "thestatsapi":  "Modern API, check plan level — Growth plan needed for WC2026",
            "highlightly":  "Highlights/media focus, supplementary",
            "thesportsdb":  "Metadata/badges only, free tier limited for live",
            "openfootball": "Open source JSON, very fast, but human-maintained — lags by 1-24h",
            "local_manual": "Zero latency fallback, manually maintained, always stale",
        },
        "live_data_current": any(
            r.get("live_fixtures_count", r.get("live_count", 0)) > 0
            for r in results.values()
        ),
    }

    # Save main output
    output = {
        "decision": decision,
        "provider_results": results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = OUT_AUDIT / "provider_battle_test.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    log(f"\nSaved: {out_path}")

    # Save scorecard CSV
    import csv
    scorecard_path = OUT_AUDIT / "provider_scorecard.csv"
    with open(scorecard_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["provider", "auth_ok", "total_score"] + list(SCORE_WEIGHTS.keys()) + ["errors"])
        w.writeheader()
        for key, res in results.items():
            row = {
                "provider": key,
                "auth_ok": res.get("auth_ok", False),
                "total_score": res["score"]["total"],
                **{cat: res["score"]["breakdown"].get(cat, 0) for cat in SCORE_WEIGHTS},
                "errors": "; ".join(res.get("errors", [])),
            }
            w.writerow(row)
    log(f"Saved: {scorecard_path}")

    # Save field matrix CSV
    all_fields = sorted(set(f for res in results.values() for f in res.get("fields_found", [])))
    field_matrix_path = OUT_AUDIT / "provider_field_matrix.csv"
    with open(field_matrix_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["field"] + [k for k in results])
        for field in all_fields:
            row = [field]
            for key in results:
                row.append("✓" if field in results[key].get("fields_found", []) else "")
            w.writerow(row)
    log(f"Saved: {field_matrix_path}")

    # Markdown report
    md = [
        "# Provider Battle Test — WC2026",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        "\n## Decision",
        f"\n- **Primary live provider**: `{primary}` (score: {results[primary]['score']['total']}/100)",
        f"- **Secondary fallback**: `{secondary}`",
        f"- **Metadata**: TheSportsDB",
        f"- **Highlights**: {decision['highlights_provider']}",
        f"- **Live data currently fresh**: {decision['live_data_current']}",
        "\n## Provider Scores\n",
        "| Provider | Auth | Score | live_score | in_play_stats | xG | events | odds | historical |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key, res in results.items():
        b = res["score"]["breakdown"]
        auth_icon = "✅" if res.get("auth_ok") else "❌"
        md.append(
            f"| {key} | {auth_icon} | **{res['score']['total']}** | "
            f"{b.get('live_score',0)} | {b.get('in_play_stats',0)} | {b.get('xG',0)} | "
            f"{b.get('events_lineups',0)} | {b.get('odds',0)} | {b.get('historical',0)} |"
        )

    md.append("\n## Fields Available by Provider\n")
    md.append("| Field | " + " | ".join(results.keys()) + " |")
    md.append("|---|" + "---|" * len(results))
    for field in all_fields:
        row = f"| {field} |"
        for key in results:
            row += " ✓ |" if field in results[key].get("fields_found", []) else " |"
        md.append(row)

    md.append("\n## Missing Fields (no provider covers)\n")
    wanted = ["xG", "lineups", "odds", "events", "injuries", "live_score", "in_play_stats"]
    for field in wanted:
        covered = [k for k, res in results.items() if field in res.get("fields_found", [])]
        if not covered:
            md.append(f"- ❌ **{field}** — NOT covered by any available provider/plan")
        elif len(covered) == 1:
            md.append(f"- ⚠️ **{field}** — single-source only: {covered[0]}")
        else:
            md.append(f"- ✅ **{field}** — covered by: {', '.join(covered)}")

    md.append("\n## Manual Actions Required\n")
    if not results.get("api_football", {}).get("wc2026_league_id"):
        md.append("- ⚠️ API-Football: WC2026 competition not found. "
                  "Check dashboard at api-sports.io — 'International Tournaments' may need enabling. "
                  "Also confirm your plan covers WC2026 season=2026.")
    if not results.get("thestatsapi", {}).get("auth_ok"):
        md.append("- ❌ TheStatsAPI: Auth failed. Verify THESTATSAPI_KEY in .env is correct.")
    if results.get("thestatsapi", {}).get("auth_ok") and not results.get("thestatsapi", {}).get("wc2026_comp_id"):
        md.append("- ⚠️ TheStatsAPI: WC2026 competition not found. "
                  "Your Growth plan may require enabling 'FIFA World Cup 2026' in provider dashboard.")
    if results.get("highlightly", {}).get("auth_ok") and not results.get("highlightly", {}).get("wc_covered"):
        md.append("- ⚠️ Highlightly: Auth OK but WC2026 not confirmed in coverage. "
                  "Check if International Tournaments pack is enabled in your account.")

    md_path = OUT_AUDIT / "provider_battle_test.md"
    md_path.write_text("\n".join(md))
    log(f"Saved: {md_path}")

    # Summary
    log("\n" + "=" * 60)
    log("BATTLE TEST SUMMARY")
    log("=" * 60)
    for key, res in results.items():
        auth = "✅" if res.get("auth_ok") else "❌"
        log(f"  {auth} {key:20s} score={res['score']['total']:5.1f} "
            f"fields={res.get('fields_found', [])}")
    log(f"\n  → PRIMARY: {primary}")
    log(f"  → FALLBACK: {secondary}")
    log(f"\nRaw responses: {OUT_RAW_TS}")


if __name__ == "__main__":
    main()
