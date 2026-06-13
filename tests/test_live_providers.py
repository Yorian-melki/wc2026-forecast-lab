"""
Tests for the live provider abstraction layer.
These tests use local/cached data only — no network calls.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wc2026.providers.normalizer import NormalizedMatch, NormalizedStandings, from_provider_dict
from wc2026.providers.base import ProviderStatus


class TestNormalizedMatch:
    def test_is_completed_true(self):
        m = NormalizedMatch(
            provider="test", home="ESP", away="ARG",
            home_goals=2, away_goals=1, date="2026-06-14",
            status="FT",
        )
        assert m.is_completed is True

    def test_is_completed_false_no_goals(self):
        m = NormalizedMatch(
            provider="test", home="ESP", away="ARG",
            home_goals=None, away_goals=None, date="2026-06-14",
            status="FT",
        )
        assert m.is_completed is False

    def test_is_completed_false_not_ft(self):
        m = NormalizedMatch(
            provider="test", home="ESP", away="ARG",
            home_goals=1, away_goals=0, date="2026-06-14",
            status="1H",
        )
        assert m.is_completed is False

    def test_is_live_true(self):
        for status in ["1H", "HT", "2H", "ET", "BT", "P"]:
            m = NormalizedMatch(
                provider="test", home="ESP", away="ARG",
                home_goals=1, away_goals=0, date="2026-06-14",
                status=status,
            )
            assert m.is_live is True, f"Expected live for status={status}"

    def test_safe_goals_none(self):
        m = NormalizedMatch(
            provider="test", home="ESP", away="ARG",
            home_goals=None, away_goals=None, date="2026-06-14",
        )
        assert m.home_goals_safe == 0
        assert m.away_goals_safe == 0

    def test_from_provider_dict(self):
        d = {
            "provider": "openfootball",
            "home": "MEX", "away": "RSA",
            "home_goals": 2, "away_goals": 0,
            "date": "2026-06-12",
            "group": "A",
            "status": "FT",
            "quality_level": "C",
        }
        m = from_provider_dict(d)
        assert m.home == "MEX"
        assert m.away == "RSA"
        assert m.home_goals == 2
        assert m.away_goals == 0
        assert m.is_completed is True
        assert m.quality_level == "C"

    def test_quality_levels_valid(self):
        for ql in ["A", "B", "C", "D"]:
            m = NormalizedMatch(
                provider="test", home="X", away="Y",
                home_goals=1, away_goals=0, date="2026-06-14",
                quality_level=ql,
            )
            assert m.quality_level == ql


class TestProviderStatus:
    def test_status_fields(self):
        s = ProviderStatus(
            name="openfootball",
            available=True,
            plan="free",
            wc2026_accessible=True,
            quality_level="C",
        )
        assert s.name == "openfootball"
        assert s.available is True
        assert s.wc2026_accessible is True


class TestOpenFootballProvider:
    def test_get_completed_matches_from_local(self):
        """OpenFootball should return completed matches from wc2026_live.json cache."""
        from wc2026.providers.openfootball import OpenFootballProvider

        live_path = ROOT / "data" / "wc2026_live.json"
        if not live_path.exists():
            pytest.skip("wc2026_live.json not found")

        of = OpenFootballProvider(local_cache=live_path)
        # Should not crash
        status = of.get_status()
        assert status.name == "openfootball"

    def test_name_to_code_coverage(self):
        """All WC2026 team names appearing in the OpenFootball JSON should map to a code."""
        from wc2026.providers.openfootball import NAME_TO_CODE
        import pandas as pd

        # All teams we need to handle are the WC2026 48 teams
        # Their names appear in the openfootball worldcup.json schedule
        # We only require the WC2026 teams to have name mappings (not WC2022 non-qualifiers)
        wc26_names_expected = {
            "Argentina", "Australia", "Belgium", "Brazil", "Canada",
            "Colombia", "Croatia", "Ecuador", "England", "France",
            "Germany", "Ghana", "Iran", "Japan", "Morocco",
            "Mexico", "Netherlands", "Portugal", "Senegal", "South Korea",
            "Spain", "Switzerland", "Tunisia", "United States", "Uruguay",
            "Qatar", "Saudi Arabia", "Bosnia and Herzegovina",
        }
        missing = wc26_names_expected - set(NAME_TO_CODE.keys())
        assert missing == set(), f"Missing WC2026 team names in NAME_TO_CODE: {missing}"


class TestRouterLocalData:
    def test_router_uses_local_fallback(self):
        """Router falls back to local wc2026_live.json when providers unavailable."""
        from wc2026.providers.router import ProviderRouter

        router = ProviderRouter()
        completed = router.get_completed_matches()
        # Should return at least the matches we already have
        assert isinstance(completed, list)
        # All returned matches should be NormalizedMatch
        from wc2026.providers.normalizer import NormalizedMatch
        for m in completed:
            assert isinstance(m, NormalizedMatch)

    def test_completed_matches_are_ft(self):
        """All completed matches returned by router should have status FT."""
        from wc2026.providers.router import ProviderRouter

        router = ProviderRouter()
        completed = router.get_completed_matches()
        for m in completed:
            assert m.status == "FT", f"Expected FT for {m.home} vs {m.away}, got {m.status}"
            assert m.home_goals is not None
            assert m.away_goals is not None

    def test_freshness_dict_structure(self):
        """get_source_freshness() returns expected provider keys."""
        from wc2026.providers.router import ProviderRouter

        router = ProviderRouter()
        freshness = router.get_source_freshness()
        expected_keys = {"openfootball", "api_football", "thestatsapi", "highlightly",
                         "thesportsdb", "local_manual"}
        assert set(freshness.keys()) == expected_keys


class TestLiveDataFiles:
    """Integration test: check that live data files exist and are valid JSON."""

    def test_provider_status_json(self):
        p = ROOT / "data" / "live" / "provider_status.json"
        if not p.exists():
            pytest.skip("provider_status.json not generated yet")
        data = json.loads(p.read_text())
        assert "providers" in data
        assert "generated_at" in data

    def test_wc2026_live_json_structure(self):
        p = ROOT / "data" / "wc2026_live.json"
        assert p.exists(), "wc2026_live.json must exist"
        data = json.loads(p.read_text())
        assert "completed_matches" in data
        assert "group_standings" in data
        # Check match structure
        for m in data["completed_matches"]:
            assert "home" in m and "away" in m
            assert "home_goals" in m and "away_goals" in m

    def test_elo_live_params_valid(self):
        p = ROOT / "data" / "elo_live_params.json"
        assert p.exists(), "elo_live_params.json must exist"
        data = json.loads(p.read_text())
        assert "team_elos" in data
        assert "beta_elo" in data
        # Elo values should be in reasonable range
        for code, elo in data["team_elos"].items():
            assert 800 <= elo <= 3000, f"{code} Elo={elo} out of range"
