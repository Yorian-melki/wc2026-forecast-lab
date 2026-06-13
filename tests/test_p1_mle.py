"""
P1 MLE calibration tests.
All must pass before declaring P1 done.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def toy_train() -> pd.DataFrame:
    """Minimal 10-match toy dataset with known structure."""
    rows = [
        ("ARG", "FRA", 3, 0),
        ("FRA", "BRA", 2, 1),
        ("BRA", "ARG", 1, 1),
        ("ESP", "GER", 2, 1),
        ("GER", "ENG", 1, 2),
        ("ENG", "ESP", 0, 1),
        ("ARG", "ESP", 1, 0),
        ("FRA", "GER", 2, 0),
        ("BRA", "ENG", 3, 1),
        ("ARG", "GER", 2, 1),
    ]
    return pd.DataFrame(rows, columns=["home_code", "away_code", "home_goals", "away_goals"]).assign(
        weight=1.0, competition="toy", date="2018-06-15"
    )


@pytest.fixture(scope="module")
def toy_teams() -> list[str]:
    return sorted(["ARG", "BRA", "ENG", "ESP", "FRA", "GER"])


@pytest.fixture(scope="module")
def toy_params(toy_train, toy_teams):
    from wc2026.calibration.dixon_coles_mle import fit_dixon_coles
    return fit_dixon_coles(toy_train, toy_teams, regularization_lambda=0.1, n_restarts=2, verbose=False)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Installation
# ─────────────────────────────────────────────────────────────────────────────

def test_scipy_installed():
    import scipy
    assert scipy.__version__ >= "1.0"


def test_mle_stack():
    import scipy, numpy, pandas
    assert hasattr(scipy.optimize, "minimize")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Dataset module
# ─────────────────────────────────────────────────────────────────────────────

def test_dataset_module_importable():
    from wc2026.calibration.datasets import load_calibration_dataset, _SB_TO_FIFA3
    assert len(_SB_TO_FIFA3) >= 40


def test_sb_name_mapping_covers_all_wc_teams():
    from wc2026.calibration.datasets import _SB_TO_FIFA3
    expected = {
        "Argentina", "Australia", "Belgium", "Brazil", "Cameroon", "Canada",
        "Colombia", "Croatia", "Denmark", "Ecuador", "Egypt", "England",
        "France", "Germany", "Ghana", "Iceland", "Iran", "Japan", "Mexico",
        "Morocco", "Netherlands", "Nigeria", "Panama", "Peru", "Poland",
        "Portugal", "Qatar", "Russia", "Saudi Arabia", "Senegal", "Serbia",
        "South Korea", "Spain", "Sweden", "Switzerland", "Tunisia",
        "United States", "Uruguay", "Wales", "Costa Rica",
    }
    missing = expected - set(_SB_TO_FIFA3.keys())
    assert not missing, f"Missing mappings: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Metrics module
# ─────────────────────────────────────────────────────────────────────────────

def test_nll_perfect_prediction():
    from wc2026.calibration.metrics import negative_log_likelihood
    probs = [(1.0, 0.0, 0.0)]
    outcomes = [0]
    nll = negative_log_likelihood(probs, outcomes)
    assert nll < 1e-6


def test_nll_random_baseline():
    from wc2026.calibration.metrics import negative_log_likelihood
    probs = [(1/3, 1/3, 1/3)] * 100
    outcomes = [0] * 50 + [1] * 30 + [2] * 20
    nll = negative_log_likelihood(probs, outcomes)
    assert abs(nll - math.log(3)) < 0.001


def test_brier_random_baseline():
    from wc2026.calibration.metrics import brier_score_1x2
    probs = [(1/3, 1/3, 1/3)] * 100
    outcomes = [0] * 50 + [1] * 30 + [2] * 20
    brier = brier_score_1x2(probs, outcomes)
    # Random: E[(1-1/3)^2 + (0-1/3)^2 + (0-1/3)^2] = (4/9+1/9+1/9) = 6/9 = 2/3
    assert abs(brier - 2/3) < 0.02


def test_outcome_from_goals():
    from wc2026.calibration.metrics import outcome_from_goals
    assert outcome_from_goals(2, 1) == 0  # home win
    assert outcome_from_goals(1, 1) == 1  # draw
    assert outcome_from_goals(0, 2) == 2  # away win


def test_indep_poisson_probs_sum_to_one():
    from wc2026.calibration.metrics import indep_poisson_probs
    ph, pd_, pa = indep_poisson_probs(1.2, 0.8)
    # Truncated at max_goals=8: miss ~1e-5 probability mass — tolerance 1e-4
    assert abs(ph + pd_ + pa - 1.0) < 1e-4


def test_indep_poisson_favors_stronger_team():
    from wc2026.calibration.metrics import indep_poisson_probs
    ph_strong, _, pa_strong = indep_poisson_probs(2.0, 0.5)  # home dominates
    ph_equal, _, pa_equal = indep_poisson_probs(1.0, 1.0)
    assert ph_strong > pa_strong
    assert abs(ph_equal - pa_equal) < 0.001  # symmetric at equal strength


# ─────────────────────────────────────────────────────────────────────────────
# 4. Dixon-Coles MLE
# ─────────────────────────────────────────────────────────────────────────────

def test_mle_returns_finite_nll(toy_params):
    assert math.isfinite(toy_params.final_nll)
    assert toy_params.final_nll < 1000.0


def test_mle_probabilities_sum_to_one(toy_params):
    for h, a in [("ARG", "FRA"), ("BRA", "GER"), ("ENG", "ESP")]:
        ph, pd_, pa = toy_params.prob_1x2(h, a)
        assert abs(ph + pd_ + pa - 1.0) < 1e-6, f"Probs don't sum to 1 for {h} vs {a}"
        assert ph >= 0 and pd_ >= 0 and pa >= 0


def test_rho_in_bounds(toy_params):
    assert -0.20 <= toy_params.rho <= 0.20


def test_base_xg_positive(toy_params):
    assert 0.05 < toy_params.base_xg < 5.0


def test_attack_identifiability(toy_params):
    """Mean attack must be ~0 (soft constraint satisfied)."""
    mean_atk = sum(toy_params.attack.values()) / len(toy_params.attack)
    assert abs(mean_atk) < 0.1, f"Mean attack = {mean_atk:.4f}, expected ~0"


def test_stronger_attack_increases_xg(toy_params):
    """Team with highest attack should have higher mu when facing same defense."""
    strongest = max(toy_params.attack, key=toy_params.attack.get)
    weakest = max(toy_params.defense, key=toy_params.defense.get)  # worst defense = easiest opponent
    mu_strong, _ = toy_params.expected_goals(strongest, weakest)
    # Compare to a team with negative attack
    weakest_atk = min(toy_params.attack, key=toy_params.attack.get)
    mu_weak, _ = toy_params.expected_goals(weakest_atk, weakest)
    assert mu_strong > mu_weak


def test_stronger_defense_reduces_opponent_xg(toy_params):
    """Team with best defense (lowest value) should concede less."""
    best_def = min(toy_params.defense, key=toy_params.defense.get)  # best defense = hardest to score against
    worst_def = max(toy_params.defense, key=toy_params.defense.get)
    # An average attacker scores more against worst defense
    avg_attacker = "ESP"  # neutral-ish
    _, mu_vs_best = toy_params.expected_goals(avg_attacker, best_def)
    _, mu_vs_worst = toy_params.expected_goals(avg_attacker, worst_def)
    assert mu_vs_worst > mu_vs_best


def test_mle_beats_random_on_toy(toy_train, toy_params):
    from wc2026.calibration.metrics import evaluate_model_on_dataset, random_baseline_probs
    dc_fn = lambda h, a: toy_params.prob_1x2(h, a)
    random_fn = random_baseline_probs
    dc_m = evaluate_model_on_dataset(toy_train, dc_fn)
    rnd_m = evaluate_model_on_dataset(toy_train, random_fn)
    assert dc_m["nll"] < rnd_m["nll"], (
        f"DC NLL {dc_m['nll']:.4f} should beat random {rnd_m['nll']:.4f} on train"
    )


def test_optimize_convergence_toy(toy_train, toy_teams):
    """MLE converges and produces finite NLL on toy dataset.
    Note: with only 10 matches + L2 regularization, NLL may exceed random baseline
    because regularization shrinks params toward zero (uniform). This is expected.
    Convergence on real 64-match WC2018 train is tested via calibrate_mle.py.
    """
    from wc2026.calibration.dixon_coles_mle import fit_dixon_coles
    params = fit_dixon_coles(toy_train, toy_teams, regularization_lambda=0.1, n_restarts=3, verbose=False)
    assert math.isfinite(params.final_nll)
    assert params.final_nll > 0  # NLL is always positive
    assert params.n_teams == 6
    assert len(params.attack) == 6
    assert len(params.defense) == 6


# ─────────────────────────────────────────────────────────────────────────────
# 5. Output files (require calibrate_mle.py to have been run)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not (Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json").exists(),
    reason="mle_params.json not yet generated — run scripts/calibrate_mle.py first",
)
def test_mle_params_json_schema():
    path = Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json"
    d = json.loads(path.read_text())
    assert "params" in d
    assert "team_attack" in d["params"]
    assert "team_defense" in d["params"]
    assert "rho" in d["params"]
    assert "base_xg" in d["params"]
    assert "holdout_metrics" in d
    assert "verdict" in d
    assert "production_candidate" in d["verdict"]


@pytest.mark.skipif(
    not (Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json").exists(),
    reason="mle_params.json not yet generated — run scripts/calibrate_mle.py first",
)
def test_mle_params_json_valid_rho():
    path = Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json"
    d = json.loads(path.read_text())
    rho = d["params"]["rho"]
    assert -0.20 <= rho <= 0.20, f"rho={rho} out of bounds"


@pytest.mark.skipif(
    not (Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json").exists(),
    reason="mle_params.json not yet generated",
)
def test_mle_verdict_is_documented():
    """
    Does not assert DC beats random — it may not on 64 training matches.
    Asserts that the verdict (beats_random, beats_elo_only, production_candidate)
    is honestly documented in mle_params.json.
    With 64 training matches and 40 teams, DC may fail to beat Elo-only — that is
    a valid finding, not a code defect.
    """
    path = Path(__file__).parents[1] / "outputs" / "calibration" / "mle_params.json"
    d = json.loads(path.read_text())
    dc_nll = d["holdout_metrics"]["nll"]
    random_nll = d["baselines"]["random"]["nll"]
    elo_nll = d["baselines"]["elo_only"]["nll"]
    verdict = d["verdict"]
    # Verdict fields must exist and be booleans
    assert isinstance(verdict["beats_random"], bool)
    assert isinstance(verdict["beats_elo_only"], bool)
    assert isinstance(verdict["production_candidate"], bool)
    # Verdict must match actual NLL values
    assert verdict["beats_random"] == (dc_nll < random_nll)
    assert verdict["beats_elo_only"] == (dc_nll < elo_nll)
    # If DC doesn't beat Elo, must not be production candidate
    if not verdict["beats_elo_only"]:
        assert not verdict["production_candidate"], (
            "CRITICAL: mle_params.json claims production_candidate=True but DC does not beat Elo"
        )
