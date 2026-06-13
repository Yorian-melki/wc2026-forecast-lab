"""
P3 production validation tests.

Verifies:
1. CalibratedEloMatchModel loads and works correctly
2. Elo signal drives win probability monotonically
3. Probability sums to 1
4. Simulation conservation laws
5. Expert model still functional
6. Full Hybrid NOT promoted to production
7. All comparison outputs exist
8. Public report is honest (forbidden claims absent)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPERT_CSV   = ROOT / "outputs" / "tournament_run" / "expert_summary.csv"
ELO_CSV      = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"
DELTA_CSV    = ROOT / "outputs" / "tournament_run" / "model_delta_summary.csv"
REPORT_MD    = ROOT / "outputs" / "public" / "model_selection_report.md"
CHART_PNG    = ROOT / "outputs" / "public" / "wc2026_model_comparison_chart.png"
ELO_PARAMS   = ROOT / "data" / "elo_calibrated_params.json"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Model loads
# ─────────────────────────────────────────────────────────────────────────────

def test_calibrated_elo_model_imports():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_team_elos


def test_model_factory_imports():
    from wc2026.model_factory import make_match_model, MODEL_NAMES


def test_model_factory_expert_works():
    from wc2026.model_factory import make_match_model
    model = make_match_model("expert")
    assert hasattr(model, "simulate_group_match")
    assert hasattr(model, "simulate_knockout_match")
    assert hasattr(model, "expected_goals")


def test_model_factory_elo_calibrated_works():
    from wc2026.model_factory import make_match_model
    model = make_match_model("elo_calibrated")
    assert hasattr(model, "simulate_group_match")
    assert hasattr(model, "simulate_knockout_match")
    assert hasattr(model, "expected_goals")


def test_model_factory_rejects_hybrid():
    from wc2026.model_factory import make_match_model
    with pytest.raises(ValueError, match="Unknown model"):
        make_match_model("hybrid")


def test_model_factory_rejects_unknown():
    from wc2026.model_factory import make_match_model
    with pytest.raises(ValueError):
        make_match_model("magic_model")


# ─────────────────────────────────────────────────────────────────────────────
# 2. CalibratedEloMatchModel functional tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def elo_model():
    from wc2026.model_factory import make_match_model
    return make_match_model("elo_calibrated")


@pytest.fixture(scope="module")
def two_teams():
    from wc2026.data_loader import load_teams
    teams = load_teams()
    codes = list(teams.keys())
    return teams[codes[0]], teams[codes[1]]


def test_expected_goals_positive(elo_model, two_teams):
    t_a, t_b = two_teams
    mu_a, mu_b = elo_model.expected_goals(t_a, t_b, knockout=False)
    assert mu_a > 0
    assert mu_b > 0
    assert mu_a < 5.0
    assert mu_b < 5.0


def test_expected_goals_knockout_different_from_group(elo_model, two_teams):
    t_a, t_b = two_teams
    mu_g_a, mu_g_b = elo_model.expected_goals(t_a, t_b, knockout=False)
    mu_k_a, mu_k_b = elo_model.expected_goals(t_a, t_b, knockout=True)
    # Knockout intensity multiplier ≠ 1.0 (config: 0.96), so must differ
    assert abs(mu_k_a - mu_g_a) > 1e-6


def test_higher_elo_increases_expected_goals(elo_model):
    """Team with higher Elo should have higher expected goals."""
    from wc2026.data_loader import load_teams
    from dataclasses import replace
    teams = load_teams()
    code_a, code_b = list(teams.keys())[0], list(teams.keys())[1]
    t_a, t_b = teams[code_a], teams[code_b]
    # Set high elo for t_a
    elo_model.team_elos[code_a] = 2200.0
    elo_model.team_elos[code_b] = 1500.0
    mu_strong, mu_weak = elo_model.expected_goals(t_a, t_b)
    elo_model.team_elos[code_a] = 1500.0
    mu_equal_a, mu_equal_b = elo_model.expected_goals(t_a, t_b)
    assert mu_strong > mu_equal_a, "Higher Elo should mean higher expected goals"


def test_simulate_group_match_returns_match_summary(elo_model, two_teams):
    from wc2026.match_model import MatchSummary
    rng = np.random.default_rng(42)
    t_a, t_b = two_teams
    result = elo_model.simulate_group_match(t_a, t_b, rng)
    assert isinstance(result, MatchSummary)
    assert result.goals_a >= 0
    assert result.goals_b >= 0


def test_simulate_knockout_has_winner(elo_model, two_teams):
    from wc2026.match_model import MatchSummary
    rng = np.random.default_rng(123)
    t_a, t_b = two_teams
    # Run 20 times to ensure we always get a winner
    for seed in range(20):
        rng = np.random.default_rng(seed)
        result = elo_model.simulate_knockout_match(t_a, t_b, rng)
        assert result.winner is not None, "Knockout match must always have a winner"
        assert result.winner in (t_a.code, t_b.code)
        assert result.loser is not None


def test_tournament_simulator_accepts_elo_model():
    from wc2026.tournament import TournamentSimulator
    from wc2026.data_loader import load_teams, load_groups, load_config
    from wc2026.model_factory import make_match_model
    teams  = load_teams()
    groups = load_groups()
    config = load_config()
    model  = make_match_model("elo_calibrated", config)
    sim = TournamentSimulator(teams=teams, groups=groups, config=config, model=model)
    assert sim.model is model


# ─────────────────────────────────────────────────────────────────────────────
# 3. Elo params file
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not ELO_PARAMS.exists(), reason="elo_calibrated_params.json not generated")
def test_elo_params_schema():
    d = json.loads(ELO_PARAMS.read_text())
    for key in ["log_base", "beta_elo", "rho", "base_xg", "team_elos"]:
        assert key in d, f"Missing: {key}"


@pytest.mark.skipif(not ELO_PARAMS.exists(), reason="elo_calibrated_params.json not generated")
def test_elo_params_plausible():
    d = json.loads(ELO_PARAMS.read_text())
    assert 0.5 < d["base_xg"] < 2.5, f"base_xg={d['base_xg']} implausible"
    assert 0.0 < d["beta_elo"] < 3.0, f"beta_elo={d['beta_elo']} implausible"
    assert -0.20 <= d["rho"] <= 0.20, f"rho={d['rho']} out of bounds"


@pytest.mark.skipif(not ELO_PARAMS.exists(), reason="elo_calibrated_params.json not generated")
def test_elo_params_covers_48_teams():
    d = json.loads(ELO_PARAMS.read_text())
    from wc2026.data_loader import load_teams
    teams = load_teams()
    for code in teams:
        assert code in d["team_elos"], f"Missing Elo for team {code}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Conservation laws
# ─────────────────────────────────────────────────────────────────────────────

def _check_conservation(df: pd.DataFrame, label: str):
    tol = 0.01
    checks = [
        ("champion", 1.0),
        ("final",    2.0),
        ("sf",       4.0),
        ("qf",       8.0),
        ("group_survival", 32.0),
    ]
    for stage, expected in checks:
        col = f"{stage}_prob"
        actual = df[col].sum()
        assert abs(actual - expected) < tol, (
            f"[{label}] {col} sum={actual:.4f}, expected={expected}"
        )


@pytest.mark.skipif(not EXPERT_CSV.exists(), reason="expert_summary.csv absent")
def test_expert_conservation():
    _check_conservation(pd.read_csv(EXPERT_CSV), "expert")


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo_calibrated_summary.csv absent")
def test_elo_calibrated_conservation():
    _check_conservation(pd.read_csv(ELO_CSV), "elo_calibrated")


@pytest.mark.skipif(not EXPERT_CSV.exists(), reason="expert_summary.csv absent")
def test_expert_champion_probs_positive():
    df = pd.read_csv(EXPERT_CSV)
    assert (df["champion_prob"] > 0).all()


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo_calibrated_summary.csv absent")
def test_elo_champion_probs_non_negative():
    """Some weak teams will have 0 in 100K simulations — non-negative is the correct invariant."""
    df = pd.read_csv(ELO_CSV)
    assert (df["champion_prob"] >= 0).all()
    # Top-6 Elo teams must have non-trivial champion probability
    top6 = df.head(6)
    assert (top6["champion_prob"] > 0.001).all()


@pytest.mark.skipif(not EXPERT_CSV.exists(), reason="expert_summary.csv absent")
def test_expert_has_48_teams():
    df = pd.read_csv(EXPERT_CSV)
    assert len(df) == 48


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo_calibrated_summary.csv absent")
def test_elo_has_48_teams():
    df = pd.read_csv(ELO_CSV)
    assert len(df) == 48


# ─────────────────────────────────────────────────────────────────────────────
# 5. Delta summary
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not DELTA_CSV.exists(), reason="model_delta_summary.csv absent")
def test_delta_summary_schema():
    df = pd.read_csv(DELTA_CSV)
    for col in ["team", "expert_champion_prob", "elo_champion_prob", "delta_pp",
                "expert_rank", "elo_rank", "rank_delta"]:
        assert col in df.columns, f"Missing: {col}"


@pytest.mark.skipif(not DELTA_CSV.exists(), reason="model_delta_summary.csv absent")
def test_delta_summary_has_48_teams():
    df = pd.read_csv(DELTA_CSV)
    assert len(df) == 48


@pytest.mark.skipif(not DELTA_CSV.exists(), reason="model_delta_summary.csv absent")
def test_delta_sum_of_deltas_near_zero():
    """sum(delta_pp) must be ≈ 0 since both models sum to 1."""
    df = pd.read_csv(DELTA_CSV)
    total_delta = df["delta_pp"].sum()
    assert abs(total_delta) < 0.01, f"sum(delta_pp)={total_delta:.4f}, expected ≈ 0"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Full Hybrid NOT in production
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_not_in_match_model():
    """MatchModel must not reference hybrid_params.json or CalibratedHybridMatchModel."""
    src = (ROOT / "src" / "wc2026" / "match_model.py").read_text()
    assert "hybrid_params.json" not in src
    assert "CalibratedHybridMatchModel" not in src


def test_model_factory_only_allows_valid_models():
    from wc2026.model_factory import MODEL_NAMES
    assert "expert" in MODEL_NAMES
    assert "elo_calibrated" in MODEL_NAMES
    assert "hybrid" not in MODEL_NAMES
    assert "full_hybrid" not in MODEL_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# 7. Output files exist
# ─────────────────────────────────────────────────────────────────────────────

def test_expert_summary_exists():
    assert EXPERT_CSV.exists(), "expert_summary.csv absent"


def test_elo_summary_exists():
    assert ELO_CSV.exists(), "elo_calibrated_summary.csv absent"


def test_delta_summary_exists():
    assert DELTA_CSV.exists(), "model_delta_summary.csv absent"


def test_model_selection_report_exists():
    assert REPORT_MD.exists(), "model_selection_report.md absent"


def test_comparison_chart_exists():
    assert CHART_PNG.exists(), "wc2026_model_comparison_chart.png absent"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Public report is honest (forbidden claims absent)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not REPORT_MD.exists(), reason="model_selection_report.md absent")
def test_report_no_forbidden_claims():
    text = REPORT_MD.read_text().lower()
    forbidden = [
        "hedge-fund-grade",
        "beats betting markets",
        "guaranteed edge",
        "ai predicts winner",
        "production betting model",
        "peer-reviewed methodology",
        "fully calibrated",
    ]
    # The "Forbidden" section lists these explicitly — check they're not in body
    # Split at "### Forbidden" to only check body before the explicit list
    body = text.split("### forbidden")[0] if "### forbidden" in text else text
    for phrase in forbidden:
        assert phrase not in body, f"Forbidden claim found in report body: '{phrase}'"


@pytest.mark.skipif(not REPORT_MD.exists(), reason="model_selection_report.md absent")
def test_report_contains_allowed_claims():
    text = REPORT_MD.read_text()
    assert "49,450" in text, "Expected mention of 49,450 matches"
    assert "100,000" in text or "100K" in text, "Expected mention of 100K simulations"
    assert "BORDERLINE_EXPERIMENTAL" in text, "Expected honest P2.5 gate verdict"
    assert "17%" in text, "Expected ECE degradation mention"
