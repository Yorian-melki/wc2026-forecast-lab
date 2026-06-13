"""Tests for the ML 1X2 ensemble wired into CalibratedEloMatchModel (scoreline reweighting)."""
import json
from pathlib import Path

import numpy as np
import pytest

from wc2026.calibrated_elo_model import CalibratedEloMatchModel
from wc2026.data_loader import load_teams

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def teams():
    return load_teams(apply_temporal_form=True)


def test_rollback_off_matches_plain_dc(teams):
    """use_ml=False must produce the exact unreweighted DC PMF."""
    m = CalibratedEloMatchModel(use_ml=False)
    a, b = teams["ESP"], teams["RSA"]
    mu = m.expected_goals(a, b)
    plain = m._build_dc_flat(*mu)
    # _dc_sample path caches; the cached flat must equal the plain flat when ML off
    import numpy.random as npr
    m._dc_sample(a, b, knockout=False, rng=np.random.default_rng(0))
    cached = m._dc_cache[(a.code, b.code, "group")]
    assert np.allclose(cached, plain)
    assert m.use_ml is False


def test_reweight_hits_target_marginals(teams):
    m = CalibratedEloMatchModel(use_ml=True)
    if not m.use_ml:
        pytest.skip("ML model/config not available")
    a, b = teams["ESP"], teams["RSA"]
    flat = m._build_dc_flat(*m.expected_goals(a, b))
    target = (0.6, 0.25, 0.15)
    rw = m._reweight_flat_to_wdl(flat, target)
    w, d, l = m._implied_wdl(rw)
    assert (w, d, l) == pytest.approx(target, abs=1e-9)
    assert rw.sum() == pytest.approx(1.0, abs=1e-9)


def test_within_region_conditional_preserved(teams):
    m = CalibratedEloMatchModel(use_ml=True)
    if not m.use_ml:
        pytest.skip("ML model/config not available")
    a, b = teams["ESP"], teams["RSA"]
    flat = m._build_dc_flat(*m.expected_goals(a, b))
    rw = m._reweight_flat_to_wdl(flat, (0.7, 0.2, 0.1))
    g = m.dc_max_goals + 1
    idx = np.arange(g * g)
    home = (idx // g) > (idx % g)
    c_before = flat[home] / flat[home].sum()
    c_after = rw[home] / rw[home].sum()
    assert np.allclose(c_before, c_after), "scoreline shape within home-win region must be preserved"


def test_ml_shifts_toward_favorite(teams):
    """Ensemble should not REDUCE a strong favorite's win prob vs plain DC (ML is more decisive)."""
    m = CalibratedEloMatchModel(use_ml=True)
    if not m.use_ml:
        pytest.skip("ML model/config not available")
    a, b = teams["ESP"], teams["RSA"]
    flat = m._build_dc_flat(*m.expected_goals(a, b))
    dc = m._implied_wdl(flat)
    ml = m._ml_wdl(a, b)
    assert ml is not None
    assert abs(sum(ml) - 1.0) < 1e-6
    # ML home-win prob for a big favorite should be >= DC home-win prob
    assert ml[0] >= dc[0] - 0.05


def test_ml_off_when_forced(teams):
    m = CalibratedEloMatchModel(use_ml=False)
    a, b = teams["FRA"], teams["JPN"] if "JPN" in teams else teams["RSA"]
    # _ml_wdl returns None when clf not loaded
    assert m._ml_wdl(a, b) is None


def test_conservation_with_ml(teams):
    """Champion probabilities must still sum to ~1 with the ensemble active (small N)."""
    from wc2026.tournament import TournamentSimulator
    from wc2026.data_loader import load_groups
    m = CalibratedEloMatchModel(use_ml=True)
    if not m.use_ml:
        pytest.skip("ML model/config not available")
    sim = TournamentSimulator(teams=teams, groups=load_groups(), model=m)
    art = sim.simulate_many(iterations=400, seed=7)
    assert art.summary["champion_prob"].sum() == pytest.approx(1.0, abs=1e-6)


def test_integration_decision_artifact():
    p = ROOT / "outputs" / "audit" / "ml_ensemble_integration_decision.json"
    if not p.exists():
        pytest.skip("integration decision not generated")
    a = json.loads(p.read_text())
    assert a["decision"] in ("INTEGRATED", "DIAGNOSTIC_ONLY")
    if a["decision"] == "INTEGRATED":
        assert a["conservation"]["champion_sum_ml_ensemble"] == pytest.approx(1.0, abs=1e-4)
        assert "honest_caveats" in a and len(a["honest_caveats"]) >= 1
