"""Phase 3K — champion-safe temperature policy correctness (offline). No production change."""
import numpy as np

from wc2026.experimental.market_temperature import (
    apply_temperature, champion_safe_blend, fit_temperature_to_conf, mean_confidence,
)

P = np.array([0.55, 0.25, 0.20])
M = np.array([0.78, 0.12, 0.10])


def test_temperature_identity_at_S1():
    assert np.allclose(apply_temperature(P, 1.0), P, atol=1e-12)


def test_temperature_flattens_below_1():
    flat = apply_temperature(P, 0.5)
    assert flat.sum() == np.float64(1.0) or abs(flat.sum() - 1.0) < 1e-12
    assert flat.max() < P.max()          # flatter => lower confidence
    assert flat.argmax() == P.argmax()   # class order preserved


def test_temperature_sharpens_above_1():
    sharp = apply_temperature(P, 2.0)
    assert sharp.max() > P.max()


def test_champion_safe_blend_identity():
    assert np.allclose(champion_safe_blend(P, M, 0.0, 1.0), P, atol=1e-12)


def test_fit_temperature_restores_confidence():
    blended = champion_safe_blend(P[None, :].repeat(50, 0), M[None, :].repeat(50, 0), 0.6, 1.0)
    target = 0.50
    S = fit_temperature_to_conf(blended, target)
    assert 0.2 <= S <= 1.0
    assert abs(mean_confidence(apply_temperature(blended, S)) - target) < 0.01


def test_normalised_2d():
    Q = champion_safe_blend(np.tile(P, (5, 1)), np.tile(M, (5, 1)), 0.4, 0.8)
    assert np.allclose(Q.sum(1), 1.0, atol=1e-12)
