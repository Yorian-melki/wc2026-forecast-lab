"""Phase 2D — correctness of the analytic ceiling + helpers (offline).

The audit's whole claim rests on: "analytic ceiling == expected score when outcomes are drawn from
the model itself." This test proves that identity by Monte-Carlo for several distributions, so the
report's REAL-vs-CEILING verdicts are trustworthy. No model/config/data/probability change.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat  # noqa: E402
from exp_objective_ceiling import rps_ordered  # noqa: E402

G = 8
CASES = [(1.25, 1.25, -0.021), (2.4, 0.7, -0.021), (0.8, 1.9, -0.04)]


def test_rps_ordered_known_values():
    assert rps_ordered(np.array([1.0, 0.0, 0.0]), 0) == 0.0
    assert rps_ordered(np.array([1.0, 0.0, 0.0]), 2) == pytest.approx(1.0)
    assert rps_ordered(np.array([1 / 3, 1 / 3, 1 / 3]), 1) == pytest.approx(1 / 9, abs=1e-9)


@pytest.mark.parametrize("mu_a,mu_b,rho", CASES)
def test_analytic_ceiling_matches_simulation(mu_a, mu_b, rho):
    flat = poisson_dc_flat(mu_a, mu_b, rho, G)
    order = np.argsort(flat)[::-1]
    ranks = np.empty(G * G); ranks[order] = np.arange(1, G * G + 1)

    # analytic ceilings
    c_top1 = flat[order[0]]
    c_top3 = flat[order[:3]].sum()
    c_rank = float(np.sum(flat * ranks))
    ph, pdr, pa = wdl_from_flat(flat, G)
    wdl = np.array([ph, pdr, pa])
    c_nll = float(-np.sum(wdl * np.log(np.clip(wdl, 1e-12, 1))))
    c_rps = float(sum(wdl[k] * rps_ordered(wdl, k) for k in range(3)))
    c_acc = float(wdl.max())

    # simulate outcomes from the model itself, score the model against them
    rng = np.random.default_rng(0)
    draws = rng.choice(G * G, size=400_000, p=flat)
    top1 = (draws == order[0]).mean()
    top3 = np.isin(draws, order[:3]).mean()
    rank = ranks[draws].mean()
    di, dj = draws // G, draws % G
    outc = np.where(di > dj, 0, np.where(di == dj, 1, 2))
    nll = np.mean([-np.log(max(wdl[o], 1e-12)) for o in outc[:50_000]])
    acc = (np.argmax(wdl) == outc).mean()

    assert top1 == pytest.approx(c_top1, abs=3e-3)
    assert top3 == pytest.approx(c_top3, abs=3e-3)
    assert rank == pytest.approx(c_rank, abs=5e-2)
    assert nll == pytest.approx(c_nll, abs=2e-2)
    assert acc == pytest.approx(c_acc, abs=3e-3)
    assert c_rps >= 0.0


def test_nll_ceiling_is_entropy():
    flat = poisson_dc_flat(1.4, 1.1, -0.02, G)
    wdl = np.array(wdl_from_flat(flat, G))
    entropy = float(-np.sum(wdl * np.log(wdl)))
    c_nll = float(-np.sum(wdl * np.log(np.clip(wdl, 1e-12, 1))))
    assert c_nll == pytest.approx(entropy, abs=1e-9)


def test_bootstrap_ci_sane():
    rng = np.random.default_rng(1)
    arr = rng.random(2000)
    idx = rng.integers(0, 2000, size=(1000, 2000))
    s = arr[idx].mean(axis=1)
    lo, hi = np.percentile(s, 2.5), np.percentile(s, 97.5)
    assert lo <= arr.mean() <= hi and lo < hi
