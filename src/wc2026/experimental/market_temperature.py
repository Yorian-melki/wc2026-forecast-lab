"""OFFLINE-ONLY: champion-safe market-blend temperature policy (Phase 3K).

Formalises the Phase 3J finding: a naive market blend over-concentrates champions; re-tempering the
*blended W/D/L* back toward baseline sharpness keeps the directional match-level gain while restoring
champion-safe concentration.

Policy (applied to W/D/L PROBABILITIES, not the scoreline grid — the scoreline grid is then reweighted to
this tempered W/D/L via the production `_reweight_flat_to_wdl`, preserving scoreline/total-goal shape):
    1. blend:    w = (1-alpha)*production + alpha*market           (identity-preserving, alpha<=0.6)
    2. temper:   q = w**S / sum(w**S)                              (S<1 flattens = champion-safe; S=1 none)
Normalisation and class order (home/draw/away) are preserved. NOT imported by app.py / production model.
"""
from __future__ import annotations

import numpy as np

from wc2026.experimental.market_blend import blend_wdl


def apply_temperature(wdl, S: float):
    """Power-temper a probability vector. S<1 flattens (champion-safe), S=1 identity, S>1 sharpens."""
    w = np.clip(np.asarray(wdl, float), 1e-12, None) ** S
    return w / w.sum(axis=-1, keepdims=True)


def champion_safe_blend(prod, market, alpha: float, S: float = 1.0):
    """Blend at alpha (capped identity-preserving), then temper by S. alpha=0,S=1 ⇒ production."""
    return apply_temperature(blend_wdl(prod, market, alpha), S)


def mean_confidence(P) -> float:
    return float(np.asarray(P, float).max(axis=-1).mean())


def fit_temperature_to_conf(blended, target_conf: float, lo: float = 0.2, hi: float = 1.0) -> float:
    """Find S so the tempered blend's mean max-prob == target_conf (e.g. the baseline model confidence).

    Monotone: lower S ⇒ flatter ⇒ lower confidence. Bisection on [lo, hi]. Returns S in [lo, hi].
    """
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if mean_confidence(apply_temperature(blended, mid)) > target_conf:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0
