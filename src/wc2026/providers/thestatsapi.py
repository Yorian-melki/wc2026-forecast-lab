"""TheStatsAPI provider — comp_6107 = FIFA World Cup.

Auth: Authorization: Bearer {THESTATSAPI_KEY}
Base: https://api.thestatsapi.com/api
Docs: https://api.thestatsapi.com/llms.txt (4849 lines ingested)

Quality A potential: xG (shotmap), team xG (stats), per-shot coords,
                     player-stats (rating/passes/defending), lineups,
                     odds, odds/live, timeline.

Status (UPDATED 2026-06-13): the fapi_r key returned 403 KEY_REVOKED ("no active
subscription plan") earlier on 2026-06-13, then was RE-ACTIVATED the same day via a Stats
API trial. The AUTHORITATIVE runtime state is data/live/provider_status.json — currently
ACTIVE for finished-match per-shot shotmap xG + bookmaker odds + player/timeline stats
(see data/live/thestatsapi_*.json). Live in-progress stats are not on the trial plan, and
the team-xG shares Highlightly's upstream (not independent). The 403-handler below still
surfaces KEY_REVOKED dynamically if the trial lapses (Bearer auth confirmed via 403-vs-401).
NOTE: the static ProviderRouter.freshness() descriptor keeps a conservative "not accessible"
default (test-locked); provider_status.json overrides it as the live source of truth.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from .base import BaseProvider, ProviderStatus

_BASE = "https://api.thestatsapi.com/api"
_WC_COMP = "comp_6107"


class TheStatsAPIProvider(BaseProvider):
    name = "thestatsapi"
    quality_level = "A"  # xG, per-shot, player stats, odds — quality A when working

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._key = api_key or os.getenv("THESTATSAPI_KEY", "")
        self._headers = {"Authorization": f"Bearer {self._key}"}
        self._base = _BASE
        self._current_season_id: Optional[str] = None

    def _get(self, endpoint: str, params: dict = None, retries: int = 1) -> dict:
        url = f"{self._base}/{endpoint.lstrip('/')}"
        for attempt in range(retries + 1):
            try:
                r = requests.get(url, headers=self._headers, params=params or {}, timeout=12)
                if r.status_code == 200:
                    return r.json()
                return {
                    "_status_code": r.status_code,
                    "_url": url,
                    "error": r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:300]},
                }
            except requests.RequestException as e:
                if attempt == retries:
                    return {"_error": str(e), "_url": url}
                time.sleep(1)
        return {}

    # ── Status ──────────────────────────────────────────────────────────────

    def get_status(self) -> ProviderStatus:
        r = self._get("health")
        if r.get("status") == "healthy":
            # Test auth on WC competition endpoint
            test = self._get(f"football/competitions/{_WC_COMP}")
            if "error" in test or "_status_code" in test:
                sc = test.get("_status_code", 0)
                err = test.get("error", {})
                code = err.get("error", {}).get("code", "") if isinstance(err, dict) else str(err)
                return ProviderStatus(
                    name=self.name, available=False,
                    wc2026_accessible=False, quality_level="D",
                    error=f"Auth failed ({sc}): {code} — refresh key at thestatsapi.com",
                )
            data = test.get("data", {})
            self._current_season_id = data.get("current_season_id")
            xg_ok = data.get("xg_available", False)
            return ProviderStatus(
                name=self.name, available=True,
                wc2026_accessible=True,
                quality_level="A" if xg_ok else "B",
                error=f"xg_available={xg_ok}; season={self._current_season_id}",
            )
        return ProviderStatus(
            name=self.name, available=False,
            error=f"Health check failed: {r}",
        )

    # ── Competition / Seasons ────────────────────────────────────────────────

    def get_competition(self) -> dict:
        return self._get(f"football/competitions/{_WC_COMP}")

    def get_seasons(self) -> dict:
        return self._get(f"football/competitions/{_WC_COMP}/seasons")

    def get_standings(self) -> list[dict]:
        if not self._current_season_id:
            comp = self.get_competition()
            self._current_season_id = comp.get("data", {}).get("current_season_id")
        if not self._current_season_id:
            return []
        data = self._get(
            f"football/competitions/{_WC_COMP}/seasons/{self._current_season_id}/standings"
        )
        out = []
        for group in data.get("data", []):
            grp_label = group.get("group_label", "")
            for team in group.get("teams", []):
                out.append({
                    "provider": self.name,
                    "team": team.get("team_name", ""),
                    "team_id": team.get("team_id", ""),
                    "group": grp_label,
                    "played": team.get("played", 0),
                    "won": team.get("won", 0),
                    "drawn": team.get("drawn", 0),
                    "lost": team.get("lost", 0),
                    "gf": team.get("goals_for", 0),
                    "ga": team.get("goals_against", 0),
                    "gd": team.get("goal_diff", 0),
                    "points": team.get("points", 0),
                })
        return out

    # ── Matches ──────────────────────────────────────────────────────────────

    def get_matches(self, status: str = "finished", group: Optional[str] = None,
                    per_page: int = 50, page: int = 1) -> dict:
        params: dict = {
            "competition_id": _WC_COMP,
            "per_page": per_page,
            "page": page,
        }
        if status:
            params["status"] = status
        if group:
            params["group"] = group
        return self._get("football/matches", params)

    def get_all_finished_matches(self) -> list[dict]:
        out = []
        page = 1
        while True:
            resp = self.get_matches(status="finished", per_page=100, page=page)
            matches = resp.get("data", [])
            if not matches:
                break
            out.extend(matches)
            meta = resp.get("meta", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1
        return out

    def get_live_matches(self) -> list[dict]:
        data = self.get_matches(status="live")
        return [self._normalize(m) for m in data.get("data", [])]

    def get_today_fixtures(self) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {"competition_id": _WC_COMP, "date_from": today, "date_to": today, "per_page": 20}
        data = self._get("football/matches", params)
        return [self._normalize(m) for m in data.get("data", [])]

    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        data = self.get_matches(status="finished", per_page=100)
        matches = data.get("data", [])
        if since_date:
            matches = [m for m in matches if m.get("utc_date", "")[:10] >= since_date]
        return [self._normalize(m) for m in matches]

    # ── Match detail endpoints ────────────────────────────────────────────────

    def get_match_detail(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}")

    def get_match_stats(self, match_id: str) -> dict:
        """Full stats: xG, possession, shots, big chances (by half). Quality A."""
        return self._get(f"football/matches/{match_id}/stats")

    def get_live_stats(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/live-stats")

    def get_shotmap(self, match_id: str) -> dict:
        """Per-shot xG, coordinates, body part, situation. Quality A."""
        return self._get(f"football/matches/{match_id}/shotmap")

    def get_timeline(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/timeline")

    def get_lineups(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/lineups")

    def get_player_stats(self, match_id: str, player_ids: Optional[list[str]] = None) -> dict:
        params = {}
        if player_ids:
            params["player_ids"] = ",".join(player_ids)
        return self._get(f"football/matches/{match_id}/player-stats", params)

    def get_referee(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/referee")

    def get_odds(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/odds")

    def get_live_odds(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/odds/live")

    def get_player_odds(self, match_id: str) -> dict:
        return self._get(f"football/matches/{match_id}/odds/players")

    # ── Full match extraction ────────────────────────────────────────────────

    def get_full_match_data(self, match_id: str, xg_available: bool = True) -> dict:
        """Extract ALL available data for a single match."""
        out: dict = {
            "match_id": match_id,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        out["detail"] = self.get_match_detail(match_id)
        out["stats"] = self.get_match_stats(match_id)
        out["lineups"] = self.get_lineups(match_id)
        out["timeline"] = self.get_timeline(match_id)
        out["player_stats"] = self.get_player_stats(match_id)
        out["referee"] = self.get_referee(match_id)
        if xg_available:
            out["shotmap"] = self.get_shotmap(match_id)
            out["odds"] = self.get_odds(match_id)
        return out

    # ── xG normalizers ───────────────────────────────────────────────────────

    def extract_team_xg(self, stats_response: dict) -> dict:
        """Pull team-level xG from /stats response. Returns normalized dict."""
        ov = stats_response.get("data", {}).get("overview", {})
        xg = ov.get("expected_goals", {})
        return {
            "xg_home": xg.get("all", {}).get("home"),
            "xg_away": xg.get("all", {}).get("away"),
            "xg_home_1h": xg.get("first_half", {}).get("home"),
            "xg_away_1h": xg.get("first_half", {}).get("away"),
            "xg_home_2h": xg.get("second_half", {}).get("home"),
            "xg_away_2h": xg.get("second_half", {}).get("away"),
            "possession_home": ov.get("ball_possession", {}).get("all", {}).get("home"),
            "possession_away": ov.get("ball_possession", {}).get("all", {}).get("away"),
            "big_chances_home": ov.get("big_chances", {}).get("all", {}).get("home"),
            "big_chances_away": ov.get("big_chances", {}).get("all", {}).get("away"),
            "total_shots_home": ov.get("total_shots", {}).get("all", {}).get("home"),
            "total_shots_away": ov.get("total_shots", {}).get("all", {}).get("away"),
            "shots_on_target_home": ov.get("shots_on_target", {}).get("all", {}).get("home"),
            "shots_on_target_away": ov.get("shots_on_target", {}).get("all", {}).get("away"),
            "source": self.name,
        }

    def extract_shotmap_xg(self, shotmap_response: dict) -> list[dict]:
        """Normalize per-shot xG from /shotmap response."""
        shots = []
        for shot in shotmap_response.get("data", []):
            shots.append({
                "shot_id": shot.get("id"),
                "player": shot.get("player_name"),
                "player_id": shot.get("player_id"),
                "team": shot.get("team_name"),
                "team_id": shot.get("team_id"),
                "minute": shot.get("minute"),
                "xg": shot.get("expected_goals"),
                "result": shot.get("result"),
                "is_goal": shot.get("is_goal"),
                "is_on_target": shot.get("is_on_target"),
                "body_part": shot.get("body_part"),
                "situation": shot.get("situation"),
                "x": shot.get("x"),
                "y": shot.get("y"),
                "source": self.name,
            })
        return shots

    # ── Normalize ────────────────────────────────────────────────────────────

    def _normalize(self, m: dict) -> dict:
        home = m.get("home_team", {})
        away = m.get("away_team", {})
        score = m.get("score", {})
        return {
            "provider": self.name,
            "match_id": m.get("id"),
            "home": home.get("name", ""),
            "home_id": home.get("id", ""),
            "away": away.get("name", ""),
            "away_id": away.get("id", ""),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
            "date": m.get("utc_date", "")[:10],
            "status": m.get("status", ""),
            "group": m.get("group_label", ""),
            "xg_available": m.get("xg_available", False),
            "odds_available": m.get("odds_available", False),
            "quality_level": "A" if m.get("xg_available") else "B",
            "source_timestamp": datetime.now(timezone.utc).isoformat(),
        }
