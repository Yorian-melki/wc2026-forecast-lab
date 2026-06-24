"""Phase 2F — draw-calibrator correctness (offline). No model/config/data/probability change."""
import numpy as np
import pytest

from wc2026.experimental.draw_calibrators import (
    apply_gamma, fit_gamma, rescale_to_draw, IsotonicDrawCalibrator,
)

WDL = np.array([[0.45, 0.25, 0.30], [0.60, 0.20, 0.20], [0.20, 0.30, 0.50]])


def test_gamma_one_is_identity():
    assert np.allclose(apply_gamma(WDL, 1.0), WDL, atol=1e-12)


def test_outputs_normalised():
    for g in (0.7, 1.0, 1.5):
        out = apply_gamma(WDL, g)
        assert np.allclose(out.sum(axis=1), 1.0, atol=1e-12)
        assert (out >= 0).all()


def test_gamma_gt_one_raises_draw_mass():
    out = apply_gamma(WDL, 1.4)
    assert (out[:, 1] > WDL[:, 1] - 1e-9).all()
    assert out[:, 1] == pytest.approx(np.clip(1.4 * WDL[:, 1], 0, 1), abs=1e-9)


def test_rescale_preserves_home_away_ratio():
    out = rescale_to_draw(WDL, np.array([0.4, 0.4, 0.4]))
    for i in range(len(WDL)):
        assert out[i, 0] / out[i, 2] == pytest.approx(WDL[i, 0] / WDL[i, 2], rel=1e-9)


def test_fit_gamma_recovers_underprediction():
    # Construct data where draws happen MORE than predicted -> best gamma should be > 1.
    rng = np.random.default_rng(0)
    base = np.tile([0.45, 0.20, 0.35], (3000, 1))
    # true draw rate 0.30 >> predicted 0.20
    outc = np.where(rng.random(3000) < 0.30, 1, np.where(rng.random(3000) < 0.55, 0, 2))
    g = fit_gamma(base, outc)
    assert g > 1.0


def test_isotonic_is_monotone_and_normalised():
    rng = np.random.default_rng(1)
    p = rng.random(2000) * 0.4
    y = (rng.random(2000) < (0.1 + p)).astype(float)
    iso = IsotonicDrawCalibrator().fit(p, y)
    grid = np.linspace(0.01, 0.45, 50)
    wdl = np.column_stack([(1 - grid) / 2, grid, (1 - grid) / 2])
    out = iso.apply(wdl)
    assert np.allclose(out.sum(1), 1.0, atol=1e-12)
    cal = out[:, 1]
    assert np.all(np.diff(cal) >= -1e-9)   # non-decreasing in predicted draw


def test_isotonic_apply_before_fit_raises():
    with pytest.raises(RuntimeError):
        IsotonicDrawCalibrator().apply(WDL)
