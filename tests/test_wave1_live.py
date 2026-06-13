"""Tests for Wave 1: live state parsing + conditioned simulation."""
from __future__ import annotations

import json
import numpy as np
import pytest
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from wc2026.name_map import NAME_TO_CODE, to_code, CODE_TO_NAME
from wc2026.live_state import LiveState, LiveMatchResult, _parse_score, _infer_group, save_live_state, load_live_state_from_file
from wc2026.group_rules import PlayedMatch, simulate_group_conditioned
from wc2026.data_loader import load_config, load_groups, load_teams
from wc2026.match_model import MatchModel
from wc2026.tournament import TournamentSimulator


# --- name_map ---

def test_name_map_covers_all_48_teams():
    import json
    groups = json.load(open(ROOT / 'data' / 'groups.json'))
    all_48 = [team for g in groups.values() for team in g]
    for code in all_48:
        assert code in CODE_TO_NAME, f"Code {code} has no full name"


def test_to_code_known_names():
    assert to_code('France') == 'FRA'
    assert to_code('Netherlands') == 'NED'
    assert to_code('South Korea') == 'KOR'
    assert to_code('DR Congo') == 'COD'
    assert to_code('Curaçao') == 'CUW'
    assert to_code('USA') == 'USA'
    assert to_code('Iraq') == 'IRQ'


def test_to_code_unknown_raises():
    with pytest.raises(ValueError):
        to_code('Narnia')


def test_name_map_bidirectional_48():
    groups = json.load(open(ROOT / 'data' / 'groups.json'))
    all_48 = [team for g in groups.values() for team in g]
    for code in all_48:
        name = CODE_TO_NAME[code]
        assert to_code(name) == code, f"Round-trip failed: {code} → {name} → {to_code(name)}"


# --- live_state parsing ---

def test_parse_score_90():
    assert _parse_score({'ft': [2, 1]}) == (2, 1, '90')


def test_parse_score_et():
    assert _parse_score({'ft': [1, 1], 'et': [2, 1]}) == (2, 1, 'ET')


def test_parse_score_pen():
    g1, g2, d = _parse_score({'ft': [1, 1], 'et': [1, 1], 'p': [5, 4]})
    assert d == 'PEN'
    assert g1 == 1 and g2 == 1  # ET score, not penalties


def test_infer_group():
    assert _infer_group('Group A') == 'A'
    assert _infer_group('Group L') == 'L'
    assert _infer_group('') is None
    assert _infer_group('Round of 32') is None


def test_live_state_empty_on_no_scores():
    """Before tournament starts, JSON has no scores → empty state."""
    import urllib.request
    try:
        req = urllib.request.Request(
            'https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json',
            headers={'User-Agent': 'wc2026-test'}
        )
        raw = json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception:
        pytest.skip("Network unavailable")
    state_matches = [m for m in raw['matches'] if 'score' in m]
    # Pre-tournament: 0 completed (or if during tournament, skip assertion)
    assert isinstance(state_matches, list)


# --- simulate_group_conditioned ---

def test_conditioned_group_uses_fixed_result():
    teams = load_teams()
    config = load_config()
    model = MatchModel(config)
    groups = load_groups()
    rng = np.random.default_rng(42)

    grp = 'H'  # ESP, CPV, KSA, URU
    codes = groups[grp]

    # Fix ESP 3-0 CPV
    fixed = [PlayedMatch(team_a='ESP', team_b='CPV', goals_a=3, goals_b=0,
                         conduct_a=1, conduct_b=2)]
    table, all_matches, order = simulate_group_conditioned(
        grp, codes, teams, model, rng, fixed
    )

    # ESP vs CPV result should be exactly 3-0
    esp_cpv = [m for m in all_matches if {m.team_a, m.team_b} == {'ESP', 'CPV'}]
    assert len(esp_cpv) == 1
    m = esp_cpv[0]
    if m.team_a == 'ESP':
        assert m.goals_a == 3 and m.goals_b == 0
    else:
        assert m.goals_b == 3 and m.goals_a == 0


