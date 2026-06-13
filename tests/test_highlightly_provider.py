"""Tests for Highlightly provider."""
from __future__ import annotations
import json
from unittest.mock import MagicMock, patch

import pytest

from wc2026.providers.highlightly import HighlightlyProvider, _WC_LEAGUE_ID


@pytest.fixture()
def provider():
    return HighlightlyProvider(api_key="test-key-xxxx")


# ── Auth / init ──────────────────────────────────────────────────────────────

class TestHighlightlyInit:
    def test_headers_set(self, provider):
        assert provider._headers["x-rapidapi-key"] == "test-key-xxxx"
        assert provider._headers["x-rapidapi-host"] == "soccer.highlightly.net"

    def test_quality_level_a(self, provider):
        assert provider.quality_level == "A"

    def test_wc_league_id(self):
        assert _WC_LEAGUE_ID == 1635


# ── State parsing ─────────────────────────────────────────────────────────────

class TestStateParser:
    def test_finished_match(self, provider):
        m = {"state": {"description": "Finished", "score": {"current": "2 - 0"}, "clock": 90}}
        desc, hg, ag, clock = provider._parse_state(m)
        assert "finish" in desc.lower()
        assert hg == 2
        assert ag == 0
        assert clock == 90

    def test_not_started(self, provider):
        m = {"state": {"description": "Not started", "score": {"current": ""}, "clock": None}}
        desc, hg, ag, clock = provider._parse_state(m)
        assert "not started" in desc.lower()
        assert hg is None
        assert ag is None

    def test_live_match(self, provider):
        m = {"state": {"description": "Live", "score": {"current": "1 - 0"}, "clock": 67}}
        desc, hg, ag, clock = provider._parse_state(m)
        assert hg == 1
        assert ag == 0
        assert clock == 67

    def test_malformed_score(self, provider):
        m = {"state": {"description": "Finished", "score": {"current": "?"}, "clock": 90}}
        desc, hg, ag, clock = provider._parse_state(m)
        assert hg is None
        assert ag is None


# ── Normalize ─────────────────────────────────────────────────────────────────

class TestNormalize:
    def _make_match(self, home="USA", home_id=100, away="PAR", away_id=200,
                    desc="Finished", score="4 - 1", clock=90, date="2026-06-13", mid=123):
        return {
            "id": mid, "date": date + "T18:00:00Z",
            "homeTeam": {"id": home_id, "name": home},
            "awayTeam": {"id": away_id, "name": away},
            "state": {"description": desc, "score": {"current": score}, "clock": clock},
            "round": "Group Stage", "league": {"id": _WC_LEAGUE_ID},
        }

    def test_completed_status_ft(self, provider):
        m = self._make_match(desc="Finished")
        n = provider._normalize(m)
        assert n["status"] == "FT"

    def test_goals_parsed(self, provider):
        m = self._make_match(score="4 - 1")
        n = provider._normalize(m)
        assert n["home_goals"] == 4
        assert n["away_goals"] == 1

    def test_not_started_ns(self, provider):
        m = self._make_match(desc="Not started", score="", clock=None)
        n = provider._normalize(m)
        assert n["status"] == "NS"
        assert n["home_goals"] is None

    def test_provider_name(self, provider):
        n = provider._normalize(self._make_match())
        assert n["provider"] == "highlightly"

    def test_quality_level_a(self, provider):
        n = provider._normalize(self._make_match())
        assert n["quality_level"] == "A"

    def test_match_id_is_str(self, provider):
        n = provider._normalize(self._make_match(mid=9999))
        assert n["match_id"] == "9999"

    def test_date_truncated(self, provider):
        n = provider._normalize(self._make_match(date="2026-06-13"))
        assert n["date"] == "2026-06-13"


# ── xG extraction ─────────────────────────────────────────────────────────────

