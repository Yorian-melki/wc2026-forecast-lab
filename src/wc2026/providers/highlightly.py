"""Highlightly provider — soccer.highlightly.net.

Auth: x-rapidapi-key: {HIGHLIGHTLY_API_KEY}
      x-rapidapi-host: soccer.highlightly.net
Base: https://soccer.highlightly.net
Docs: RapidAPI OpenAPI spec (saved at data/raw/provider_docs/highlightly_openapi.json)

Plan: BASIC — xG confirmed working (Expected Goals via /statistics/{matchId})
WC2026: league_id=1635, name="World Cup"

Quality A: xG (Expected Goals), Big Chances Created, Expected Assists, Key Passes,
           Passes Into Final Third, Tackles, Clearances, Aerial Duels, Dribbles,
           Venue (name/city/capacity), Referee (name/nationality), Weather forecast,
           Full match events (goals/cards/subs), Lineups, Box scores.

Key discovery: match state uses state.description / state.score.current / state.clock
               NOT top-level status/homeScore fields.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

_BASE = "https://soccer.highlightly.net"
_WC_LEAGUE_ID = 1635
_WC_LEAGUE_NAME = "World Cup"


class HighlightlyProvider(BaseProvider):
    name = "highlightly"
    quality_level = "A"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._key = api_key or os.getenv("HIGHLIGHTLY_API_KEY", "")
        self._headers = {
            "x-rapidapi-key": self._key,
            "x-rapidapi-host": "soccer.highlightly.net",
        }

    def _get(self, path: str, params: dict = None) -> dict | list:
        r = requests.get(
            f"{_BASE}/{path.lstrip('/')}",
            headers=self._headers,
            params=params or {},
            timeout=12,
        )
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return {"_raw": r.text[:400]}
        return {"_status_code": r.status_code, "error": r.text[:200]}

    # ── Status ──────────────────────────────────────────────────────────────

    def get_status(self) -> ProviderStatus:
        r = self._get("countries")
        if isinstance(r, dict) and "_status_code" in r:
            sc = r["_status_code"]
            return ProviderStatus(
                name=self.name, available=False,
                quality_level="D",
                error=f"HTTP {sc}: {r.get('error','')[:120]}",
            )
        n_countries = len(r) if isinstance(r, list) else 0
        # Confirm WC league accessible
        wc = self._get("leagues", {"name": _WC_LEAGUE_NAME})
        wc_data = wc if isinstance(wc, list) else wc.get("data", [])
        wc_id = None
        for league in wc_data:
            if league.get("id") == _WC_LEAGUE_ID:
                wc_id = _WC_LEAGUE_ID
                break
        return ProviderStatus(
            name=self.name, available=True,
            plan="basic",
            wc2026_accessible=wc_id is not None,
            quality_level=self.quality_level,
            error=f"xG confirmed; {n_countries} countries; WC league_id={wc_id}",
        )

    # ── Matches ──────────────────────────────────────────────────────────────

    def _get_matches_by_date(self, date_str: str) -> list[dict]:
        r = self._get("matches", {"date": date_str, "leagueName": _WC_LEAGUE_NAME})
        if isinstance(r, dict) and "_status_code" in r:
            return []
        data = r.get("data", r) if isinstance(r, dict) else r
        return [m for m in (data if isinstance(data, list) else [])]

    def _parse_state(self, match: dict) -> tuple[str, Optional[int], Optional[int], Optional[int]]:
        """Return (status_desc, home_goals, away_goals, clock_minutes)."""
        state = match.get("state", {})
        desc = state.get("description", "Not started")
        clock = state.get("clock")
        score_str = state.get("score", {}).get("current", "")
        hg, ag = None, None
        if score_str and " - " in score_str:
            try:
                parts = score_str.split(" - ")
                hg, ag = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                pass
        return desc, hg, ag, clock

    def _normalize(self, m: dict) -> dict:
        desc, hg, ag, clock = self._parse_state(m)
        status_map = {
            "finished": "FT",
            "not started": "NS",
            "live": "LIVE",
            "half time": "HT",
        }
        status = status_map.get(desc.lower(), desc)
        return {
            "provider": self.name,
            "match_id": str(m.get("id", "")),
            "home": m.get("homeTeam", {}).get("name", ""),
            "home_id": m.get("homeTeam", {}).get("id"),
            "away": m.get("awayTeam", {}).get("name", ""),
            "away_id": m.get("awayTeam", {}).get("id"),
            "home_goals": hg,
            "away_goals": ag,
            "date": (m.get("date", "") or "")[:10],
            "kickoff_utc": m.get("date", ""),
            "status": status,
            "clock": clock,
            "round": m.get("round", ""),
            "league_id": m.get("league", {}).get("id"),
            "quality_level": self.quality_level,
            "source_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        out = []
        today = datetime.now(timezone.utc).date()
        for delta in range(-7, 1):
            dt = (today + timedelta(days=delta)).strftime("%Y-%m-%d")
            if since_date and dt < since_date:
                continue
            for m in self._get_matches_by_date(dt):
                desc, _, _, _ = self._parse_state(m)
                if "finish" in desc.lower():
                    out.append(self._normalize(m))
        return out

    def get_live_matches(self) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        matches = self._get_matches_by_date(today)
        live = []
        for m in matches:
            desc, _, _, clock = self._parse_state(m)
            if "live" in desc.lower() or (clock is not None and clock < 91):
                live.append(self._normalize(m))
        return live

    def get_today_fixtures(self) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return [self._normalize(m) for m in self._get_matches_by_date(today)]

    def get_standings(self) -> list[dict]:
        r = self._get("standings", {"leagueId": _WC_LEAGUE_ID, "season": 2026})
        data = r if isinstance(r, list) else r.get("data", [])
        if not data or isinstance(r, dict) and "_status_code" in r:
            return []
        out = []
        for entry in data:
            team = entry.get("team", {})
            stats = entry.get("stats", entry)
            out.append({
                "provider": self.name,
                "group": entry.get("group", entry.get("stage", "")),
                "position": entry.get("position"),
                "team": team.get("name", "") or entry.get("name", ""),
                "team_id": team.get("id") or entry.get("teamId"),
                "played": stats.get("played", stats.get("gamesPlayed", 0)),
                "won": stats.get("won", stats.get("wins", 0)),
                "drawn": stats.get("drawn", stats.get("draws", 0)),
                "lost": stats.get("lost", stats.get("losses", 0)),
                "gf": stats.get("goalsFor", stats.get("goals", 0)),
                "ga": stats.get("goalsAgainst", 0),
                "gd": stats.get("goalDifference", 0),
                "points": stats.get("points", 0),
            })
        return out

    # ── Match detail endpoints ────────────────────────────────────────────────

    def get_match_detail(self, match_id: str | int) -> dict:
        r = self._get(f"matches/{match_id}")
        if isinstance(r, list):
            return r[0] if r else {}
        return r if isinstance(r, dict) and "_status_code" not in r else {}

    def get_statistics(self, match_id: str | int) -> list[dict]:
        """Returns per-team stats including xG (Expected Goals), Big Chances, etc."""
        r = self._get(f"statistics/{match_id}")
        if isinstance(r, list):
            return r
        return r.get("data", []) if isinstance(r, dict) else []

    def get_lineups(self, match_id: str | int) -> list | dict:
        r = self._get(f"lineups/{match_id}")
        if isinstance(r, dict) and "_status_code" in r:
            return []
        return r if isinstance(r, list) else r.get("data", r)

    def get_highlights(self, match_id: str | int) -> list[dict]:
        r = self._get("highlights", {"matchId": match_id})
        if isinstance(r, dict) and "_status_code" in r:
            return []
        return r.get("data", r) if isinstance(r, dict) else (r if isinstance(r, list) else [])

    def get_odds(self, match_id: str | int) -> list[dict]:
        r = self._get("odds", {"matchId": match_id})
        if isinstance(r, dict) and "_status_code" in r:
            return []
        return r.get("data", r) if isinstance(r, dict) else (r if isinstance(r, list) else [])

    def get_head_to_head(self, home_team_id: int, away_team_id: int) -> list[dict]:
        r = self._get("head-2-head", {"homeTeamId": home_team_id, "awayTeamId": away_team_id})
        if isinstance(r, dict) and "_status_code" in r:
            return []
        return r.get("data", r) if isinstance(r, dict) else (r if isinstance(r, list) else [])

    def get_last_five_games(self, team_id: int) -> list[dict]:
        r = self._get("last-five-games", {"teamId": team_id})
        if isinstance(r, dict) and "_status_code" in r:
            return []
        return r.get("data", r) if isinstance(r, dict) else (r if isinstance(r, list) else [])

    def get_box_score(self, match_id: str | int) -> dict:
        r = self._get(f"box-score/{match_id}")
        if isinstance(r, dict) and "_status_code" in r:
            return {}
        return r

    # ── xG extraction ────────────────────────────────────────────────────────

    def extract_xg(self, statistics: list[dict]) -> dict:
        """Extract xG and key stats from /statistics response per team."""
        result = {}
        for team_stats in statistics:
            team_name = team_stats.get("team", {}).get("name", "unknown")
            stats_dict = {s["displayName"]: s["value"] for s in team_stats.get("statistics", [])}
            result[team_name] = {
                "xg": stats_dict.get("Expected Goals"),
                "big_chances": stats_dict.get("Big Chances Created"),
                "expected_assists": stats_dict.get("Expected Assists"),
                "attacks": stats_dict.get("Attacks"),
                "shots": stats_dict.get("Shots"),
                "shots_on_target": stats_dict.get("Shots on Target"),
                "key_passes": stats_dict.get("Key Passes"),
                "passes_final_third": stats_dict.get("Passes Into Final Third"),
                "successful_crosses": stats_dict.get("Successful Crosses"),
                "interceptions": stats_dict.get("Interceptions"),
                "tackles": stats_dict.get("Tackles"),
                "clearances": stats_dict.get("Clearances"),
                "aerial_duels": stats_dict.get("Aerial Duels"),
                "successful_dribbles": stats_dict.get("Successful Dribbles"),
                "source": self.name,
            }
        return result

    # ── Full match extraction ────────────────────────────────────────────────

    def get_full_match_data(self, match_id: str | int) -> dict:
        """Extract all available data for a single match (venue, referee, events, xG, lineups)."""
        detail = self.get_match_detail(match_id)
        stats = self.get_statistics(match_id)
        lineups = self.get_lineups(match_id)

        events = detail.get("events", []) if isinstance(detail, dict) else []
        venue = detail.get("venue", {}) if isinstance(detail, dict) else {}
        referee = detail.get("referee", {}) if isinstance(detail, dict) else {}
        forecast = detail.get("forecast", {}) if isinstance(detail, dict) else {}

        return {
            "match_id": str(match_id),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "venue": venue,
            "referee": referee,
            "forecast": forecast,
            "events": events,
            "xg": self.extract_xg(stats),
            "lineups": lineups,
        }
