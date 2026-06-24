"""OFFLINE-ONLY: alternative scoreline distributions for Phase 2B tail experiments.

Builds flat g×g scoreline distributions from expected goals (mu_a, mu_b), mirroring the
PRODUCTION construction in `CalibratedEloMatchModel._build_dc_flat` (independent marginals →
outer product → Dixon-Coles tau correction on the 4 low-score cells → normalise), but allowing
the marginal family to be Poisson (baseline) or Negative-Binomial (fat-tailed).

Key invariant (tested): `negbin_dc_flat(..., r=inf)` == `poisson_dc_flat(...)` == production
`_build_dc_flat(...)`, elementwise, within floating-point tolerance. As the NB dispersion r → ∞,
NB(mean=mu, size=r) → Poisson(mu), so the experiment reduces exactly to the live model at r=∞.

This module is NOT imported by app.py or by the production model. It cannot affect the live site.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np


def _poisson_pmf(mu: float, g: int) -> np.ndarray:
    """Truncated Poisson pmf over k = 0..g-1 (NOT renormalised — matches production)."""
    k = np.arange(g, dtype=np.float64)
    log_fact = np.array([math.lgamma(i + 1) for i in range(g)])
    return np.exp(k * math.log(max(mu, 1e-9)) - mu - log_fact)


def _negbin_pmf(mu: float, r: float, g: int) -> np.ndarray:
    """Truncated Negative-Binomial pmf (mean=mu, dispersion size=r) over k = 0..g-1.

    Variance = mu + mu^2 / r (overdispersed; fatter upper tail than Poisson). r → ∞ ⇒ Poisson.
    """
    if r is None or not math.isfinite(r):
        return _poisson_pmf(mu, g)
    mu = max(mu, 1e-9)
    k = np.arange(g, dtype=np.float64)
    log_p = math.log(r / (r + mu))          # log P(success)
    log_q = math.log(mu / (r + mu))          # log (1 - p)
    gammaln = np.array([math.lgamma(i + r) - math.lgamma(r) - math.lgamma(i + 1) for i in range(g)])
    return np.exp(gammaln + r * log_p + k * log_q)


def _apply_dc_tau(joint: np.ndarray, mu_a: float, mu_b: float, rho: float) -> None:
    """Dixon-Coles low-score correction, in place — identical to production `_build_dc_flat`."""
    if rho != 0.0:
        joint[0, 0] *= max(1.0 - mu_a * mu_b * rho, 1e-9)
        joint[1, 0] *= max(1.0 + mu_b * rho, 1e-9)
        joint[0, 1] *= max(1.0 + mu_a * rho, 1e-9)
        joint[1, 1] *= max(1.0 - rho, 1e-9)


def poisson_dc_flat(mu_a: float, mu_b: float, rho: float, g: int = 8) -> np.ndarray:
    """Production-equivalent independent-Poisson + DC flat scoreline distribution."""
    pa, pb = _poisson_pmf(mu_a, g), _poisson_pmf(mu_b, g)
    joint = np.outer(pa, pb)
    _apply_dc_tau(joint, mu_a, mu_b, rho)
    flat = joint.ravel()
    flat /= flat.sum()
    return flat


def negbin_dc_flat(mu_a: float, mu_b: float, rho: float, r: Optional[float], g: int = 8) -> np.ndarray:
    """Negative-Binomial marginals (dispersion r) + DC flat scoreline distribution.

    r=None or r=inf reproduces `poisson_dc_flat` exactly.
    """
    pa, pb = _negbin_pmf(mu_a, r, g), _negbin_pmf(mu_b, r, g)
    joint = np.outer(pa, pb)
    _apply_dc_tau(joint, mu_a, mu_b, rho)
    flat = joint.ravel()
    flat /= flat.sum()
    return flat


def wdl_from_flat(flat: np.ndarray, g: int = 8) -> tuple[float, float, float]:
    """(P home win, P draw, P away win) from a flat g×g grid (rows = home goals)."""
    idx = np.arange(g * g)
    i, j = idx // g, idx % g
    return float(flat[i > j].sum()), float(flat[i == j].sum()), float(flat[i < j].sum())
