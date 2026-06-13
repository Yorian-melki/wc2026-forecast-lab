from wc2026.data_loader import load_teams
from wc2026.group_rules import PlayedMatch, rank_group


def test_group_rank_respects_points_then_tiebreaks():
    teams = load_teams()
    group_codes = ['ESP', 'CPV', 'KSA', 'URU']
    matches = [
        PlayedMatch('ESP', 'CPV', 1, 0, 1, 2),
        PlayedMatch('KSA', 'URU', 0, 0, 2, 1),
        PlayedMatch('ESP', 'KSA', 1, 1, 1, 1),
        PlayedMatch('URU', 'CPV', 1, 0, 1, 2),
        PlayedMatch('URU', 'ESP', 0, 1, 1, 2),
        PlayedMatch('CPV', 'KSA', 0, 2, 2, 1),
    ]
    order = rank_group(group_codes, matches, teams)
    assert order[0] == 'ESP'
    assert order[-1] == 'CPV'
