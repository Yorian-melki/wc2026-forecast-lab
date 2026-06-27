"""OFFLINE-ONLY: market-informed W/D/L blend + scoreline-grid reweight (Phase 3I lab prototype).

Pure functions; NOT imported by app.py or the production model — cannot affect live scoring. Implements
the Phase 3H-B design: an identity-preserving capped blend of the production W/D/L with the market no-vig
1X2, and a scoreline-grid reweight equivalent to the production `_reweight_flat_to_wdl` (tested for parity).
"""
from __future__ import annotations

import numpy as np


def blend_wdl(prod, mkt, alpha: float):
    """(1-alpha)*production + alpha*market, renormalised. alpha=0 → production (identity)."""
    prod = np.asarray(prod, float); mkt = np.asarray(mkt, float)
    b = (1.0 - alpha) * prod + alpha * mkt
    s = b.sum(axis=-1, keepdims=True)
    return np.divide(b, s, out=np.full_like(b, 1 / 3), where=s > 0)


def entropy(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1.0)
    return -np.sum(p * np.log(p), axis=-1)


def regime_alpha(prod, cap: float = 0.6, floor: float = 0.0):
    """PROTOTYPE regime-aware alpha: trust the market MORE where the model is LESS certain.

    alpha_eff = cap * (model entropy / log 3)  — clipped to [floor, cap]. A near-uniform (uncertain)
    model approaches `cap` market weight; a confident model gets little. Illustrative, NOT a tuned policy.
    """
    e_norm = entropy(prod) / np.log(3.0)            # in [0, 1]
    return np.clip(cap * e_norm, floor, cap)


def blend_wdl_regime(prod, mkt, cap: float = 0.6):
    a = regime_alpha(prod, cap=cap)[:, None] if np.asarray(prod).ndim == 2 else regime_alpha(prod, cap=cap)
    prod = np.asarray(prod, float); mkt = np.asarray(mkt, float)
    b = (1.0 - a) * prod + a * mkt
    s = b.sum(axis=-1, keepdims=True)
    return np.divide(b, s, out=np.full_like(b, 1 / 3), where=s > 0)


def reweight_grid_to_wdl(flat, target, g: int = 8):
    """Scale each W/D/L region of a flat g×g scoreline grid to `target`, renormalise.

    Equivalent to production `CalibratedEloMatchModel._reweight_flat_to_wdl` (parity-tested): preserves the
    within-region (conditional) scoreline shape and total-goal structure; only the W/D/L mass moves.
    """
    flat = np.asarray(flat, float)
    idx = np.arange(g * g); i, j = idx // g, idx % g
    home, draw, away = i > j, i == j, i < j
    tw, td, tl = target
    out = flat.copy()
    sw, sd, sl = flat[home].sum(), flat[draw].sum(), flat[away].sum()
    if sw > 0:
        out[home] *= tw / sw
    if sd > 0:
        out[draw] *= td / sd
    if sl > 0:
        out[away] *= tl / sl
    t = out.sum()
    return out / t if t > 0 else flat
