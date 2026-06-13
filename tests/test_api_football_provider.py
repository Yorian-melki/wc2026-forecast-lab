"""
Tests for ApiFootballProvider date-bypass and normalization logic.
No network calls — tests use mocked requests or locally saved probe responses.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wc2026.providers.api_football import ApiFootballProvider, _name_to_code, WC_LEAGUE_ID


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

class TestNameToCode:
    def test_south_korea(self):
        assert _name_to_code("South Korea") == "KOR"

    def test_czechia(self):
        assert _name_to_code("Czechia") == "CZE"

    def test_bosnia(self):
        assert _name_to_code("Bosnia & Herzegovina") == "BIH"

    def test_usa(self):
        assert _name_to_code("USA") == "USA"

    def test_turkey_with_umlaut(self):
        assert _name_to_code("Türkiye") == "TUR"

    def test_ivory_coast(self):
        assert _name_to_code("Ivory Coast") == "CIV"

    def test_unknown_name_truncates(self):
        result = _name_to_code("Zembolia")
        assert isinstance(result, str) and len(result) <= 3


# ---------------------------------------------------------------------------
# Normalize helper
# ---------------------------------------------------------------------------

SAMPLE_FIXTURE = {
    "fixture": {
        "id": 1489370,
        "date": "2026-06-13T01:00:00+00:00",
        "status": {"short": "FT", "elapsed": 90},
        "venue": {"name": "SoFi Stadium"},
    },
    "league": {"id": 1, "name": "World Cup"},
    "teams": {
        "home": {"name": "USA"},
        "away": {"name": "Paraguay"},
    },
    "goals": {"home": 4, "away": 1},
}


class TestNormalize:
    def setup_method(self):
        self.prov = ApiFootballProvider(api_key="test")

    def test_normalize_basic(self):
        out = self.prov._normalize(SAMPLE_FIXTURE)
        assert out["home"] == "USA"
        assert out["away"] == "PAR"
        assert out["home_goals"] == 4
        assert out["away_goals"] == 1
        assert out["status"] == "FT"
        assert out["date"] == "2026-06-13"

    def test_normalize_quality_level(self):
        out = self.prov._normalize(SAMPLE_FIXTURE)
        assert out["quality_level"] == "B"

    def test_normalize_match_id(self):
        out = self.prov._normalize(SAMPLE_FIXTURE)
        assert out["match_id"] == 1489370

    def test_normalize_preserves_full_name(self):
        out = self.prov._normalize(SAMPLE_FIXTURE)
        assert out["home_name_full"] == "USA"
        assert out["away_name_full"] == "Paraguay"


# ---------------------------------------------------------------------------
# Date-bypass filtering
# ---------------------------------------------------------------------------

MULTI_LEAGUE_RESPONSE = {
    "response": [
        {
            "fixture": {"id": 1489370, "date": "2026-06-13T01:00:00+00:00",
                        "status": {"short": "FT", "elapsed": 90},
                        "venue": {"name": "SoFi Stadium"}},
            "league": {"id": 1, "name": "World Cup"},
            "teams": {"home": {"name": "USA"}, "away": {"name": "Paraguay"}},
            "goals": {"home": 4, "away": 1},
        },
        {
            "fixture": {"id": 9999, "date": "2026-06-13T20:00:00+00:00",
                        "status": {"short": "FT", "elapsed": 90},
                        "venue": {"name": "Camp Nou"}},
            "league": {"id": 140, "name": "La Liga"},
            "teams": {"home": {"name": "Barcelona"}, "away": {"name": "Real Madrid"}},
            "goals": {"home": 2, "away": 1},
        },
    ]
}


class TestDateBypass:
    def setup_method(self):
        self.prov = ApiFootballProvider(api_key="test")

    def test_filters_to_wc_only(self):
        with patch.object(self.prov, "_get", return_value=MULTI_LEAGUE_RESPONSE):
            fixtures = self.prov.get_wc_fixtures_by_date("2026-06-13")
        assert len(fixtures) == 1
        assert fixtures[0]["league"]["id"] == WC_LEAGUE_ID

    def test_today_fixtures_filters_wc(self):
        with patch.object(self.prov, "_get", return_value=MULTI_LEAGUE_RESPONSE):
            today = self.prov.get_today_fixtures()
        assert len(today) == 1
        assert today[0]["home"] == "USA"

    def test_live_matches_filters_wc(self):
        live_fixture = {**SAMPLE_FIXTURE,
                        "fixture": {**SAMPLE_FIXTURE["fixture"],
                                    "status": {"short": "1H", "elapsed": 35}},
                        "goals": {"home": 1, "away": 0}}
        response = {"response": [live_fixture, MULTI_LEAGUE_RESPONSE["response"][1]]}
        with patch.object(self.prov, "_get", return_value=response):
            live = self.prov.get_live_matches()
        assert len(live) == 1
        assert live[0]["home"] == "USA"
        assert live[0]["minute"] == 35


# ---------------------------------------------------------------------------
# Completed matches (FT filter)
# ---------------------------------------------------------------------------

class TestCompletedMatches:
    def setup_method(self):
        self.prov = ApiFootballProvider(api_key="test")

    def test_only_ft_returned(self):
        scheduled_fixture = {
            "fixture": {"id": 1489373, "date": "2026-06-13T19:00:00+00:00",
                        "status": {"short": "NS", "elapsed": None},
                        "venue": {"name": "Gillette Stadium"}},
            "league": {"id": 1},
            "teams": {"home": {"name": "Qatar"}, "away": {"name": "Switzerland"}},
            "goals": {"home": None, "away": None},
        }
        response = {"response": [SAMPLE_FIXTURE, scheduled_fixture]}
        with patch.object(self.prov, "_get", return_value=response):
            completed = self.prov.get_completed_matches(days_back=1)
        assert len(completed) == 1
        assert completed[0]["home"] == "USA"
        assert completed[0]["status"] == "FT"

    def test_completed_has_goals(self):
        with patch.object(self.prov, "_get", return_value={"response": [SAMPLE_FIXTURE]}):
            completed = self.prov.get_completed_matches(days_back=1)
        assert completed[0]["home_goals"] == 4
        assert completed[0]["away_goals"] == 1


# ---------------------------------------------------------------------------
# Fixture detail endpoints (events, stats, lineups)
# ---------------------------------------------------------------------------

SAMPLE_EVENTS_RESPONSE = {
    "response": [
        {"time": {"elapsed": 7, "extra": None}, "type": "Goal", "detail": "Own Goal",
         "team": {"name": "USA"}, "player": {"name": "D. Bobadilla"}, "assist": {"name": None}},
        {"time": {"elapsed": 31, "extra": None}, "type": "Goal", "detail": "Normal Goal",
         "team": {"name": "USA"}, "player": {"name": "F. Balogun"}, "assist": {"name": None}},
        {"time": {"elapsed": 73, "extra": None}, "type": "Goal", "detail": "Normal Goal",
         "team": {"name": "Paraguay"}, "player": {"name": "Mauricio"}, "assist": {"name": None}},
    ]
}

SAMPLE_STATS_RESPONSE = {
    "response": [
        {"team": {"name": "USA"}, "statistics": [
            {"type": "Shots on Goal", "value": 6},
            {"type": "Total Shots", "value": 16},
            {"type": "Corner Kicks", "value": 3},
        ]},
        {"team": {"name": "Paraguay"}, "statistics": [
            {"type": "Shots on Goal", "value": 1},
            {"type": "Total Shots", "value": 9},
        ]},
    ]
}

SAMPLE_LINEUPS_RESPONSE = {
    "response": [
        {"team": {"name": "USA"}, "formation": "4-2-3-1",
         "coach": {"name": "Mauricio Pochettino"},
         "startXI": [{"player": {"name": "Matthew Freese"}}],
         "substitutes": [{"player": {"name": "Weston McKennie"}}]},
        {"team": {"name": "Paraguay"}, "formation": "4-4-2",
         "coach": {"name": "Gustavo Alfaro"},
         "startXI": [{"player": {"name": "Orlando Gill"}}],
         "substitutes": []},
    ]
}


class TestFixtureDetailEndpoints:
    def setup_method(self):
        self.prov = ApiFootballProvider(api_key="test")

    def test_events_returns_goals(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_EVENTS_RESPONSE):
            events = self.prov.get_fixture_events(1489370)
        goals = [e for e in events if e["type"] == "Goal"]
        assert len(goals) == 3

    def test_events_normalizes_team_code(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_EVENTS_RESPONSE):
            events = self.prov.get_fixture_events(1489370)
        assert events[0]["team"] == "USA"
        assert events[2]["team"] == "PAR"

    def test_stats_returns_by_code(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_STATS_RESPONSE):
            stats = self.prov.get_fixture_stats(1489370)
        assert "USA" in stats
        assert "PAR" in stats
        assert stats["USA"]["shots_on_goal"] == 6
        assert stats["USA"]["total_shots"] == 16

    def test_lineups_returns_formation(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_LINEUPS_RESPONSE):
            lineups = self.prov.get_fixture_lineups(1489370)
        assert lineups["USA"]["formation"] == "4-2-3-1"
        assert lineups["USA"]["coach"] == "Mauricio Pochettino"
        assert "Matthew Freese" in lineups["USA"]["startXI"]

    def test_lineups_no_xg(self):
        """API-Football does not provide xG — this test documents the gap."""
        with patch.object(self.prov, "_get", return_value=SAMPLE_STATS_RESPONSE):
            stats = self.prov.get_fixture_stats(1489370)
        # No xG field anywhere
        for team_stats in stats.values():
            assert "expected_goals" not in team_stats
            assert "xg" not in team_stats

    def test_standings_returns_empty_free_plan(self):
        """Standings endpoint blocked on Free plan — must return empty list, not crash."""
        standings = self.prov.get_standings()
        assert standings == []


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

SAMPLE_STATUS_RESPONSE = {
    "response": {
        "subscription": {"plan": "Free"},
        "requests": {"current": 21, "limit_day": 100},
    }
}


class TestGetStatus:
    def setup_method(self):
        self.prov = ApiFootballProvider(api_key="test")

    def test_status_wc_accessible_free_plan(self):
        """Free plan should now be wc2026_accessible=True (date-bypass discovered)."""
        with patch.object(self.prov, "_get", return_value=SAMPLE_STATUS_RESPONSE):
            status = self.prov.get_status()
        assert status.wc2026_accessible is True
        assert status.available is True

    def test_status_plan_reported(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_STATUS_RESPONSE):
            status = self.prov.get_status()
        assert status.plan == "Free"

    def test_status_requests_tracked(self):
        with patch.object(self.prov, "_get", return_value=SAMPLE_STATUS_RESPONSE):
            status = self.prov.get_status()
        assert status.requests_used == 21
        assert status.requests_limit == 100