class TestExtractXG:
    def _stats(self, team_name, xg, big_chances=2, attacks=50):
        return {
            "team": {"name": team_name},
            "statistics": [
                {"displayName": "Expected Goals", "value": xg},
                {"displayName": "Big Chances Created", "value": big_chances},
                {"displayName": "Attacks", "value": attacks},
                {"displayName": "Expected Assists", "value": round(xg * 0.8, 2)},
            ],
        }

    def test_xg_extracted(self, provider):
        stats = [self._stats("USA", 1.42, big_chances=4), self._stats("Paraguay", 0.54, big_chances=1)]
        result = provider.extract_xg(stats)
        assert "USA" in result
        assert result["USA"]["xg"] == 1.42
        assert result["USA"]["big_chances"] == 4
        assert result["Paraguay"]["xg"] == 0.54

    def test_source_field(self, provider):
        stats = [self._stats("Mexico", 1.46)]
        result = provider.extract_xg(stats)
        assert result["Mexico"]["source"] == "highlightly"

    def test_empty_stats(self, provider):
        result = provider.extract_xg([])
        assert result == {}

    def test_all_known_xg_values(self, provider):
        cases = [
            ("Mexico", 1.46), ("South Africa", 0.07),
            ("Canada", 1.23), ("Bosnia & Herzegovina", 0.96),
            ("South Korea", 2.3), ("Czech Republic", 0.83),
            ("USA", 1.42), ("Paraguay", 0.54),
        ]
        for team, expected_xg in cases:
            result = provider.extract_xg([self._stats(team, expected_xg)])
            assert result[team]["xg"] == expected_xg, f"{team} xG mismatch"


# ── HTTP error handling ───────────────────────────────────────────────────────

class TestErrorHandling:
    def test_get_statistics_404(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 404, "error": "Not found"}):
            result = provider.get_statistics(99999)
            assert result == []

    def test_get_lineups_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 403, "error": "Forbidden"}):
            result = provider.get_lineups(99999)
            assert result == []

    def test_get_completed_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 429, "error": "Rate limit"}):
            result = provider.get_completed_matches()
            assert result == []

    def test_get_standings_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 403, "error": "Forbidden"}):
            result = provider.get_standings()
            assert result == []


# ── Status ────────────────────────────────────────────────────────────────────

class TestGetStatus:
    def test_status_available(self, provider):
        countries_resp = [{"id": 1, "name": "USA"}] * 50
        wc_leagues = [{"id": _WC_LEAGUE_ID, "name": "World Cup"}]
        with patch.object(provider, "_get", side_effect=[countries_resp, wc_leagues]):
            status = provider.get_status()
        assert status.available is True
        assert status.quality_level == "A"
        assert status.wc2026_accessible is True

    def test_status_unavailable_on_http_error(self, provider):
        with patch.object(provider, "_get", return_value={"_status_code": 401, "error": "Unauthorized"}):
            status = provider.get_status()
        assert status.available is False
        assert status.quality_level == "D"

    def test_plan_basic(self, provider):
        with patch.object(provider, "_get", side_effect=[[{"id": 1}] * 10, [{"id": _WC_LEAGUE_ID}]]):
            status = provider.get_status()
        assert status.plan == "basic"


# ── Completed matches filter ───────────────────────────────────────────────────

class TestCompletedMatches:
    def _make_api_response(self, matches):
        return matches

    def test_only_finished_returned(self, provider):
        finished = {
            "id": 111, "date": "2026-06-11T18:00:00Z",
            "homeTeam": {"id": 1, "name": "Mexico"},
            "awayTeam": {"id": 2, "name": "South Africa"},
            "state": {"description": "Finished", "score": {"current": "2 - 0"}, "clock": 90},
            "round": "Group A", "league": {"id": _WC_LEAGUE_ID},
        }
        scheduled = {
            "id": 222, "date": "2026-06-15T18:00:00Z",
            "homeTeam": {"id": 3, "name": "Brazil"},
            "awayTeam": {"id": 4, "name": "Morocco"},
            "state": {"description": "Not started", "score": {"current": ""}, "clock": None},
            "round": "Group C", "league": {"id": _WC_LEAGUE_ID},
        }
        with patch.object(provider, "_get_matches_by_date", return_value=[finished, scheduled]):
            result = provider.get_completed_matches()
        ft = [m for m in result if m["status"] == "FT"]
        ns = [m for m in result if m["status"] == "NS"]
        assert len(ft) >= 1
        assert len(ns) == 0

    def test_goals_in_completed(self, provider):
        m = {
            "id": 333, "date": "2026-06-13T18:00:00Z",
            "homeTeam": {"id": 5, "name": "USA"},
            "awayTeam": {"id": 6, "name": "Paraguay"},
            "state": {"description": "Finished", "score": {"current": "4 - 1"}, "clock": 90},
            "round": "Group D", "league": {"id": _WC_LEAGUE_ID},
        }
        with patch.object(provider, "_get_matches_by_date", return_value=[m]):
            result = provider.get_completed_matches()
        ft = [r for r in result if r["status"] == "FT"]
        assert ft[0]["home_goals"] == 4
        assert ft[0]["away_goals"] == 1
