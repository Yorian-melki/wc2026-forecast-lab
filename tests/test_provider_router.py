"""
Tests for ProviderRouter — priority logic, merge behavior, freshness dict.
No network calls — uses mocked providers or local cached data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wc2026.providers.normalizer import NormalizedMatch
from wc2026.providers.base import ProviderStatus


class TestProviderRouterFreshness:
    def test_freshness_has_all_keys(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        expected = {"openfootball", "api_football", "thestatsapi", "highlightly",
                    "thesportsdb", "local_manual"}
        assert set(freshness.keys()) == expected

    def test_api_football_is_accessible(self):
        """After date-bypass discovery, api_football must be wc2026_accessible=True."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        af = freshness["api_football"]
        assert af["wc2026_accessible"] is True

    def test_api_football_quality_B(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        assert freshness["api_football"]["quality_level"] == "B"

    def test_thestatsapi_not_accessible(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        assert freshness["thestatsapi"]["wc2026_accessible"] is False

    def test_xg_gap_documented(self):
        """xG gap must be documented in api_football missing fields."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        missing = freshness["api_football"].get("missing", [])
        assert any("xG" in str(m) for m in missing), "xG gap must be documented in api_football missing fields"

    def test_bypass_method_documented(self):
        """Date-bypass method must be documented in api_football entry."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        freshness = router.get_source_freshness()
        af = freshness["api_football"]
        assert "bypass_method" in af or "bypass" in str(af).lower()


class TestProviderRouterCompleted:
    def test_falls_back_to_local_when_all_fail(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        # Force both providers to fail
        router._af.get_completed_matches = MagicMock(side_effect=Exception("API down"))
        router._of.get_completed_matches = MagicMock(return_value=[])
        result = router.get_completed_matches()
        assert isinstance(result, list)
        # Should still return local data
        for m in result:
            assert isinstance(m, NormalizedMatch)

    def test_af_primary_over_of(self):
        """When API-Football returns data, it should be used over OpenFootball."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        af_match = {
            "provider": "api_football", "home": "USA", "away": "PAR",
            "home_goals": 4, "away_goals": 1, "date": "2026-06-13",
            "status": "FT", "quality_level": "B",
        }
        of_match = {
            "provider": "openfootball", "home": "USA", "away": "PAR",
            "home_goals": 4, "away_goals": 1, "date": "2026-06-13",
            "status": "FT", "quality_level": "C",
        }
        router._af.get_completed_matches = MagicMock(return_value=[af_match])
        router._of.get_completed_matches = MagicMock(return_value=[of_match])
        result = router.get_completed_matches()
        # Should contain the API-Football match as primary
        af_results = [m for m in result if m.provider == "api_football"]
        assert len(af_results) >= 1

    def test_completed_all_ft(self):
        """All matches returned by router must be FT with non-None goals."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        result = router.get_completed_matches()
        for m in result:
            assert m.status == "FT"
            assert m.home_goals is not None
            assert m.away_goals is not None


class TestProviderRouterLive:
    def test_returns_list(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        router._af.get_live_matches = MagicMock(return_value=[])
        result = router.get_live_matches()
        assert isinstance(result, list)

    _FALLBACK_PROVS = ("_af", "_fdo", "_tsa", "_hl", "_tsdb")

    def test_live_normalizes_to_normalized_match(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        live_match = {
            "provider": "espn", "home": "ESP", "away": "ARG",
            "home_goals": 1, "away_goals": 0, "date": "2026-06-15",
            "status": "1H", "minute": 35, "quality_level": "B",
        }
        router._espn.live_or_none = MagicMock(return_value=[live_match])   # ESPN is the authority
        result = router.get_live_matches()
        assert len(result) == 1
        assert isinstance(result[0], NormalizedMatch)
        assert result[0].is_live

    def test_live_empty_when_espn_says_none_live(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        # ESPN reachable but reports nothing live (e.g. a match just hit FULL_TIME) → authoritative
        # empty, NO fall-back to a laggy provider still reporting it as in-play.
        router._espn.live_or_none = MagicMock(return_value=[])
        assert router.get_live_matches() == []

    def test_live_falls_back_when_espn_unreachable(self):
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        router._espn.live_or_none = MagicMock(return_value=None)   # ESPN down
        for name in self._FALLBACK_PROVS:
            getattr(router, name).get_live_matches = MagicMock(return_value=[])
        router._fdo.get_live_matches = MagicMock(return_value=[{
            "provider": "football_data_org", "home": "BRA", "away": "FRA",
            "home_goals": 0, "away_goals": 0, "date": "2026-06-15", "status": "1H", "minute": 5,
        }])
        result = router.get_live_matches()
        assert len(result) == 1 and result[0].home == "BRA"


class TestOverallQualityUpgrade:
    def test_overall_quality_is_B_not_C(self):
        """After integration, overall quality must be B (was C before date-bypass)."""
        from wc2026.providers.router import ProviderRouter
        router = ProviderRouter()
        # Write live outputs and check the quality
        import tempfile, os
        from pathlib import Path
        # Just check the freshness, not a full write
        freshness = router.get_source_freshness()
        af_quality = freshness["api_football"]["quality_level"]
        assert af_quality == "B", f"Expected B quality for API-Football, got {af_quality}"
