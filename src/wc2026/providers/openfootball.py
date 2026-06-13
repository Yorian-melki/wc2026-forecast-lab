"""OpenFootball provider — open source JSON, manually maintained, WC2026 primary fallback."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# name → 3-letter code
NAME_TO_CODE: dict[str, str] = {
    "Mexico": "MEX", "South Africa": "RSA", "South Korea": "KOR",
    "Czech Republic": "CZE", "Canada": "CAN", "Bosnia & Herzegovina": "BIH",
    "Bosnia and Herzegovina": "BIH", "Qatar": "QAT", "Switzerland": "SUI",
    "Brazil": "BRA", "Morocco": "MAR", "Haiti": "HAI", "Scotland": "SCO",
    "USA": "USA", "United States": "USA", "Paraguay": "PAR",
    "Australia": "AUS", "Turkey": "TUR", "Germany": "GER",
    "Curaçao": "CUW", "Ivory Coast": "CIV", "Côte d'Ivoire": "CIV",
    "Ecuador": "ECU", "Netherlands": "NED", "Japan": "JPN",
    "Sweden": "SWE", "Tunisia": "TUN", "Belgium": "BEL",
    "Egypt": "EGY", "Iran": "IRN", "New Zealand": "NZL",
    "Spain": "ESP", "Cape Verde": "CPV", "Saudi Arabia": "KSA",
    "Uruguay": "URU", "France": "FRA", "Senegal": "SEN",
    "Iraq": "IRQ", "Norway": "NOR", "Argentina": "ARG",
    "Algeria": "ALG", "Austria": "AUT", "Jordan": "JOR",
    "Portugal": "POR", "DR Congo": "COD", "Uzbekistan": "UZB",
    "Colombia": "COL", "England": "ENG", "Croatia": "CRO",
    "Ghana": "GHA", "Panama": "PAN",
}


def _to_code(name: str) -> str:
    return NAME_TO_CODE.get(name, name[:3].upper())


class OpenFootballProvider(BaseProvider):
    name = "openfootball"
    quality_level = "C"  # score + date + group only; no stats, no xG, no events

    def __init__(self, local_cache: Optional[Path] = None) -> None:
        self._cache = local_cache
        self._data: Optional[dict] = None
        self._fetched_at: Optional[str] = None

    def _fetch(self) -> dict:
        if self._data is not None:
            return self._data
        try:
            r = requests.get(URL, timeout=12)
            r.raise_for_status()
            self._data = r.json()
            self._fetched_at = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            # Fallback to local cache
            if self._cache and self._cache.exists():
                self._data = json.loads(self._cache.read_text())
                self._fetched_at = "local_cache"
            else:
                self._data = {}
        return self._data

    def get_status(self) -> ProviderStatus:
        try:
            data = self._fetch()
            return ProviderStatus(
                name=self.name,
                available=bool(data),
                plan="open_source",
                wc2026_accessible=bool(data.get("matches")),
                quality_level=self.quality_level,
            )
        except Exception as e:
            return ProviderStatus(name=self.name, available=False, error=str(e))

    def _all_matches(self) -> list[dict]:
        data = self._fetch()
        return data.get("matches", [])

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        out = []
        for m in self._all_matches():
            score = m.get("score", {})
            ft = score.get("ft") if score else None
            if ft is None:
                continue
            date = m.get("date", "")
            if since_date and date < since_date:
                continue
            home_code = _to_code(m.get("team1", ""))
            away_code = _to_code(m.get("team2", ""))
            group = m.get("group", "").replace("Group ", "")
            goals1 = [g.get("name", "") + " " + str(g.get("minute", "")) for g in (m.get("goals1") or [])]
            goals2 = [g.get("name", "") + " " + str(g.get("minute", "")) for g in (m.get("goals2") or [])]
            out.append({
                "provider": self.name,
                "home": home_code,
                "away": away_code,
                "home_goals": ft[0],
                "away_goals": ft[1],
                "ht_home": (score.get("ht") or [None, None])[0],
                "ht_away": (score.get("ht") or [None, None])[1],
                "date": date,
                "group": group,
                "round": m.get("round", ""),
                "venue": m.get("ground", ""),
                "scorers_home": goals1,
                "scorers_away": goals2,
                "status": "FT",
                "quality_level": self.quality_level,
                "source_timestamp": self._fetched_at,
            })
        return out

    def get_live_matches(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        live = []
        for m in self._all_matches():
            score = m.get("score")
            date = m.get("date", "")
            if date == today and score is None:
                # Scheduled today — could be live (we can't tell without live source)
                home_code = _to_code(m.get("team1", ""))
                away_code = _to_code(m.get("team2", ""))
                live.append({
                    "provider": self.name,
                    "home": home_code,
                    "away": away_code,
                    "home_goals": None,
                    "away_goals": None,
                    "date": date,
                    "group": m.get("group", "").replace("Group ", ""),
                    "status": "SCHEDULED_TODAY",
                    "minute": None,
                    "quality_level": "D",
                    "note": "OpenFootball cannot report in-play status — no live endpoint",
                })
        return live

    def get_today_fixtures(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        out = []
        for m in self._all_matches():
            if m.get("date", "") == today:
                score = m.get("score", {})
                ft = score.get("ft") if score else None
                home_code = _to_code(m.get("team1", ""))
                away_code = _to_code(m.get("team2", ""))
                out.append({
                    "provider": self.name,
                    "home": home_code,
                    "away": away_code,
                    "home_goals": ft[0] if ft else None,
                    "away_goals": ft[1] if ft else None,
                    "date": today,
                    "group": m.get("group", "").replace("Group ", ""),
                    "status": "FT" if ft else "SCHEDULED",
                    "quality_level": self.quality_level,
                })
        return out

    def get_standings(self) -> list[dict]:
        """Compute group standings from completed match data."""
        completed = self.get_completed_matches()
        table: dict[str, dict] = {}
        for m in completed:
            grp = m["group"]
            for team, gf, ga in [
                (m["home"], m["home_goals"], m["away_goals"]),
                (m["away"], m["away_goals"], m["home_goals"]),
            ]:
                if team not in table:
                    table[team] = {"team": team, "group": grp, "played": 0, "won": 0,
                                   "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0}
                r = table[team]
                r["played"] += 1
                r["gf"] += gf or 0
                r["ga"] += ga or 0
                r["gd"] = r["gf"] - r["ga"]
                if (gf or 0) > (ga or 0):
                    r["won"] += 1; r["points"] += 3
                elif (gf or 0) == (ga or 0):
                    r["drawn"] += 1; r["points"] += 1
                else:
                    r["lost"] += 1
        return list(table.values())

    def get_full_schedule(self) -> list[dict]:
        """Return ALL matches (completed + scheduled)."""
        out = []
        for m in self._all_matches():
            score = m.get("score", {})
            ft = score.get("ft") if score else None
            home_code = _to_code(m.get("team1", ""))
            away_code = _to_code(m.get("team2", ""))
            out.append({
                "provider": self.name,
                "home": home_code,
                "away": away_code,
                "home_goals": ft[0] if ft else None,
                "away_goals": ft[1] if ft else None,
                "date": m.get("date", ""),
                "time": m.get("time", ""),
                "group": m.get("group", "").replace("Group ", ""),
                "round": m.get("round", ""),
                "venue": m.get("ground", ""),
                "status": "FT" if ft else "SCHEDULED",
                "quality_level": self.quality_level,
            })
        return out
