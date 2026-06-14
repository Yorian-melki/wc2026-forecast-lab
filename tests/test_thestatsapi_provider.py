"""Tests for TheStatsAPI provider.

The fapi_r key was KEY_REVOKED early 2026-06-13, then re-activated the same day via a Stats
API trial (runtime authority: data/live/provider_status.json = ACTIVE). These tests use mocked
HTTP regardless and exercise the 403 KEY_REVOKED error path, which stays valid if the trial lapses.
xG extraction logic is tested against the documented response structure.
"""
from __future__ import annotations
from unittest.mock import patch

import pytest

from wc2026.providers.thestatsapi import TheStatsAPIProvider


@pytest.fixture()
def provider():
    return TheStatsAPIProvider(api_key="test-tsa-key")


class TestInit:
    def test_auth_header(self, provider):
        assert "Bearer test-tsa-key" in provider._headers["Authorization"]

    def test_quality_level_a(self, provider):
        assert provider.quality_level == "A"

    def test_wc_comp_constant(self):
        from wc2026.providers.thestatsapi import _WC_COMP
        assert _WC_COMP == "comp_6107"


class TestGetStatus:
    def test_healthy_with_valid_key(self, provider):
        with patch.object(provider, "_get", side_effect=[
            {"status": "healthy"},
            {"data": {"name": "FIFA World Cup", "current_season_id": "s_2026", "xg_available": True}},
        ]):
            status = provider.get_status()
        assert status.available is True
        assert status.quality_level == "A"
        assert status.wc2026_accessible is True

    def test_key_revoked_403(self, provider):
        # _get() wraps parsed JSON body under "error" key; TSA body is {"error": {"code": ...}}
        with patch.object(provider, "_get", side_effect=[
            {"status": "healthy"},
            {"_status_code": 403, "error": {"error": {"code": "KEY_REVOKED", "message": "No active plan", "status_code": 403}}},
        ]):
            status = provider.get_status()
        assert status.available is False
        assert status.wc2026_accessible is False
        assert "KEY_REVOKED" in status.error

    def test_health_fail(self, provider):
        with patch.object(provider, "_get", return_value={"_error": "timeout"}):
            status = provider.get_status()
        assert status.available is False

    def test_quality_b_when_no_xg(self, provider):
        with patch.object(provider, "_get", side_effect=[
            {"status": "healthy"},
            {"data": {"name": "FIFA World Cup", "current_season_id": "s_2026", "xg_available": False}},
        ]):
            status = provider.get_status()
        assert status.quality_level == "B"


class TestExtractTeamXG:
    def _stats_response(self, home_xg, away_xg, home_poss=55, away_poss=45):
        return {
            "data": {
                "overview": {
                    "expected_goals": {
                        "all": {"home": home_xg, "away": away_xg},
                        "first_half": {"home": round(home_xg * 0.3, 2), "away": round(away_xg * 0.4, 2)},
                        "second_half": {"home": round(home_xg * 0.7, 2), "away": round(away_xg * 0.6, 2)},
                    },
                    "ball_possession": {"all": {"home": home_poss, "away": away_poss}},
                    "big_chances": {"all": {"home": 3, "away": 1}},
                    "total_shots": {"all": {"home": 12, "away": 6}},
                    "shots_on_target": {"all": {"home": 5, "away": 2}},
                }
            }
        }

    def test_xg_extracted(self, provider):
        resp = self._stats_response(1.42, 0.54)
        result = provider.extract_team_xg(resp)
        assert result["xg_home"] == 1.42
        assert result["xg_away"] == 0.54

    def test_possession_extracted(self, provider):
        resp = self._stats_response(1.23, 0.96, home_poss=52, away_poss=48)
        result = provider.extract_team_xg(resp)
        assert result["possession_home"] == 52
        assert result["possession_away"] == 48

    def test_big_chances(self, provider):
        resp = self._stats_response(2.3, 0.83)
        result = provider.extract_team_xg(resp)
        assert result["big_chances_home"] == 3
        assert result["big_chances_away"] == 1

    def test_source_field(self, provider):
        resp = self._stats_response(1.46, 0.07)
        result = provider.extract_team_xg(resp)
        assert result["source"] == "thestatsapi"

    def test_half_xg(self, provider):
        resp = self._stats_response(2.0, 1.0)
        result = provider.extract_team_xg(resp)
        assert result["xg_home_1h"] is not None
        assert result["xg_home_2h"] is not None


class TestExtractShotmapXG:
    def _shotmap_response(self, n_shots=5):
        return {
            "data": [
                {
                    "id": f"shot_{i}",
                    "player_name": f"Player {i}",
                    "player_id": f"p_{i}",
                    "team_name": "USA",
                    "team_id": "t_usa",
                    "minute": 15 + i * 10,
                    "expected_goals": round(0.1 + i * 0.05, 2),
                    "result": "Goal" if i == 0 else "Saved",
                    "is_goal": i == 0,
                    "is_on_target": i <= 2,
                    "body_part": "Right Foot",
                    "situation": "Open Play",
                    "x": 80 + i,
                    "y": 50 + i,
                }
                for i in range(n_shots)
            ]
        }

    def test_shots_extracted(self, provider):
        resp = self._shotmap_response(5)
        result = provider.extract_shotmap_xg(resp)
        assert len(result) == 5

    def test_shot_fields(self, provider):
        resp = self._shotmap_response(1)
        shot = provider.extract_shotmap_xg(resp)[0]
        assert shot["shot_id"] == "shot_0"
        assert shot["xg"] == 0.1
        assert shot["is_goal"] is True
        assert shot["x"] == 80
        assert shot["y"] == 50

    def test_source_field(self, provider):
        resp = self._shotmap_response(1)
        shot = provider.extract_shotmap_xg(resp)[0]
        assert shot["source"] == "thestatsapi"

    def test_empty_shotmap(self, provider):
        result = provider.extract_shotmap_xg({"data": []})
        assert result == []


class TestGetCompletedMatches:
    def test_finished_matches_normalized(self, provider):
        mock_resp = {
            "data": [
                {
                    "id": "m_001",
                    "home_team": {"id": "t_mex", "name": "Mexico"},
                    "away_team": {"id": "t_rsa", "name": "South Africa"},
                    "score": {"home": 2, "away": 0},
                    "utc_date": "2026-06-11T18:00:00Z",
                    "status": "finished",
                    "group_label": "Group A",
                    "xg_available": True,
                    "odds_available": False,
                }
            ],
            "meta": {"total_pages": 1}
        }
        with patch.object(provider, "_get", return_value=mock_resp):
            result = provider.get_completed_matches()
        assert len(result) == 1
        assert result[0]["home"] == "Mexico"
        assert result[0]["home_goals"] == 2
        assert result[0]["quality_level"] == "A"

    def test_empty_on_403(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 403, "error": {"code": "KEY_REVOKED"}}):
            result = provider.get_completed_matches()
        assert result == []
