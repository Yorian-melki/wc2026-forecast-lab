"""Phase 2B — equivalence guarantees for the offline NB scoreline experiment.

Critical invariants:
  1. negbin_dc_flat(r=inf) == poisson_dc_flat (the experiment reduces to Poisson at r=inf).
  2. poisson_dc_flat == production CalibratedEloMatchModel._build_dc_flat (faithful baseline).
  3. larger NB variance than Poisson (fatter tail) for finite r.
All offline; no model/config/data/probability change.
"""
import numpy as np
import pytest

from wc2026.experimental.nb_scoreline import negbin_dc_flat, poisson_dc_flat, wdl_from_flat

G = 8
CASES = [(1.25, 1.25, -0.021), (2.4, 0.7, -0.021), (0.5, 3.1, -0.04), (1.8, 1.1, 0.0)]


@pytest.mark.parametrize("mu_a,mu_b,rho", CASES)
def test_negbin_inf_equals_poisson(mu_a, mu_b, rho):
    nb = negbin_dc_flat(mu_a, mu_b, rho, r=float("inf"), g=G)
    po = poisson_dc_flat(mu_a, mu_b, rho, g=G)
    assert np.allclose(nb, po, atol=1e-12)


@pytest.mark.parametrize("mu_a,mu_b,rho", CASES)
def test_negbin_large_r_approaches_poisson(mu_a, mu_b, rho):
    nb = negbin_dc_flat(mu_a, mu_b, rho, r=1e7, g=G)
    po = poisson_dc_flat(mu_a, mu_b, rho, g=G)
    assert np.allclose(nb, po, atol=1e-4)


@pytest.mark.parametrize("mu_a,mu_b,rho", CASES)
def test_poisson_matches_production_build_dc_flat(mu_a, mu_b, rho):
    # The offline Poisson path must reproduce the live model's scoreline grid exactly.
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
    from wc2026.data_loader import load_config
    params = dict(load_calibrated_params()); params["rho"] = rho
    m = CalibratedEloMatchModel(config=load_config(), params=params)
    prod = m._build_dc_flat(mu_a, mu_b)
    po = poisson_dc_flat(mu_a, mu_b, rho, g=m.dc_max_goals + 1)
    assert np.allclose(prod, po, atol=1e-12)


def test_distributions_normalised():
    flat = negbin_dc_flat(1.25, 1.25, -0.021, r=6.0, g=G)
    assert abs(flat.sum() - 1.0) < 1e-12


def test_negbin_has_fatter_tail_than_poisson():
    # P(home goals >= 4) should be larger under a finite-r NB than under Poisson, same mean.
    nb = negbin_dc_flat(1.6, 1.6, 0.0, r=4.0, g=G)
    po = poisson_dc_flat(1.6, 1.6, 0.0, g=G)
    hi = np.zeros(G * G, dtype=bool)
    idx = np.arange(G * G)
    hi[(idx // G) >= 4] = True
    assert nb[hi].sum() > po[hi].sum()


def test_wdl_sums_to_one():
    h, d, a = wdl_from_flat(negbin_dc_flat(1.2, 0.9, -0.02, r=8.0, g=G), G)
    assert abs(h + d + a - 1.0) < 1e-9
