"""Tests for the Forecast Uncertainty & Robustness engine (Batch A–D)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "outputs" / "audit"
LIVE = ROOT / "data" / "live"


# ── A: champion probability intervals ────────────────────────────────────────

def test_champion_intervals_ordered():
    p = LIVE / "champion_probability_intervals.json"
    if not p.exists():
        pytest.skip("intervals not generated")
    d = json.loads(p.read_text())
    assert d["beta"]["p5"] <= d["beta"]["p50"] <= d["beta"]["p95"]
    for team, iv in d["intervals"].items():
        assert iv["low"] <= iv["base"] <= iv["high"], f"{team} interval not ordered"
        assert 0.0 <= iv["low"] and iv["high"] <= 1.0


def test_intervals_csv_ordered():
    import csv
    p = AUDIT / "champion_probability_intervals.csv"
    if not p.exists():
        pytest.skip("intervals csv not generated")
    with open(p) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        assert float(r["p_low"]) <= float(r["p_base"]) <= float(r["p_high"])


def test_beta_bootstrap_artifact():
    p = AUDIT / "beta_uncertainty_bootstrap.json"
    if not p.exists():
        pytest.skip("beta bootstrap not generated")
    d = json.loads(p.read_text())
    bb = d["beta_bootstrap"]
    assert bb["p5"] < bb["p95"]
    assert bb["se"] > 0
    # honest caveat about sampling vs sensitivity must be present
    assert any("stress test" in c.lower() or "lower bound" in c.lower() for c in d["honest_caveats"])


# ── C: dynamic ML weighting ──────────────────────────────────────────────────

def test_dynamic_weight_decays_with_gap():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    from wc2026.data_loader import load_teams
    teams = load_teams(apply_temporal_form=True)
    import pickle
    mp = ROOT / "outputs" / "models" / "ml_match_model.pkl"
    if not mp.exists():
        pytest.skip("ml model not present")
    clf = pickle.loads(mp.read_bytes())
    m = CalibratedEloMatchModel(use_ml=False)
    m.set_ml_ensemble(clf, 0.20, mode="dynamic", gap_scale=300.0)
    # a big-gap pair must get LESS effective ML weight than a near-even pair
    strong, weak = teams["ESP"], teams["RSA"]
    even_a, even_b = teams["ESP"], teams["ARG"]
    w_big = m._effective_ml_weight(strong, weak)
    w_even = m._effective_ml_weight(even_a, even_b)
    assert w_big < w_even <= 0.20
    assert w_big > 0


def test_fixed_mode_constant_weight():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    from wc2026.data_loader import load_teams
    teams = load_teams(apply_temporal_form=True)
    import pickle
    mp = ROOT / "outputs" / "models" / "ml_match_model.pkl"
    if not mp.exists():
        pytest.skip("ml model not present")
    clf = pickle.loads(mp.read_bytes())
    m = CalibratedEloMatchModel(use_ml=False)
    m.set_ml_ensemble(clf, 0.20, mode="fixed")
    assert m._effective_ml_weight(teams["ESP"], teams["RSA"]) == pytest.approx(0.20)
    assert m._effective_ml_weight(teams["ESP"], teams["ARG"]) == pytest.approx(0.20)


def test_dynamic_does_not_break_rollback():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    m = CalibratedEloMatchModel(use_ml=False)
    m.set_ml_ensemble(None, 0.0, mode="dynamic")
    assert m.use_ml is False


def test_upset_robust_decision_artifact():
    p = AUDIT / "upset_robust_ml_weighting.json"
    if not p.exists():
        pytest.skip("not generated")
    d = json.loads(p.read_text())
    assert d["decision"] in ("ADOPT_DYNAMIC", "KEEP_FIXED")
    assert "fixed_0.20" in d["worst_case_regret_vs_elo"]


# ── B: expanded validation ───────────────────────────────────────────────────

def test_expanded_validation_artifact():
    p = AUDIT / "expanded_tournament_validation.json"
    if not p.exists():
        pytest.skip("not generated")
    d = json.loads(p.read_text())
    # at least the 2 original WCs accepted; rejects must carry a reason
    assert len(d["accepted_tournaments"]) >= 2
    for r in d["rejected_tournaments"]:
        assert "reason" in r and r["reason"]


# ── D: market disagreement flags ─────────────────────────────────────────────

def test_market_flags_well_formed():
    p = LIVE / "market_disagreement_flags.json"
    if not p.exists():
        pytest.skip("not generated")
    d = json.loads(p.read_text())
    valid = {"agree", "model_more_confident", "model_underprices_team", "market_unavailable"}
    for f in d["flags"]:
        assert f["class"] in valid


# ── conservation still holds with production config ──────────────────────────

def test_conservation_production_config():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    from wc2026.tournament import TournamentSimulator
    from wc2026.data_loader import load_teams, load_groups
    m = CalibratedEloMatchModel(use_ml=None)  # production config
    sim = TournamentSimulator(teams=load_teams(apply_temporal_form=True), groups=load_groups(), model=m)
    art = sim.simulate_many(iterations=400, seed=11)
    assert art.summary["champion_prob"].sum() == pytest.approx(1.0, abs=1e-6)
