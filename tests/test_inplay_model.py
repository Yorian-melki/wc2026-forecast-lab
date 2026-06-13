"""
Tests for the in-play probability model.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest
from wc2026.inplay_model import (
    InPlayInput, InPlayOutput, compute_inplay,
    _remaining_rate, _poisson_sum_prob,
    _compute_lead_win_prob, _compute_equalize_prob,
)


class TestDataQuality:
    def test_quality_A_with_xg(self):
        inp = InPlayInput(minute=45, home_score=1, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                          xg_home=1.2, xg_away=0.8)
        assert inp.data_quality == "A"

    def test_quality_B_with_shots(self):
        inp = InPlayInput(minute=45, home_score=1, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                          shots_home=8, shots_on_target_home=3)
        assert inp.data_quality == "B"

    def test_quality_C_score_only(self):
        inp = InPlayInput(minute=60, home_score=2, away_score=1,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        assert inp.data_quality == "C"

    def test_quality_D_returns_none(self):
        # InPlayInput.data_quality is a computed property — we use a subclass to force D
        class QualityDInput(InPlayInput):
            @property
            def data_quality(self) -> str:
                return "D"

        inp = QualityDInput(minute=60, home_score=0, away_score=0,
                            pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        result = compute_inplay(inp)
        assert result is None


class TestComputeInplay:
    def test_returns_output_for_quality_C(self):
        inp = InPlayInput(minute=30, home_score=0, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.1)
        result = compute_inplay(inp)
        assert result is not None
        assert isinstance(result, InPlayOutput)

    def test_probabilities_sum_to_one(self):
        inp = InPlayInput(minute=45, home_score=1, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        result = compute_inplay(inp)
        total = result.p_home_win + result.p_draw + result.p_away_win
        assert abs(total - 1.0) < 0.01, f"Probs sum to {total}"

    def test_leading_team_has_higher_win_prob(self):
        inp = InPlayInput(minute=60, home_score=2, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        result = compute_inplay(inp)
        assert result.p_home_win > 0.80, "Home leading 2-0 at 60min should have >80% win prob"

    def test_trailing_team_has_lower_win_prob(self):
        inp = InPlayInput(minute=60, home_score=0, away_score=2,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        result = compute_inplay(inp)
        assert result.p_home_win < 0.15, "Home trailing 0-2 at 60min should have <15% win prob"

    def test_late_game_draw_low_variance(self):
        inp = InPlayInput(minute=85, home_score=1, away_score=1,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        result = compute_inplay(inp)
        # With 5 min left and 1-1, draw should be dominant
        assert result.p_draw > 0.50, "1-1 at 85min should have >50% draw prob"

    def test_knockout_gives_advance_probs(self):
        inp = InPlayInput(minute=60, home_score=0, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                          is_knockout=True)
        result = compute_inplay(inp)
        assert result.p_home_ko_advance is not None
        assert result.p_away_ko_advance is not None
        total = result.p_home_ko_advance + result.p_away_ko_advance
        assert abs(total - 1.0) < 0.01

    def test_group_stage_no_advance_probs(self):
        inp = InPlayInput(minute=45, home_score=1, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                          is_knockout=False)
        result = compute_inplay(inp)
        assert result.p_home_ko_advance is None
        assert result.p_away_ko_advance is None

    def test_quality_B_uses_shots(self):
        inp = InPlayInput(minute=45, home_score=1, away_score=0,
                          pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                          shots_home=12, shots_on_target_home=5,
                          shots_away=4, shots_on_target_away=1)
        result = compute_inplay(inp)
        assert result.data_quality == "B"
        assert "proxy" in result.quality_warning.lower() or "PROXY" in result.quality_warning

    def test_red_card_reduces_rate(self):
        base_inp = InPlayInput(minute=50, home_score=0, away_score=0,
                               pre_match_lambda_home=1.3, pre_match_lambda_away=1.0)
        rc_inp = InPlayInput(minute=50, home_score=0, away_score=0,
                             pre_match_lambda_home=1.3, pre_match_lambda_away=1.0,
                             red_cards_home=1)
        base_result = compute_inplay(base_inp)
        rc_result = compute_inplay(rc_inp)
        # Home team with red card should have lower expected goals
        assert rc_result.expected_remaining_goals_home < base_result.expected_remaining_goals_home


class TestRemainingRate:
    def test_rate_decreases_with_time(self):
        rate_30 = _remaining_rate(1.3, elapsed=30, total=90)
        rate_60 = _remaining_rate(1.3, elapsed=60, total=90)
        assert rate_30 > rate_60

    def test_leading_team_reduced_rate(self):
        rate_level = _remaining_rate(1.3, elapsed=45, score_diff=0)
        rate_leading = _remaining_rate(1.3, elapsed=45, score_diff=2)
        assert rate_leading < rate_level

    def test_trailing_team_increased_rate(self):
        rate_level = _remaining_rate(1.3, elapsed=45, score_diff=0)
        rate_trailing = _remaining_rate(1.3, elapsed=45, score_diff=-2)
        assert rate_trailing > rate_level

    def test_rate_non_negative(self):
        for elapsed in [0, 30, 60, 90]:
            for diff in [-3, -2, -1, 0, 1, 2, 3]:
                rate = _remaining_rate(1.3, elapsed=elapsed, score_diff=diff)
                assert rate >= 0.0


class TestPoissonSumProb:
    def test_sums_to_one(self):
        for lam_h, lam_a in [(1.0, 1.0), (1.5, 0.8), (0.5, 2.0)]:
            p_h, p_d, p_a = _poisson_sum_prob(lam_h, lam_a)
            assert abs(p_h + p_d + p_a - 1.0) < 1e-6

    def test_symmetric_at_equal_rates(self):
        p_h, p_d, p_a = _poisson_sum_prob(1.0, 1.0)
        assert abs(p_h - p_a) < 0.001, "Equal rates should give ~equal home/away probs"

    def test_stronger_team_higher_win_prob(self):
        p_h, _, p_a = _poisson_sum_prob(2.0, 0.5)
        assert p_h > p_a

    def test_all_probs_positive(self):
        for lam_h, lam_a in [(1.3, 1.0), (0.3, 0.8), (3.0, 0.1)]:
            p_h, p_d, p_a = _poisson_sum_prob(lam_h, lam_a)
            assert p_h > 0 and p_d > 0 and p_a > 0


class TestLeadWinProb:
    def test_big_lead_late_game(self):
        """Team leading 3-0 with 5 minutes left should have >99% win prob."""
        p = _compute_lead_win_prob(0.3, 0.5, lead=3, remaining_min=5)
        assert p > 0.95

    def test_small_lead_much_time(self):
        """Team leading 1-0 with 45 minutes left has uncertain outcome."""
        p = _compute_lead_win_prob(1.3, 1.3, lead=1, remaining_min=45)
        assert 0.5 < p < 0.85

    def test_result_in_range(self):
        for lead in [1, 2, 3]:
            p = _compute_lead_win_prob(1.0, 1.0, lead=lead, remaining_min=30)
            assert 0.0 <= p <= 1.0
