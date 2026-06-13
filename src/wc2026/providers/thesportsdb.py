"""TheSportsDB provider.

Status: Free key (123) — demo/metadata only.
        WC2026 fixtures return null on free tier.
        v2 livescores require paid plan.
        Usable for: team badges, logos, player photos.
        NOT usable for: live scores, WC2026 fixtures, stats.
"""
from __future__ import annotations

import os
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

FREE_KEY = "123"


class TheSportsDBProvider(BaseProvider):
    name = "thesportsdb"
    quality_level = "D"  # metadata only on free key

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._key = api_key or os.getenv("THESPORTSDB_API_KEY", FREE_KEY)
        self._base = f"https://www.thesportsdb.com/api/v1/json/{self._key}"

    def _get(self, endpoint: str, params: dict = None) -> dict:
        try:
            r = requests.get(f"{self._base}/{endpoint}", params=params or {}, timeout=10)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def get_status(self) -> ProviderStatus:
        is_free = self._key == FREE_KEY
        return ProviderStatus(
            name=self.name,
            available=True,
            plan="free_demo" if is_free else "paid",
            wc2026_accessible=False,  # WC2026 returns null even on free
            quality_level=self.quality_level,
            error=(
                "Free key (123): WC2026 fixtures return null. "
                "v2 livescores require paid plan. "
                "Usable for team badges/metadata only."
            ) if is_free else "",
        )

    def get_live_matches(self) -> list[dict]:
        return []  # Requires paid v2 key

    def get_today_fixtures(self) -> list[dict]:
        return []  # WC2026 returns null on free

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        return []

    def get_standings(self) -> list[dict]:
        return []

    def get_team_badge(self, team_name: str) -> Optional[str]:
        """Return badge URL for a team name (works on free key)."""
        data = self._get("searchteams.php", {"t": team_name})
        teams = data.get("teams") or []
        if teams:
            return teams[0].get("strTeamBadge") or teams[0].get("strTeamLogo")
        return None