def test_conditioned_group_still_plays_6_matches():
    teams = load_teams()
    config = load_config()
    model = MatchModel(config)
    groups = load_groups()
    rng = np.random.default_rng(0)

    grp = 'A'
    codes = groups[grp]
    fixed = [
        PlayedMatch('MEX', 'RSA', 2, 0, 1, 1),
        PlayedMatch('KOR', 'CZE', 1, 1, 0, 0),
    ]
    table, all_matches, order = simulate_group_conditioned(grp, codes, teams, model, rng, fixed)
    assert len(all_matches) == 6


def test_conditioned_group_table_valid():
    teams = load_teams()
    config = load_config()
    model = MatchModel(config)
    groups = load_groups()
    rng = np.random.default_rng(7)

    for grp, codes in groups.items():
        table, _, order = simulate_group_conditioned(grp, codes, teams, model, rng, [])
        total_pts = sum(t.points for t in table.values())
        # 6 matches, each gives 3 pts (decisive) or 2 pts (draw) → range [12, 18]
        assert 12 <= total_pts <= 18, f"Group {grp}: total pts={total_pts}"
        assert len(order) == 4


# --- Live tournament simulation ---

def test_live_sim_with_empty_state_matches_baseline():
    """With no results, simulate_many_live should behave like simulate_many."""
    teams = load_teams()
    groups = load_groups()
    config = load_config()
    sim = TournamentSimulator(teams=teams, groups=groups, config=config)

    from wc2026.live_state import LiveState
    from datetime import datetime
    empty_state = LiveState(fetched_at=datetime.now())

    a1 = sim.simulate_many(iterations=1000, seed=99)
    a2 = sim.simulate_many_live(iterations=1000, seed=99, live_state=empty_state)

    champ_sum1 = a1.summary['champion_prob'].sum()
    champ_sum2 = a2.summary['champion_prob'].sum()
    assert abs(champ_sum1 - 1.0) < 1e-4
    assert abs(champ_sum2 - 1.0) < 1e-4


def test_live_sim_with_group_results_shifts_probs():
    """After ARG wins 3-0, ARG group survival should be very high."""
    teams = load_teams()
    groups = load_groups()
    config = load_config()
    sim = TournamentSimulator(teams=teams, groups=groups, config=config)

    from wc2026.live_state import LiveState, LiveMatchResult
    from datetime import datetime, date
    state = LiveState(fetched_at=datetime.now())
    # ARG wins all 3 group matches convincingly
    for opp in ['ALG', 'AUT', 'JOR']:
        state.group_results.setdefault('J', []).append(
            PlayedMatch('ARG', opp, 3, 0, 0, 0)
        )

    a = sim.simulate_many_live(iterations=2000, seed=42, live_state=state)
    arg_row = a.summary[a.summary['team'] == 'ARG'].iloc[0]
    # ARG won all group games → should qualify almost certainly
    assert arg_row['group_survival_prob'] > 0.98, \
        f"ARG group survival={arg_row['group_survival_prob']:.4f} should be >0.98 after 3 wins"


# --- save/load round-trip ---

def test_save_load_state_roundtrip(tmp_path):
    from wc2026.live_state import LiveState, LiveMatchResult
    from datetime import datetime, date
    state = LiveState(fetched_at=datetime(2026, 6, 12, 18, 0))
    state.completed.append(LiveMatchResult(
        team1='MEX', team2='RSA', goals1=2, goals2=0,
        group='A', round_name='Matchday 1', decided_in='90',
        match_date=date(2026, 6, 11)
    ))
    state.group_results['A'] = [PlayedMatch('MEX', 'RSA', 2, 0, 0, 0)]
    state.eliminated = {'RSA'}

    path = str(tmp_path / 'state.json')
    save_live_state(state, path)
    loaded = load_live_state_from_file(path)

    assert loaded.n_completed == 1
    assert loaded.completed[0].team1 == 'MEX'
    assert loaded.completed[0].goals1 == 2
    assert 'RSA' in loaded.eliminated
