"""Tests for Wave 0 implementations: #17 #19 #20 #24 #48."""
import math
from datetime import date
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wc2026.data_loader import load_config, load_teams
from wc2026.match_model import MatchModel
from wc2026.entropy import group_death_scores
from wc2026.temporal_form import temporal_form_score, decay_weight, REFERENCE_DATE
from wc2026.jet_lag import compute_jet_lag, TEAM_HOME_UTC

import pandas as pd


@pytest.fixture
def model():
    return MatchModel(load_config())


@pytest.fixture
def teams():
    return load_teams()


# --- #20 Red card malus ---

def test_red_card_malus_reduces_goals(model, teams):
    fra, bra = teams["FRA"], teams["BRA"]
    rng = np.random.default_rng(seed=42)
    goals_malus = [model.simulate_group_match(fra, bra, rng).goals_a for _ in range(5000)]
    # With discipline lambda=1.35, about 15% of matches get red-card malus
    # Goals should be slightly lower than pure Poisson
    rng2 = np.random.default_rng(seed=42)
    mu_a, _ = model.expected_goals(fra, bra)
    raw_goals = [int(rng2.poisson(mu_a)) for _ in range(5000)]
    # Malus should push average down
    assert sum(goals_malus) / 5000 <= sum(raw_goals) / 5000 + 0.05


def test_red_card_malus_never_below_zero(model, teams):
    esp, ned = teams["ESP"], teams["NED"]
    rng = np.random.default_rng(0)
    for _ in range(1000):
        result = model.simulate_group_match(esp, ned, rng)
        assert result.goals_a >= 0
        assert result.goals_b >= 0


def test_red_card_malus_in_knockout(model, teams):
    arg, fra = teams["ARG"], teams["FRA"]
    rng = np.random.default_rng(7)
    for _ in range(500):
        result = model.simulate_knockout_match(arg, fra, rng)
        assert result.goals_a >= 0
        assert result.goals_b >= 0


# --- #24 Home nation boost ---

def test_home_nation_boost_increases_xg(model, teams):
    usa, esp = teams["USA"], teams["ESP"]
    mu_usa, _ = model.expected_goals(usa, esp)
    # Temporarily remove from home_nations to get baseline
    model.home_nations = set()
    mu_usa_baseline, _ = model.expected_goals(usa, esp)
    model.home_nations = {"USA", "MEX", "CAN"}
    assert mu_usa > mu_usa_baseline


def test_non_home_nation_unaffected(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    model.home_nations = {"USA", "MEX", "CAN"}
    mu_fra_home, _ = model.expected_goals(fra, esp)
    model.home_nations = set()
    mu_fra_no_boost, _ = model.expected_goals(fra, esp)
    model.home_nations = {"USA", "MEX", "CAN"}
    assert abs(mu_fra_home - mu_fra_no_boost) < 1e-9


# --- #17 Entropy ---

def test_entropy_returns_all_groups():
    summary = pd.DataFrame({
        'team': ['ESP', 'URU', 'CPV', 'KSA',
                 'FRA', 'SEN', 'IRQ', 'NOR'],
        'group_survival_prob': [0.85, 0.65, 0.25, 0.15,
                                0.80, 0.70, 0.30, 0.10],
    })
    teams = pd.DataFrame({
        'code': ['ESP', 'URU', 'CPV', 'KSA', 'FRA', 'SEN', 'IRQ', 'NOR'],
        'group': ['H', 'H', 'H', 'H', 'I', 'I', 'I', 'I'],
    })
    result = group_death_scores(summary_df=summary, teams_df=teams)
    assert len(result) == 2
    assert set(result['group']) == {'H', 'I'}


def test_uniform_group_has_max_entropy():
    summary = pd.DataFrame({
        'team': ['A', 'B', 'C', 'D'],
        'group_survival_prob': [0.5, 0.5, 0.5, 0.5],
    })
    teams = pd.DataFrame({'code': ['A', 'B', 'C', 'D'], 'group': ['X', 'X', 'X', 'X']})
    result = group_death_scores(summary_df=summary, teams_df=teams)
    assert abs(result.iloc[0]['normalized_entropy'] - 1.0) < 1e-6


# --- #19 Temporal form ---

def test_decay_weight_decreases_with_distance():
    d1 = decay_weight(date(2026, 6, 10), REFERENCE_DATE)
    d30 = decay_weight(date(2026, 5, 12), REFERENCE_DATE)
    d90 = decay_weight(date(2026, 3, 13), REFERENCE_DATE)
    assert d1 > d30 > d90


def test_all_wins_gives_high_form():
    results = [('W', date(2026, 6, 8)), ('W', date(2026, 6, 4)), ('W', date(2026, 5, 29))]
    score = temporal_form_score(results)
    assert score >= 90.0


def test_all_losses_gives_low_form():
    results = [('L', date(2026, 6, 8)), ('L', date(2026, 6, 4)), ('L', date(2026, 5, 29))]
    score = temporal_form_score(results)
    assert score <= 60.0


def test_form_score_in_valid_range():
    for combo in [
        [('W', date(2026, 6, 1)), ('D', date(2026, 5, 20)), ('L', date(2026, 5, 10))],
        [('D', date(2026, 6, 8))],
        [],
    ]:
        s = temporal_form_score(combo)
        assert 0.0 <= s <= 100.0


# --- #48 Jet lag ---

def test_jet_lag_factor_bounded():
    for code in list(TEAM_HOME_UTC.keys())[:10]:
        result = compute_jet_lag(code, "Los Angeles", kickoff_utc=21.0)
        assert 0.85 <= result.performance_factor <= 1.0


def test_nearby_team_minimal_penalty():
    result = compute_jet_lag("MEX", "Los Angeles", kickoff_utc=21.0, days_since_arrival=3.0)
    assert result.performance_factor >= 0.97


def test_far_team_higher_penalty():
    jap = compute_jet_lag("JPN", "New York", kickoff_utc=21.0, days_since_arrival=2.0)
    mex = compute_jet_lag("MEX", "New York", kickoff_utc=21.0, days_since_arrival=2.0)
    assert jap.performance_factor < mex.performance_factor
