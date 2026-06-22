"""ESPN hidden scoreboard provider — the free, key-less, server-reachable source for the OFFICIAL
live clock.

ESPN's public site API (`site.api.espn.com/.../soccer/fifa.world/scoreboard`) exposes, per match:
the exact official minute via `status.displayClock` (e.g. "70'", "90'+3'" with stoppage time), the
in-play state (1st/2nd half, half-time, extra time, shootout), and the live score — with no API key
and, unlike SofaScore/FotMob, without a Cloudflare block on datacenter IPs. Quality C (score + exact
minute, no xG). Used purely as a live-clock/score source in the router's fallback chain.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from .base import BaseProvider, ProviderStatus

_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.espn.com/",
}

# ESPN status name → our compact status (consumed by app._live_label). Liveness itself is decided
# by ESPN's type.state == "in" (in-progress) — that auto-covers ANY in-play reason (half-time,
# weather delay, suspension, extra time) without us enumerating every status name.
_STATE = {
    "STATUS_FIRST_HALF": "1H", "STATUS_SECOND_HALF": "2H", "STATUS_IN_PROGRESS": "2H",
    "STATUS_HALFTIME": "HT",
    "STATUS_OVERTIME": "ET", "STATUS_FIRST_HALF_EXTRA_TIME": "ET",
    "STATUS_HALFTIME_ET": "ET", "STATUS_SECOND_HALF_EXTRA_TIME": "ET",
    "STATUS_END_OF_EXTRATIME": "ET", "STATUS_END_OF_REGULATION": "ET",
    "STATUS_SHOOTOUT": "P", "STATUS_PENALTIES": "P",
    "STATUS_DELAYED": "SUSP", "STATUS_DELAY": "SUSP", "STATUS_SUSPENDED": "SUSP",
    "STATUS_RAIN_DELAY": "SUSP", "STATUS_ABANDONED": "SUSP",
}


def _int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


class EspnProvider(BaseProvider):
    name = "espn"
    quality_level = "C"

    def _fetch(self) -> dict:
        req = urllib.request.Request(_SCOREBOARD, headers=_UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def _events(self, only_live: bool) -> list[dict]:
        try:
            data = self._fetch()
        except Exception:
            return []
        return self._parse(data, only_live)

    def live_or_none(self):
        """Live matches, or None when ESPN itself is unreachable. Lets the router treat ESPN as the
        AUTHORITY on live state: an empty list means 'nothing is live right now' (e.g. a match just
        hit FULL_TIME), NOT 'fall back to a laggy provider that still reports it as in-play'."""
        try:
            data = self._fetch()
        except Exception:
            return None
        return self._parse(data, only_live=True)

    def _parse(self, data: dict, only_live: bool) -> list[dict]:
        out = []
        for e in data.get("events", []):
            comp = (e.get("competitions") or [{}])[0]
            typ = comp.get("status", {}).get("type", {})
            name, phase = typ.get("name", ""), typ.get("state", "")   # phase: pre | in | post
            if only_live and phase != "in":      # "in" = being played (incl. HT / delay / suspension)
                continue
            cs = comp.get("competitors", [])
            home = next((c for c in cs if c.get("homeAway") == "home"), None)
            away = next((c for c in cs if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            clock = (comp.get("status", {}).get("displayClock") or "").replace("'", "").strip()
            out.append({
                "provider": self.name,
                "match_id": str(e.get("id")),
                "home": (home.get("team", {}).get("abbreviation") or "").upper(),
                "away": (away.get("team", {}).get("abbreviation") or "").upper(),
                "home_goals": _int(home.get("score")),
                "away_goals": _int(away.get("score")),
                "date": (e.get("date", "") or "")[:10],
                "status": _STATE.get(name, "2H"),    # unknown in-progress name → treat as a half (show minute)
                "minute": clock or None,             # "70" or "90+3" (added time) — no trailing quote
                "quality_level": self.quality_level,
                "source_timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return out

    def get_live_matches(self) -> list[dict]:
        return self._events(only_live=True)

    def get_today_fixtures(self) -> list[dict]:
        return self._events(only_live=False)

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        """Today's FINISHED matches (final score). ESPN flips a match to completed the moment it
        ends, so the played list updates immediately instead of waiting on OpenFootball's lag."""
        try:
            data = self._fetch()
        except Exception:
            return []
        out = []
        for e in data.get("events", []):
            comp = (e.get("competitions") or [{}])[0]
            if not comp.get("status", {}).get("type", {}).get("completed"):
                continue
            cs = comp.get("competitors", [])
            home = next((c for c in cs if c.get("homeAway") == "home"), None)
            away = next((c for c in cs if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            hg, ag = _int(home.get("score")), _int(away.get("score"))
            if hg is None or ag is None:
                continue
            out.append({
                "provider": self.name, "match_id": str(e.get("id")),
                "home": (home.get("team", {}).get("abbreviation") or "").upper(),
                "away": (away.get("team", {}).get("abbreviation") or "").upper(),
                "home_goals": hg, "away_goals": ag,
                "date": (e.get("date", "") or "")[:10], "status": "FT",
                "quality_level": self.quality_level,
                "source_timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return out

    def get_standings(self) -> list[dict]:
        return []

    def get_status(self) -> ProviderStatus:
        try:
            self._fetch()
            return ProviderStatus(name=self.name, available=True, wc2026_accessible=True,
                                  plan="free", quality_level=self.quality_level)
        except Exception as e:
            return ProviderStatus(name=self.name, available=False, error=str(e)[:80],
                                  quality_level=self.quality_level)
