"""OFFLINE-ONLY: draw-probability calibrators for Phase 2F.

Two monotone calibrators that adjust a W/D/L vector's DRAW mass to match observed reality, then
rescale home/away proportionally and renormalise (rank order within home/away preserved):
  A. single multiplicative draw-mass factor gamma (fit by minimising train NLL).
  B. isotonic regression mapping predicted P(draw) -> empirical draw rate (fit on train).

Judged ONLY by proper scores out-of-sample (see scripts/exp_draw_calibration.py). NOT imported by
app.py or the production model — cannot affect the live site.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

EPS = 1e-6


def rescale_to_draw(wdl: np.ndarray, new_draw: np.ndarray) -> np.ndarray:
    """Set the draw mass to `new_draw`, fill the rest with home/away kept in their original ratio.

    wdl: (N,3) array of (home, draw, away), each row sums to 1. Returns a new (N,3), rows sum to 1.
    """
    wdl = np.asarray(wdl, dtype=float)
    nd = np.clip(np.asarray(new_draw, dtype=float), EPS, 1 - EPS)
    non_draw = wdl[:, 0] + wdl[:, 2]
    scale = np.where(non_draw > EPS, (1.0 - nd) / non_draw, 0.0)
    out = np.empty_like(wdl)
    out[:, 0] = wdl[:, 0] * scale
    out[:, 1] = nd
    out[:, 2] = wdl[:, 2] * scale
    return out / out.sum(axis=1, keepdims=True)


# ── Calibrator A: single draw-mass factor gamma ──────────────────────────────
def apply_gamma(wdl: np.ndarray, gamma: float) -> np.ndarray:
    """new_draw = gamma * P(draw) (clipped); home/away rescaled. gamma=1 is the identity."""
    wdl = np.asarray(wdl, dtype=float)
    return rescale_to_draw(wdl, gamma * wdl[:, 1])


def _wdl_nll(wdl: np.ndarray, outcomes: np.ndarray) -> float:
    p = np.clip(wdl[np.arange(len(wdl)), outcomes], 1e-12, 1.0)
    return float(-np.mean(np.log(p)))


def fit_gamma(wdl_train: np.ndarray, outcomes_train: np.ndarray,
              grid: np.ndarray | None = None) -> float:
    """Pick gamma minimising TRAIN W/D/L NLL (a proper score). Returns the best gamma."""
    if grid is None:
        grid = np.round(np.arange(0.70, 1.81, 0.02), 3)
    best_g, best_nll = 1.0, np.inf
    for g in grid:
        nll = _wdl_nll(apply_gamma(wdl_train, g), outcomes_train)
        if nll < best_nll:
            best_nll, best_g = nll, float(g)
    return best_g


# ── Calibrator B: isotonic draw calibration ──────────────────────────────────
class IsotonicDrawCalibrator:
    """Monotone map predicted P(draw) -> calibrated P(draw), fit on (p_draw, is_draw) train pairs."""

    def __init__(self) -> None:
        self._iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._fitted = False

    def fit(self, p_draw_train: np.ndarray, is_draw_train: np.ndarray) -> "IsotonicDrawCalibrator":
        self._iso.fit(np.asarray(p_draw_train, float), np.asarray(is_draw_train, float))
        self._fitted = True
        return self

    def apply(self, wdl: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("IsotonicDrawCalibrator.apply called before fit")
        wdl = np.asarray(wdl, dtype=float)
        cal = self._iso.predict(wdl[:, 1])
        return rescale_to_draw(wdl, cal)
