from wc2026.data_loader import load_config, load_teams
from wc2026.match_model import MatchModel


def test_pairwise_probabilities_sum():
    teams = load_teams()
    model = MatchModel(load_config())
    result = model.simulate_pairwise_monte_carlo(teams['ESP'], teams['FRA'], iterations=5000, seed=1, batch_size=1000)
    assert abs(result['group_win_a'] + result['group_draw'] + result['group_win_b'] - 1.0) < 1e-9
    assert abs(result['ko_advance_a'] + result['ko_advance_b'] - 1.0) < 1e-9
