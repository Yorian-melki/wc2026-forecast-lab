"""Provider router — selects best available source for each data need."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .base import ProviderStatus
from .normalizer import NormalizedMatch, NormalizedStandings, from_provider_dict
from .openfootball import OpenFootballProvider
from .api_football import ApiFootballProvider
from .thestatsapi import TheStatsAPIProvider
from .highlightly import HighlightlyProvider
from .thesportsdb import TheSportsDBProvider

ROOT = Path(__file__).resolve().parents[4]
LIVE_DIR = ROOT / "data" / "live"
LOCAL_LIVE = ROOT / "data" / "wc2026_live.json"


class ProviderRouter:
    """
    Priority order (best available wins):
    1. ApiFootball  — best if paid plan
    2. OpenFootball — reliable open-source JSON (real data, ~1h lag on updates)
    3. Local manual — always available, manually maintained, can be 0-lag if kept fresh

    TheStatsAPI:  key revoked — disabled
    Highlightly:  not a data API — disabled
    TheSportsDB:  free key, WC2026 null — metadata only
    """

    def __init__(self) -> None:
        self._of  = OpenFootballProvider(local_cache=LOCAL_LIVE)
        self._af  = ApiFootballProvider()
        self._tsdb = TheSportsDBProvider()
        self._statuses: dict[str, ProviderStatus] = {}
        LIVE_DIR.mkdir(parents=True, exist_ok=True)

    def check_all_providers(self) -> dict[str, ProviderStatus]:
        self._statuses = {
            "api_football":  self._af.get_status(),
            "openfootball":  self._of.get_status(),
            "thestatsapi":   TheStatsAPIProvider().get_status(),
            "highlightly":   HighlightlyProvider().get_status(),
            "thesportsdb":   self._tsdb.get_status(),
        }
        return self._statuses

    def get_completed_matches(self) -> list[NormalizedMatch]:
        """Best source for completed match results.
        Priority: API-Football (quality B, date-bypass) > OpenFootball (quality C) > local manual.
        """
        try:
            af_matches = self._af.get_completed_matches(days_back=4)
            if af_matches:
                # Merge with OpenFootball to catch matches older than AF 3-day window
                of_matches = self._of.get_completed_matches()
                of_keys = {(m.get("home", ""), m.get("away", "")) for m in of_matches}
                af_keys  = {(m["home"], m["away"]) for m in af_matches}
                of_only  = [m for m in of_matches if (m.get("home",""), m.get("away","")) not in af_keys]
                all_matches = af_matches + of_only
                return [from_provider_dict(m) for m in all_matches]
        except Exception:
            pass
        # Fallback: OpenFootball
        of_matches = self._of.get_completed_matches()
        if of_matches:
            return [from_provider_dict(m) for m in of_matches]
        return self._local_completed()

    def get_live_matches(self) -> list[NormalizedMatch]:
        """In-play WC2026 matches via API-Football live=all (works on Free plan)."""
        try:
            live = self._af.get_live_matches()
            if live:
                return [from_provider_dict(m) for m in live]
        except Exception:
            pass
        return []

    def get_today_fixtures(self) -> list[NormalizedMatch]:
        """All WC2026 matches today: completed + live + scheduled.
        API-Football date-bypass is primary; OpenFootball fills schedule gaps.
        """
        try:
            af_today = self._af.get_today_fixtures()
            if af_today:
                return [from_provider_dict(m) for m in af_today]
        except Exception:
            pass
        # Fallback: OpenFootball schedule
        of_today = self._of.get_today_fixtures()
        return [from_provider_dict(m) for m in of_today]

    def get_standings(self) -> list[NormalizedStandings]:
        """Group standings computed from best completed match source."""
        raw = self._of.get_standings()
        return [NormalizedStandings(
            team=r["team"], group=r["group"], played=r["played"],
            won=r["won"], drawn=r["drawn"], lost=r["lost"],
            gf=r["gf"], ga=r["ga"], gd=r["gd"], points=r["points"],
            provider=r.get("provider", "openfootball"),
        ) for r in raw]

    def get_full_schedule(self) -> list[dict]:
        return self._of.get_full_schedule()

    def get_source_freshness(self) -> dict:
        """Return metadata about each provider's data freshness."""
        return {
            "openfootball": {
                "available": True,
                "wc2026_accessible": True,
                "quality_level": "C",
                "lag_note": "Manually maintained; typically updated within 1–12h of match completion.",
                "fields": ["score", "ht_score", "scorers", "date", "venue", "group"],
                "missing": ["live_status", "minute", "stats", "xG", "lineups", "cards", "odds"],
                "role": "Fallback for matches older than API-Football 3-day window.",
            },
            "api_football": {
                "available": True,
                "wc2026_accessible": True,
                "quality_level": "B",
                "plan": "Free (100 req/day)",
                "lag_note": "Real-time. WC2026 accessible via date-bypass (fixtures?date=YYYY-MM-DD). "
                            "Free plan blocks season=2026 endpoint but date endpoint works.",
                "fields": ["score", "minute", "events", "scorers", "cards", "shots", "possession",
                           "corners", "fouls", "lineups", "formations", "coach", "player_stats"],
                "missing": ["xG", "odds", "injuries", "standings (blocked on Free)"],
                "bypass_method": "GET /fixtures?date=YYYY-MM-DD (no league/season params) returns WC2026",
                "role": "Primary provider for completed results, live score, events, lineups.",
            },
            "thestatsapi": {
                "available": False,
                "wc2026_accessible": False,
                "quality_level": "D",
                "lag_note": "KEY_REVOKED — API key has no active subscription plan (403).",
                "action_needed": "Refresh API key at thestatsapi.com dashboard. comp_6107 = FIFA WC.",
                "potential_fields": ["xG", "shotmap", "player_stats", "odds/live", "lineups", "timeline"],
            },
            "highlightly": {
                "available": False,
                "wc2026_accessible": False,
                "quality_level": "D",
                "lag_note": "Not a data API — video highlights web app only.",
            },
            "thesportsdb": {
                "available": True,
                "wc2026_accessible": False,
                "quality_level": "D",
                "lag_note": "WC2026 returns null on free key (123). Metadata/badges only.",
                "action_needed": "Upgrade TheSportsDB plan to access WC2026 fixtures and live scores.",
            },
            "local_manual": {
                "available": True,
                "wc2026_accessible": True,
                "quality_level": "C",
                "lag_note": "Maintained manually. Update via scripts/update_live_data.py.",
                "fields": ["score", "scorers", "notes", "injuries", "standings"],
                "missing": ["live_status", "minute", "stats", "xG", "lineups"],
                "role": "Emergency fallback. Covers matches before AF 3-day window.",
            },
        }

    def write_live_outputs(self) -> dict[str, Path]:
        """Write normalized live data to data/live/ directory. Returns written paths."""
        ts = datetime.now(timezone.utc).isoformat()

        # provider_status.json
        freshness = self.get_source_freshness()
        status_path = LIVE_DIR / "provider_status.json"
        status_path.write_text(json.dumps({
            "generated_at": ts,
            "overall_quality": "B",
            "note": (
                "API-Football (Free plan) is primary source via date-bypass. "
                "Provides real-time events, stats, lineups. "
                "xG not available from any free provider. "
                "OpenFootball is fallback for matches >3 days old."
            ),
            "providers": freshness,
        }, indent=2))

        # current_matches.json — all today's matches
        today_matches = self.get_today_fixtures()
        current_path = LIVE_DIR / "current_matches.json"
        current_path.write_text(json.dumps({
            "generated_at": ts,
            "quality_level": "C",
            "matches": [vars(m) for m in today_matches],
        }, indent=2))

        # standings_normalized.json
        standings = self.get_standings()
        standings_path = LIVE_DIR / "standings_normalized.json"
        standings_path.write_text(json.dumps({
            "generated_at": ts,
            "standings": [vars(s) for s in standings],
        }, indent=2))

        # full_schedule.json
        schedule = self.get_full_schedule()
        schedule_path = LIVE_DIR / "full_schedule.json"
        schedule_path.write_text(json.dumps({
            "generated_at": ts,
            "total_matches": len(schedule),
            "completed": sum(1 for m in schedule if m["status"] == "FT"),
            "scheduled": sum(1 for m in schedule if m["status"] == "SCHEDULED"),
            "matches": schedule,
        }, indent=2))

        # source_freshness.json
        fresh_path = LIVE_DIR / "source_freshness.json"
        fresh_path.write_text(json.dumps({
            "generated_at": ts,
            "primary_source": "openfootball",
            "quality_level": "C",
            "providers": freshness,
        }, indent=2))

        return {
            "provider_status": status_path,
            "current_matches": current_path,
            "standings_normalized": standings_path,
            "full_schedule": schedule_path,
            "source_freshness": fresh_path,
        }

    def _local_completed(self) -> list[NormalizedMatch]:
        """Read local manual JSON as fallback."""
        if not LOCAL_LIVE.exists():
            return []
        data = json.loads(LOCAL_LIVE.read_text())
        out = []
        for m in data.get("completed_matches", []):
            out.append(NormalizedMatch(
                provider="local_manual",
                home=m.get("home", ""),
                away=m.get("away", ""),
                home_goals=m.get("home_goals"),
                away_goals=m.get("away_goals"),
                date=m.get("date", ""),
                group=m.get("group", ""),
                status="FT",
                notes=m.get("notes", ""),
                scorers_home=m.get("scorers", []),
                quality_level="C",
            ))
        return out
