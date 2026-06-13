#!/usr/bin/env python3
"""
update_live_data.py
Fetches freshest available WC2026 data from provider router and updates:
  - data/live/provider_status.json
  - data/live/current_matches.json
  - data/live/standings_normalized.json
  - data/live/full_schedule.json
  - data/live/source_freshness.json
  - data/wc2026_live.json  (updated from OpenFootball, preserves manual fields)

Run: PYTHONPATH=src python scripts/update_live_data.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from wc2026.providers.router import ProviderRouter
from wc2026.providers.openfootball import OpenFootballProvider, NAME_TO_CODE

LIVE_PATH = ROOT / "data" / "wc2026_live.json"
GROUPS_PATH = ROOT / "data" / "groups.json"


def build_group_standings(completed: list) -> dict[str, list[dict]]:
    """Compute group tables from completed matches."""
    table: dict[str, dict] = {}
    for m in completed:
        grp = getattr(m, "group", "") or ""
        if not grp:
            continue
        for team, gf, ga in [
            (m.home, m.home_goals or 0, m.away_goals or 0),
            (m.away, m.away_goals or 0, m.home_goals or 0),
        ]:
            if team not in table:
                table[team] = {"team": team, "group": grp, "played": 0, "won": 0,
                               "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0}
            r = table[team]
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
            r["gd"] = r["gf"] - r["ga"]
            if gf > ga:
                r["won"] += 1; r["points"] += 3
            elif gf == ga:
                r["drawn"] += 1; r["points"] += 1
            else:
                r["lost"] += 1

    # Group by group letter
    groups_out: dict[str, list[dict]] = {}
    for team, row in table.items():
        grp = row["group"]
        groups_out.setdefault(grp, []).append(row)

    # Fill missing teams from groups.json
    if GROUPS_PATH.exists():
        groups_ref = json.loads(GROUPS_PATH.read_text())
        for grp, team_codes in groups_ref.items():
            groups_out.setdefault(grp, [])
            existing = {r["team"] for r in groups_out[grp]}
            for code in team_codes:
                if code not in existing:
                    groups_out[grp].append({"team": code, "group": grp, "played": 0,
                                             "won": 0, "drawn": 0, "lost": 0,
                                             "gf": 0, "ga": 0, "gd": 0, "points": 0})

    # Sort each group
    for grp in groups_out:
        groups_out[grp].sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"]))

    return groups_out


def update_wc2026_live_json(router: ProviderRouter, completed: list) -> None:
    """Merge provider data into data/wc2026_live.json, preserving manual fields."""
    # Load existing
    existing = {}
    if LIVE_PATH.exists():
        existing = json.loads(LIVE_PATH.read_text())

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build completed_matches list
    completed_list = []
    for m in completed:
        entry = {
            "date": m.date,
            "group": m.group,
            "matchday": 1,
            "home": m.home,
            "away": m.away,
            "home_goals": m.home_goals,
            "away_goals": m.away_goals,
            "decided_in": "90",
            "scorers": m.scorers_home + m.scorers_away,
            "notes": m.notes,
            "source": m.provider,
        }
        completed_list.append(entry)

    # Group standings
    standings = build_group_standings(completed)

    # Today's upcoming (from full schedule)
    today = datetime.now().strftime("%Y-%m-%d")
    schedule = router.get_full_schedule()
    upcoming = [
        {"group": m["group"], "home": m["home"], "away": m["away"],
         "time_utc": m.get("time", "TBD"), "status": m["status"]}
        for m in schedule
        if m["date"] == today and m["status"] != "FT"
    ]

    # Preserve manual fields (key_injuries etc.) if not overwritten
    new_json = {
        "tournament": "FIFA World Cup 2026",
        "last_updated": now,
        "source": f"{completed[0].provider if completed else 'local'} + manual",
        "data_quality": "C — score/result data only; no live stats/xG",
        "status": "group_stage",
        "completed_matches": completed_list,
        "group_standings": standings,
        "upcoming_today": upcoming,
        "key_injuries": existing.get("key_injuries", {}),
    }

    LIVE_PATH.write_text(json.dumps(new_json, indent=2))
    print(f"  Updated: {LIVE_PATH} ({len(completed_list)} completed matches)")


def main() -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Updating WC2026 live data...")
    router = ProviderRouter()

    # Fetch completed matches (OpenFootball primary)
    completed = router.get_completed_matches()
    print(f"  Completed matches: {len(completed)}")
    for m in completed:
        print(f"    {m.home} {m.home_goals}–{m.away_goals} {m.away} [{m.date}] source={m.provider}")

    # Today's fixtures
    today_fixt = router.get_today_fixtures()
    print(f"  Today's fixtures: {len(today_fixt)}")
    for m in today_fixt:
        status = m.status
        score = f"{m.home_goals}–{m.away_goals}" if m.home_goals is not None else "vs"
        print(f"    {m.home} {score} {m.away} [{status}] quality={m.quality_level}")

    # Live matches
    live = router.get_live_matches()
    if live:
        print(f"  LIVE NOW: {len(live)} matches")
        for m in live:
            print(f"    🔴 {m.home} {m.home_goals}–{m.away_goals} {m.away} min={m.minute}")
    else:
        print("  No live matches from API providers (OpenFootball has no live endpoint)")

    # Write normalized live outputs
    paths = router.write_live_outputs()
    for key, path in paths.items():
        print(f"  Written: {path.name}")

    # Update wc2026_live.json
    update_wc2026_live_json(router, completed)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done.")
    print()
    print("Data quality summary:")
    print("  Source: OpenFootball (open-source JSON)")
    print("  Quality: C — result/score data only")
    print("  Missing: live minute, in-play stats, xG, lineups, events, odds")
    print()
    print("To unlock real-time stats:")
    print("  1. Upgrade api-sports.io to Starter plan ($10/mo) → WC2026 unlocked")
    print("  2. Refresh TheStatsAPI key at thestatsapi.com")


if __name__ == "__main__":
    main()
