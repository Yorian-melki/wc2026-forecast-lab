"""Phase 3I — market-blend prototype correctness (offline). No production/app/data/config change."""
import numpy as np
import pytest

from wc2026.experimental.market_blend import (
    blend_wdl, regime_alpha, blend_wdl_regime, reweight_grid_to_wdl, entropy,
)
from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat

PROD = np.array([0.55, 0.25, 0.20])
MKT = np.array([0.40, 0.30, 0.30])


def test_alpha0_is_production_identity():
    assert np.allclose(blend_wdl(PROD, MKT, 0.0), PROD, atol=1e-12)


def test_alpha1_is_market():
    assert np.allclose(blend_wdl(PROD, MKT, 1.0), MKT, atol=1e-12)


def test_blend_normalised_and_convex():
    for a in (0.25, 0.4, 0.6):
        b = blend_wdl(PROD, MKT, a)
        assert abs(b.sum() - 1.0) < 1e-12
        assert (b >= np.minimum(PROD, MKT) - 1e-9).all() and (b <= np.maximum(PROD, MKT) + 1e-9).all()


def test_regime_alpha_bounds_and_monotonicity():
    confident = np.array([[0.90, 0.06, 0.04]])
    uncertain = np.array([[0.36, 0.33, 0.31]])
    a_conf = regime_alpha(confident, cap=0.6)[0]
    a_unc = regime_alpha(uncertain, cap=0.6)[0]
    assert 0.0 <= a_conf <= 0.6 and 0.0 <= a_unc <= 0.6
    assert a_unc > a_conf            # more market weight where model is LESS certain


def test_regime_blend_caps_at_06():
    P = np.array([[0.34, 0.33, 0.33]]); M = np.array([[0.8, 0.1, 0.1]])
    b = blend_wdl_regime(P, M, cap=0.6)
    # blended cannot move more than cap*(M-P) toward market
    assert (np.abs(b - P) <= 0.6 * np.abs(M - P) + 1e-9).all()


@pytest.mark.parametrize("mu_a,mu_b,rho", [(1.4, 1.1, -0.021), (2.2, 0.7, -0.02)])
def test_reweight_matches_production(mu_a, mu_b, rho):
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
    from wc2026.data_loader import load_config
    params = dict(load_calibrated_params()); params["rho"] = rho
    m = CalibratedEloMatchModel(config=load_config(), params=params)
    flat = m._build_dc_flat(mu_a, mu_b)
    target = (0.5, 0.25, 0.25)
    prod = m._reweight_flat_to_wdl(flat, target)
    exp = reweight_grid_to_wdl(flat, target, g=m.dc_max_goals + 1)
    assert np.allclose(prod, exp, atol=1e-12)


def test_reweight_hits_target_wdl():
    flat = poisson_dc_flat(1.5, 1.0, -0.02, 8)
    target = (0.6, 0.2, 0.2)
    out = reweight_grid_to_wdl(flat, target, 8)
    h, d, a = wdl_from_flat(out, 8)
    assert np.allclose([h, d, a], target, atol=1e-9)
