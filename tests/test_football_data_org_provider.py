"""Tests for football-data.org provider."""
from __future__ import annotations
from unittest.mock import patch

import pytest

from wc2026.providers.football_data_org import FootballDataOrgProvider


@pytest.fixture()
def provider():
    return FootballDataOrgProvider(api_key="test-fdo-key")


class TestInit:
    def test_auth_header(self, provider):
        assert provider._headers["X-Auth-Token"] == "test-fdo-key"

    def test_quality_b(self, provider):
        assert provider.quality_level == "B"


class TestGetStatus:
    def test_available_when_competition_ok(self, provider):
        with patch.object(provider, "_get", return_value={"name": "FIFA World Cup", "id": 2000}):
            status = provider.get_status()
        assert status.available is True
        assert status.wc2026_accessible is True
        assert status.quality_level == "B"

    def test_unavailable_on_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 403, "error": "Forbidden"}):
            status = provider.get_status()
        assert status.available is False

    def test_wc2026_accessible_on_any_non_empty_name(self, provider):
        with patch.object(provider, "_get", return_value={"name": "FIFA World Cup", "id": 2000}):
            status = provider.get_status()
        assert status.wc2026_accessible is True


class TestStandings:
    def _make_standings(self):
        return {
            "standings": [
                {
                    "stage": "GROUP_A",
                    "table": [
                        {"team": {"name": "Mexico", "shortName": "Mexico", "tla": "MEX"},
                         "position": 1, "playedGames": 1, "won": 1, "draw": 0, "lost": 0,
                         "goalsFor": 2, "goalsAgainst": 0, "goalDifference": 2, "points": 3},
                        {"team": {"name": "South Korea", "shortName": "Korea Republic", "tla": "KOR"},
                         "position": 2, "playedGames": 1, "won": 1, "draw": 0, "lost": 0,
                         "goalsFor": 2, "goalsAgainst": 1, "goalDifference": 1, "points": 3},
                    ],
                }
            ]
        }

    def test_standings_parsed(self, provider):
        with patch.object(provider, "_get", return_value=self._make_standings()):
            result = provider.get_standings()
        assert len(result) == 2
        mex_list = [r for r in result if r["team_name_full"] == "Mexico"]
        assert len(mex_list) == 1
        mex = mex_list[0]
        assert mex["points"] == 3
        assert mex["won"] == 1
        assert mex["gf"] == 2

    def test_standings_empty_on_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 403, "error": "x"}):
            result = provider.get_standings()
        assert result == []

    def test_provider_field(self, provider):
        with patch.object(provider, "_get", return_value=self._make_standings()):
            result = provider.get_standings()
        for r in result:
            assert r["provider"] == "football_data_org"


class TestCompletedMatches:
    def _make_matches_response(self):
        return {
            "matches": [
                {
                    "id": 537327, "utcDate": "2026-06-11T18:00:00Z",
                    "status": "FINISHED", "group": "GROUP_A", "stage": "GROUP_STAGE",
                    "homeTeam": {"id": 1, "tla": "MEX", "shortName": "Mexico"},
                    "awayTeam": {"id": 2, "tla": "RSA", "shortName": "South Africa"},
                    "score": {"fullTime": {"home": 2, "away": 0}},
                },
                {
                    "id": 537333, "utcDate": "2026-06-12T21:00:00Z",
                    "status": "SCHEDULED", "group": "GROUP_B", "stage": "GROUP_STAGE",
                    "homeTeam": {"id": 3, "tla": "CAN", "shortName": "Canada"},
                    "awayTeam": {"id": 4, "tla": "BIH", "shortName": "Bosnia"},
                    "score": {"fullTime": {"home": None, "away": None}},
                },
            ]
        }

    def test_only_finished_returned(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches()
        assert len(result) == 1
        assert result[0]["home"] == "MEX"
        assert result[0]["status"] == "FT"

    def test_goals_correct(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches()
        assert result[0]["home_goals"] == 2
        assert result[0]["away_goals"] == 0

    def test_empty_on_api_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 429, "error": "rate limit"}):
            result = provider.get_completed_matches()
        assert result == []

    def test_match_id_is_str(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches()
        assert result[0]["match_id"] == "537327"

    def test_tla_used_for_team_code(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches()
        assert result[0]["home"] == "MEX"
        assert result[0]["away"] == "RSA"

    def test_since_date_filter(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches(since_date="2026-06-12")
        assert result == []

    def test_quality_level_b(self, provider):
        with patch.object(provider, "_get", return_value=self._make_matches_response()):
            result = provider.get_completed_matches()
        assert result[0]["quality_level"] == "B"
