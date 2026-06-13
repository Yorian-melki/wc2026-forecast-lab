"""Tests for Wave 2: margin removal, Kelly criterion, value detection."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


# =============================================================================
# MARGIN REMOVAL
# =============================================================================

class TestMarginRemoval:
    """Exhaustive tests for all three margin removal methods."""

    FAIR_ODDS = [2.0, 3.0, 6.0]         # sum 1/o_i = 0.5+0.33+0.17 = 1.0 (no margin)
    OVERROUND_ODDS = [1.90, 3.30, 6.00]  # typical bookmaker H2H (1X2)

    def _total_fair(self, result) -> float:
        return sum(result.fair_probs)

    def test_basic_fair_odds_no_change(self):
        from wc2026.odds.margin_removal import remove_margin
        fp = remove_margin(self.FAIR_ODDS, method="basic")
        assert abs(self._total_fair(fp) - 1.0) < 1e-9
        assert abs(fp.overround - 1.0) < 0.01
        assert fp.margin_pct < 1.0

    def test_power_fair_odds_no_change(self):
        from wc2026.odds.margin_removal import remove_margin
        fp = remove_margin(self.FAIR_ODDS, method="power")
        assert abs(self._total_fair(fp) - 1.0) < 1e-6

    def test_shin_fair_odds_no_change(self):
        from wc2026.odds.margin_removal import remove_margin
        fp = remove_margin(self.FAIR_ODDS, method="shin")
        assert abs(self._total_fair(fp) - 1.0) < 1e-6

    def test_all_methods_sum_to_one(self):
        from wc2026.odds.margin_removal import remove_margin
        for method in ("basic", "power", "shin"):
            fp = remove_margin(self.OVERROUND_ODDS, method=method)
            assert abs(sum(fp.fair_probs) - 1.0) < 1e-9, \
                f"{method}: sum={sum(fp.fair_probs)}"

    def test_overround_correctly_computed(self):
        from wc2026.odds.margin_removal import remove_margin
        fp = remove_margin(self.OVERROUND_ODDS, method="basic")
        expected_K = sum(1 / o for o in self.OVERROUND_ODDS)
        assert abs(fp.overround - expected_K) < 1e-10

    def test_all_methods_preserve_favorite_ordering(self):
        """After margin removal, the favourite should still have highest probability."""
        from wc2026.odds.margin_removal import remove_margin
        # Favourite has shortest odds (2.20), outsider has longest (4.50)
        odds = [2.20, 3.40, 4.50]
        for method in ("basic", "power", "shin"):
            fp = remove_margin(odds, method=method)
            assert fp.fair_probs[0] > fp.fair_probs[1] > fp.fair_probs[2], \
                f"{method}: ordering not preserved {fp.fair_probs}"

    def test_margin_removal_reduces_longshot_bias(self):
        """Power and Shin should give higher fair probability to longshots vs basic."""
        from wc2026.odds.margin_removal import remove_margin
        # Strong favourite vs two longshots
        odds = [1.25, 8.0, 12.0]
        basic = remove_margin(odds, method="basic")
        shin = remove_margin(odds, method="shin")
        # Shin should redistribute slightly more to longshots
        assert shin.fair_probs[2] >= basic.fair_probs[2] - 0.01

    def test_fair_probs_non_negative(self):
        from wc2026.odds.margin_removal import remove_margin
        for method in ("basic", "power", "shin"):
            for odds in [[1.50, 3.50, 6.00], [1.10, 12.0, 15.0], [2.0, 2.0, 4.0]]:
                fp = remove_margin(odds, method=method)
                assert all(p >= 0 for p in fp.fair_probs), \
                    f"{method} gave negative prob for {odds}"

    def test_invalid_odds_raise(self):
        from wc2026.odds.margin_removal import remove_margin
        with pytest.raises(ValueError):
            remove_margin([1.0, 2.0, 3.0])   # odds = 1.0 not valid
        with pytest.raises(ValueError):
            remove_margin([2.0])              # only 1 outcome

    def test_implied_overround_function(self):
        from wc2026.odds.margin_removal import implied_overround
        # Perfect market: 1/2 + 1/3 + 1/6 = 1.0
        assert abs(implied_overround([2.0, 3.0, 6.0]) - 1.0) < 1e-10
        # 10% margin: all odds scaled by 1/1.1
        scaled = [o / 1.1 for o in [2.0, 3.0, 6.0]]
        assert abs(implied_overround(scaled) - 1.1) < 1e-9

    def test_compare_methods_returns_all_three(self):
        from wc2026.odds.margin_removal import compare_methods
        result = compare_methods([1.80, 3.60, 5.00])
        assert set(result.keys()) == {"basic", "power", "shin"}


# =============================================================================
# KELLY CRITERION
# =============================================================================

class TestKelly:

    def test_kelly_zero_for_no_edge(self):
        """If model prob = market fair prob → 0 edge → Kelly = 0."""
        from wc2026.odds.kelly import kelly_fraction
        # model_p matches odds fair implied prob
        odds = 2.0  # fair implies 50%
        f = kelly_fraction(0.50, odds)
        assert abs(f) < 1e-10, f"Kelly should be ~0 for no edge, got {f}"

    def test_kelly_positive_for_positive_edge(self):
        from wc2026.odds.kelly import kelly_fraction
        # Model says 60%, odds imply 50%
        f = kelly_fraction(0.60, 2.0)
        assert f > 0

    def test_kelly_zero_for_negative_edge(self):
        from wc2026.odds.kelly import kelly_fraction
        # Model says 40%, odds imply 50% (no value)
        f = kelly_fraction(0.40, 2.0)
        assert f == 0.0

    def test_kelly_bounded_0_1(self):
        from wc2026.odds.kelly import kelly_fraction
        for p in [0.01, 0.1, 0.5, 0.9, 0.99]:
            for o in [1.5, 2.0, 3.0, 5.0, 10.0]:
                f = kelly_fraction(p, o)
                assert 0.0 <= f <= 1.0, f"kelly_fraction({p},{o}) = {f} out of [0,1]"

    def test_kelly_formula_exact(self):
        """Verify against analytic formula: f* = (p·b - q) / b."""
        from wc2026.odds.kelly import kelly_fraction
        p, o = 0.55, 2.10
        b = o - 1.0
        expected = (p * b - (1 - p)) / b
        result = kelly_fraction(p, o)
        assert abs(result - expected) < 1e-10

    def test_expected_value_formula(self):
        from wc2026.odds.kelly import expected_value
        # EV = p * decimal_odds - 1
        assert abs(expected_value(0.5, 2.0) - 0.0) < 1e-10     # fair game, EV=0
        assert expected_value(0.6, 2.0) > 0                      # positive edge
        assert expected_value(0.4, 2.0) < 0                      # negative edge

    def test_kelly_stake_is_value_when_edge_high(self):
        from wc2026.odds.kelly import compute_kelly_stake
        stake = compute_kelly_stake("ESP", 3.0, 0.45, 0.30, min_edge_pct=2.0)
        assert stake.is_value_bet, "15pp edge should be a value bet"
        assert stake.edge > 0.10

    def test_kelly_stake_not_value_when_edge_small_and_ev_negative(self):
        # Negative EV: model sees same prob as market → Kelly = 0 → not value
        from wc2026.odds.kelly import compute_kelly_stake
        stake = compute_kelly_stake("QAT", 20.0, 0.050, 0.050, min_edge_pct=2.0)
        assert not stake.is_value_bet, "no edge, no value"
        assert stake.full_kelly == 0.0

    def test_kelly_table_sorted_by_edge(self):
        from wc2026.odds.kelly import kelly_table
        model_probs = {"ESP": 0.07, "FRA": 0.06, "ARG": 0.08}
        best_odds = {"ESP": 16.0, "FRA": 18.0, "ARG": 20.0}
        market_fair = {"ESP": 0.05, "FRA": 0.05, "ARG": 0.05}
        stakes = kelly_table(model_probs, best_odds, market_fair, min_edge_pct=0.0)
        edges = [s.edge for s in stakes]
        assert edges == sorted(edges, reverse=True), "Not sorted by edge descending"

    def test_diversified_kelly_respects_max_exposure(self):
        from wc2026.odds.kelly import kelly_table, diversified_kelly
        # 5 teams each with 5% edge → individual quarter-kelly might be large
        model_probs = {t: 0.08 for t in ["A","B","C","D","E"]}
        best_odds = {t: 14.0 for t in ["A","B","C","D","E"]}
        market_fair = {t: 0.06 for t in ["A","B","C","D","E"]}
        stakes = kelly_table(model_probs, best_odds, market_fair, min_edge_pct=1.0)
        div = diversified_kelly(stakes, max_total_exposure=0.15)
        total = sum(div.values())
        assert total <= 0.155, f"Total exposure {total:.3f} exceeds 0.15"

    def test_quarter_kelly_is_quarter_of_full(self):
        from wc2026.odds.kelly import compute_kelly_stake
        stake = compute_kelly_stake("ENG", 5.0, 0.30, 0.18)
        assert abs(stake.quarter_kelly - stake.full_kelly * 0.25) < 1e-9
        assert abs(stake.half_kelly - stake.full_kelly * 0.50) < 1e-9


# =============================================================================
# DEMO MODE (end-to-end without API key)
# =============================================================================

class TestDemoMode:

    def test_demo_outright_odds_covers_48_teams(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        result = _demo_outright_odds()
        assert len(result.covered_teams()) == 48, \
            f"Expected 48 teams, got {len(result.covered_teams())}"

    def test_demo_outright_all_odds_above_one(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        result = _demo_outright_odds()
        for code, bks in result.teams.items():
            for bk, odds in bks.items():
                assert odds > 1.0, f"{code}/{bk}: odds={odds} ≤ 1.0"

    def test_demo_outright_consensus_returns_nonzero(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        result = _demo_outright_odds()
        for code in ["ESP", "FRA", "ARG", "QAT", "CUW"]:
            c = result.consensus_odds(code)
            assert c > 1.0, f"{code} consensus_odds={c}"

    def test_demo_outright_favorites_have_lower_odds(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        result = _demo_outright_odds()
        esp_odds = result.consensus_odds("ESP")
        qat_odds = result.consensus_odds("QAT")
        assert esp_odds < qat_odds, \
            f"ESP ({esp_odds:.2f}) should have lower odds than QAT ({qat_odds:.2f})"

    def test_demo_match_odds_covers_all_group_matches(self):
        from wc2026.odds.fetcher import _demo_match_odds
        matches = _demo_match_odds()
        # 12 groups × (4C2=6) matches each = 72 group matches total
        assert len(matches) == 72, f"Expected 72 group matches, got {len(matches)}"

    def test_demo_match_odds_three_way_valid(self):
        from wc2026.odds.fetcher import _demo_match_odds
        matches = _demo_match_odds()
        for mo in matches[:10]:
            cons = mo.consensus_odds
            assert cons["home"] > 1.0
            assert cons["draw"] > 1.0
            assert cons["away"] > 1.0

    def test_champion_market_analysis_runs(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        from wc2026.odds.value_detector import analyze_champion_market
        outright = _demo_outright_odds()
        stakes = analyze_champion_market(outright, method="shin", min_edge_pct=2.0)
        assert len(stakes) > 0
        assert all(s.model_prob >= 0 for s in stakes)
        assert all(s.market_fair_prob >= 0 for s in stakes)

    def test_champion_bets_sorted_by_edge(self):
        from wc2026.odds.fetcher import _demo_outright_odds
        from wc2026.odds.value_detector import analyze_champion_market
        outright = _demo_outright_odds()
        stakes = analyze_champion_market(outright, method="shin", min_edge_pct=0.0)
        edges = [s.edge for s in stakes]
        assert edges == sorted(edges, reverse=True)

    def test_total_model_prob_sums_to_one(self):
        """Model champion probabilities should sum to ~1.0."""
        import pandas as pd
        df = pd.read_csv(ROOT / "outputs" / "tournament_run" / "summary.csv")
        total = df["champion_prob"].sum()
        assert abs(total - 1.0) < 0.01, f"Champion prob sum = {total}"
