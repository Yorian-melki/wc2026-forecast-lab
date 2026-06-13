"""football-data.org provider.

Auth: X-Auth-Token: {FOOTBALL_DATA_ORG_KEY}
Base: https://api.football-data.org/v4
Docs: https://docs.football-data.org/

Free tier: ~10 competitions available, ~10 req/min.
WC2026 competition code: 'WC' (code=WC, id=2000).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

_BASE = "https://api.football-data.org/v4"
_WC_CODE = "WC"
_WC_ID = 2000


class FootballDataOrgProvider(BaseProvider):
    name = "football_data_org"
    quality_level = "B"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._key = api_key or os.getenv("FOOTBALL_DATA_ORG_KEY", "")
        self._headers = {"X-Auth-Token": self._key}
        self._base = _BASE

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self._base}/{endpoint.lstrip('/')}"
        r = requests.get(url, headers=self._headers, params=params or {}, timeout=12)
        if r.status_code == 200:
            return r.json()
        return {
            "_status_code": r.status_code,
            "_url": url,
            "error": r.text[:400],
        }

    def get_status(self) -> ProviderStatus:
        r = self._get("competitions/WC")
        if "_status_code" in r:
            sc = r["_status_code"]
            return ProviderStatus(
                name=self.name, available=False,
                error=f"HTTP {sc}: {r.get('error','')[:100]}",
            )
        comp = r.get("name", "")
        return ProviderStatus(
            name=self.name, available=True,
            wc2026_accessible="World Cup" in comp or bool(comp),
            quality_level=self.quality_level,
            error="",
        )

    def get_competition(self, code: str = _WC_CODE) -> dict:
        return self._get(f"competitions/{code}")

    def get_standings(self) -> list[dict]:
        r = self._get(f"competitions/{_WC_CODE}/standings")
        if "_status_code" in r:
            return []
        out = []
        for group in r.get("standings", []):
            stage = group.get("stage", "")
            for team in group.get("table", []):
                out.append({
                    "provider": self.name,
                    "team": team.get("team", {}).get("shortName", ""),
                    "team_name_full": team.get("team", {}).get("name", ""),
                    "group": stage,
                    "played": team.get("playedGames", 0),
                    "won": team.get("won", 0),
                    "drawn": team.get("draw", 0),
                    "lost": team.get("lost", 0),
                    "gf": team.get("goalsFor", 0),
                    "ga": team.get("goalsAgainst", 0),
                    "gd": team.get("goalDifference", 0),
                    "points": team.get("points", 0),
                })
        return out

    def get_matches(self, season: Optional[int] = None, stage: Optional[str] = None) -> dict:
        params = {}
        if season:
            params["season"] = season
        if stage:
            params["stage"] = stage
        return self._get(f"competitions/{_WC_CODE}/matches", params)

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        r = self.get_matches()
        if "_status_code" in r:
            return []
        matches = r.get("matches", [])
        out = []
        for m in matches:
            if m.get("status") != "FINISHED":
                continue
            home = m.get("homeTeam", {})
            away = m.get("awayTeam", {})
            score = m.get("score", {}).get("fullTime", {})
            date_str = m.get("utcDate", "")[:10]
            if since_date and date_str < since_date:
                continue
            out.append({
                "provider": self.name,
                "match_id": str(m.get("id")),
                "home": home.get("tla") or home.get("shortName", ""),
                "away": away.get("tla") or away.get("shortName", ""),
                "home_goals": score.get("home"),
                "away_goals": score.get("away"),
                "date": date_str,
                "status": "FT",
                "group": m.get("group", ""),
                "stage": m.get("stage", ""),
                "quality_level": self.quality_level,
                "source_timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return out

    def get_live_matches(self) -> list[dict]:
        r = self._get(f"competitions/{_WC_CODE}/matches", {"status": "IN_PLAY,PAUSED"})
        if "_status_code" in r:
            return []
        return []

    def get_today_fixtures(self) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        r = self._get(f"competitions/{_WC_CODE}/matches", {"dateFrom": today, "dateTo": today})
        if "_status_code" in r:
            return []
        matches = r.get("matches", [])
        return [self._normalize(m) for m in matches]

    def get_teams(self) -> dict:
        return self._get(f"competitions/{_WC_CODE}/teams")

    def get_scorers(self, limit: int = 20) -> dict:
        return self._get(f"competitions/{_WC_CODE}/scorers", {"limit": limit})

    def get_match_detail(self, match_id: int) -> dict:
        return self._get(f"matches/{match_id}")

    def get_past_wc_matches(self, year: int) -> dict:
        """Get historical WC matches for a given year."""
        return self._get(f"competitions/{_WC_CODE}/matches", {"season": year})

    def _normalize(self, m: dict) -> dict:
        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        score = m.get("score", {}).get("fullTime", {})
        return {
            "provider": self.name,
            "match_id": str(m.get("id")),
            "home": home.get("tla") or home.get("shortName", ""),
            "away": away.get("tla") or away.get("shortName", ""),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
            "date": m.get("utcDate", "")[:10],
            "status": m.get("status", ""),
            "group": m.get("group", ""),
            "quality_level": self.quality_level,
            "source_timestamp": datetime.now(timezone.utc).isoformat(),
        }
