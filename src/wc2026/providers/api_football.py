"""API-Football (api-sports.io) provider.

FREE PLAN — WC2026 ACCESS VIA DATE-BYPASS:
  - fixtures?season=2026&league=1  → BLOCKED ("Free plans do not have access to this season")
  - fixtures?date=YYYY-MM-DD       → WORKS (no league/season params, returns WC2026 fixtures)
  - fixtures?live=all              → WORKS (filter response by league.id == 1)
  - fixtures/events?fixture=ID     → WORKS for any WC2026 fixture ID
  - fixtures/statistics?fixture=ID → WORKS for any WC2026 fixture ID
  - fixtures/lineups?fixture=ID    → WORKS for any WC2026 fixture ID
  - fixtures/players?fixture=ID    → WORKS for any WC2026 fixture ID

Limitations on Free plan (100 req/day):
  - standings?league=1&season=2026 → BLOCKED
  - odds?league=1&season=2026      → BLOCKED
  - injuries?league=1&season=2026  → BLOCKED
  - fixtures?date before 3-day window → MAY be BLOCKED for some dates
  - xG not available on any plan (not in API-Football)
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

WC_LEAGUE_ID = 1  # FIFA World Cup

# Full name → 3-letter code mapping for API-Football team names
_AF_NAME_TO_CODE: dict[str, str] = {
    "South Korea": "KOR",
    "Korea Republic": "KOR",
    "Czechia": "CZE",
    "Czech Republic": "CZE",
    "Bosnia & Herzegovina": "BIH",
    "Bosnia and Herzegovina": "BIH",
    "USA": "USA",
    "United States": "USA",
    "Paraguay": "PAR",
    "Qatar": "QAT",
    "Switzerland": "SUI",
    "Brazil": "BRA",
    "Morocco": "MAR",
    "Australia": "AUS",
    "Türkiye": "TUR",
    "Turkey": "TUR",
    "Haiti": "HAI",
    "Scotland": "SCO",
    "Germany": "GER",
    "Curaçao": "CUW",
    "Curacao": "CUW",
    "Netherlands": "NED",
    "Japan": "JPN",
    "Ivory Coast": "CIV",
    "Côte d'Ivoire": "CIV",
    "Ecuador": "ECU",
    "Mexico": "MEX",
    "South Africa": "RSA",
    "Canada": "CAN",
    "Spain": "ESP",
    "Argentina": "ARG",
    "France": "FRA",
    "Portugal": "POR",
    "Belgium": "BEL",
    "England": "ENG",
    "Croatia": "CRO",
    "Uruguay": "URU",
    "Colombia": "COL",
    "Chile": "CHI",
    "Peru": "PER",
    "Serbia": "SRB",
    "Austria": "AUT",
    "Ukraine": "UKR",
    "Denmark": "DEN",
    "Sweden": "SWE",
    "Norway": "NOR",
    "Poland": "POL",
    "Hungary": "HUN",
    "Romania": "ROU",
    "Slovakia": "SVK",
    "Slovenia": "SVN",
    "Greece": "GRE",
    "Albania": "ALB",
    "Georgia": "GEO",
    "Venezuela": "VEN",
    "Ecuador": "ECU",
    "Bolivia": "BOL",
    "Honduras": "HON",
    "Costa Rica": "CRC",
    "Panama": "PAN",
    "Jamaica": "JAM",
    "Trinidad & Tobago": "TRI",
    "El Salvador": "SLV",
    "Guatemala": "GUA",
    "Cuba": "CUB",
    "Senegal": "SEN",
    "Cameroon": "CMR",
    "Tunisia": "TUN",
    "Algeria": "ALG",
    "Nigeria": "NGA",
    "Ghana": "GHA",
    "Mali": "MLI",
    "Guinea": "GUI",
    "Egypt": "EGY",
    "DR Congo": "COD",
    "Zambia": "ZAM",
    "Mozambique": "MOZ",
    "Tanzania": "TAN",
    "Burkina Faso": "BFA",
    "Iran": "IRN",
    "Iraq": "IRQ",
    "Saudi Arabia": "KSA",
    "South Korea": "KOR",
    "China": "CHN",
    "Uzbekistan": "UZB",
    "New Zealand": "NZL",
    "New Caledonia": "NCL",
    "Vanuatu": "VAN",
}


def _name_to_code(name: str) -> str:
    """Convert API-Football full name to 3-letter code. Returns uppercased name if unknown."""
    return _AF_NAME_TO_CODE.get(name, name[:3].upper())


class ApiFootballProvider(BaseProvider):
    name = "api_football"
    quality_level = "B"  # shots/SOT/corners/cards/events/lineups — no xG

    def __init__(self, api_key: Optional[str] = None, host: str = "v3.football.api-sports.io") -> None:
        self._key = api_key or os.getenv("API_FOOTBALL_KEY", "")
        self._host = host
        self._base = f"https://{host}"
        self._headers = {"x-apisports-key": self._key}
        self._plan: Optional[str] = None
        self._requests_used: Optional[int] = None
        self._requests_limit: Optional[int] = None

    def _get(self, endpoint: str, params: dict = None) -> dict:
        r = requests.get(
            f"{self._base}/{endpoint}",
            headers=self._headers,
            params=params or {},
            timeout=12,
        )
        return r.json() if r.status_code == 200 else {"errors": {r.status_code: r.text[:200]}}

    def get_status(self) -> ProviderStatus:
        data = self._get("status")
        if "errors" in data and data["errors"]:
            return ProviderStatus(name=self.name, available=False, error=str(data["errors"]))
        resp = data.get("response", {})
        sub  = resp.get("subscription", {})
        reqs = resp.get("requests", {})
        self._plan = sub.get("plan", "unknown")
        self._requests_used = reqs.get("current")
        self._requests_limit = reqs.get("limit_day")
        # WC2026 accessible via date-bypass on ALL plans including Free
        note = (
            "Date-bypass active: fixtures?date=YYYY-MM-DD returns WC2026 without season param. "
            "All fixture detail endpoints work. standings/odds/injuries blocked on Free plan. "
            f"Usage: {self._requests_used}/{self._requests_limit} req/day."
        )
        return ProviderStatus(
            name=self.name,
            available=True,
            plan=self._plan,
            requests_used=self._requests_used,
            requests_limit=self._requests_limit,
            wc2026_accessible=True,
            quality_level=self.quality_level,
            error=note,
        )

    def get_wc_fixtures_by_date(self, date_str: str) -> list[dict]:
        """Return WC2026 fixtures for a specific date using the date-bypass (no season param)."""
        data = self._get("fixtures", {"date": date_str})
        return [
            f for f in data.get("response", [])
            if f.get("league", {}).get("id") == WC_LEAGUE_ID
        ]

    def get_live_matches(self) -> list[dict]:
        """Get currently live WC2026 matches (free plan: filter by league.id from live=all)."""
        data = self._get("fixtures", {"live": "all"})
        fixtures = [
            f for f in data.get("response", [])
            if f.get("league", {}).get("id") == WC_LEAGUE_ID
        ]
        return [self._normalize(f) for f in fixtures]

    def get_today_fixtures(self) -> list[dict]:
        """Get all WC2026 matches today using date-bypass."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fixtures = self.get_wc_fixtures_by_date(today)
        return [self._normalize(f) for f in fixtures]

    def get_completed_matches(self, since_date: Optional[str] = None, days_back: int = 4) -> list[dict]:
        """
        Get completed WC2026 matches over the last N days using date-bypass.
        Free plan: 100 req/day limit — one request per day checked.
        """
        out = []
        today = datetime.now(timezone.utc).date()
        for delta in range(days_back):
            dt = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
            if since_date and dt < since_date:
                break
            fixtures = self.get_wc_fixtures_by_date(dt)
            for f in fixtures:
                status = f.get("fixture", {}).get("status", {}).get("short", "")
                if status == "FT":
                    norm = self._normalize(f)
                    if not since_date or norm.get("date", "") >= since_date:
                        out.append(norm)
        return out

    def get_standings(self) -> list[dict]:
        """Standings endpoint is blocked on Free plan. Returns empty list."""
        return []

    def get_fixture_events(self, fixture_id: int) -> list[dict]:
        """Goals, cards, substitutions for a fixture. Works on Free plan."""
        data = self._get("fixtures/events", {"fixture": fixture_id})
        return [
            {
                "minute": e.get("time", {}).get("elapsed"),
                "extra_time": e.get("time", {}).get("extra"),
                "type": e.get("type"),
                "detail": e.get("detail"),
                "team": _name_to_code(e.get("team", {}).get("name", "")),
                "team_name": e.get("team", {}).get("name", ""),
                "player": e.get("player", {}).get("name"),
                "assist": e.get("assist", {}).get("name"),
                "provider": self.name,
            }
            for e in data.get("response", [])
        ]

    def get_fixture_stats(self, fixture_id: int) -> dict:
        """Match statistics (shots, possession, corners, fouls). Works on Free plan. No xG."""
        data = self._get("fixtures/statistics", {"fixture": fixture_id})
        out: dict[str, dict] = {}
        for team_data in data.get("response", []):
            code = _name_to_code(team_data.get("team", {}).get("name", ""))
            stats = {}
            for s in team_data.get("statistics", []):
                key = s.get("type", "").lower().replace(" ", "_")
                stats[key] = s.get("value")
            out[code] = stats
        return out

    def get_fixture_lineups(self, fixture_id: int) -> dict:
        """Starting XI + subs + formation + coach. Works on Free plan."""
        data = self._get("fixtures/lineups", {"fixture": fixture_id})
        out: dict[str, dict] = {}
        for team_data in data.get("response", []):
            code = _name_to_code(team_data.get("team", {}).get("name", ""))
            out[code] = {
                "formation": team_data.get("formation", ""),
                "coach": team_data.get("coach", {}).get("name", ""),
                "startXI": [p["player"]["name"] for p in team_data.get("startXI", [])],
                "substitutes": [p["player"]["name"] for p in team_data.get("substitutes", [])],
            }
        return out

    def get_fixture_players(self, fixture_id: int) -> dict:
        """Per-player stats (minutes, shots, passes, rating). Works on Free plan."""
        data = self._get("fixtures/players", {"fixture": fixture_id})
        out: dict[str, list] = {}
        for team_data in data.get("response", []):
            code = _name_to_code(team_data.get("team", {}).get("name", ""))
            players = []
            for p in team_data.get("players", []):
                pl = p.get("player", {})
                st = (p.get("statistics") or [{}])[0]
                players.append({
                    "name": pl.get("name"),
                    "number": pl.get("number"),
                    "minutes": st.get("games", {}).get("minutes"),
                    "rating": st.get("games", {}).get("rating"),
                    "shots_total": st.get("shots", {}).get("total"),
                    "goals": st.get("goals", {}).get("total"),
                    "assists": st.get("goals", {}).get("assists"),
                    "passes": st.get("passes", {}).get("total"),
                    "pass_accuracy": st.get("passes", {}).get("accuracy"),
                })
            out[code] = players
        return out

    def _normalize(self, f: dict) -> dict:
        fixture = f.get("fixture", {})
        teams   = f.get("teams", {})
        goals   = f.get("goals", {})
        status  = fixture.get("status", {})
        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        return {
            "provider": self.name,
            "match_id": fixture.get("id"),
            "home": _name_to_code(home_name),
            "away": _name_to_code(away_name),
            "home_name_full": home_name,
            "away_name_full": away_name,
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "date": fixture.get("date", "")[:10],
            "status": status.get("short", ""),
            "minute": status.get("elapsed"),
            "venue": fixture.get("venue", {}).get("name", ""),
            "quality_level": self.quality_level,
            "source_timestamp": datetime.now(timezone.utc).isoformat(),
        }
