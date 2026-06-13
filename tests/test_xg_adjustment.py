"""Tests for bounded live xG adjustment (Phase 3)."""
import json
import math
from pathlib import Path

import pytest

from wc2026.xg_adjustment import (
    XGAdjustmentConfig,
    compute_xg_delta,
    explain_xg_delta,
)

ROOT = Path(__file__).resolve().parent.parent
CFG = XGAdjustmentConfig()  # defaults: weight=6.0, cap=8.0


# ── Known WC2026 matches (Highlightly xG) ────────────────────────────────────

@pytest.mark.parametrize("hg,ag,xgh,xga,expected", [
    (2, 0, 1.46, 0.07, 6.0 * (1.39 - 2)),    # MEX 2-0 RSA -> -3.66
    (2, 1, 2.30, 0.83, 6.0 * (1.47 - 1)),    # KOR 2-1 CZE -> +2.82
    (1, 1, 1.23, 0.96, 6.0 * (0.27 - 0)),    # CAN 1-1 BIH -> +1.62
])
def test_known_uncapped_matches(hg, ag, xgh, xga, expected):
    got = compute_xg_delta(hg, ag, xgh, xga, CFG)
    assert got == pytest.approx(expected, abs=1e-6)


def test_usa_par_saturates_cap():
    # score margin +3, xg margin +0.88 -> raw -12.72 -> capped at -8.0
    got = compute_xg_delta(4, 1, 1.42, 0.54, CFG)
    assert got == pytest.approx(-8.0, abs=1e-9)


# ── Bounds ───────────────────────────────────────────────────────────────────

def test_never_exceeds_cap_positive():
    got = compute_xg_delta(0, 5, 3.0, 0.0, CFG)  # huge positive perf gap
    assert got == pytest.approx(CFG.max_abs_delta)


def test_never_exceeds_cap_negative():
    got = compute_xg_delta(5, 0, 0.0, 3.0, CFG)  # huge negative perf gap
    assert got == pytest.approx(-CFG.max_abs_delta)


def test_within_bounds_always():
    for hg in range(0, 6):
        for ag in range(0, 6):
            d = compute_xg_delta(hg, ag, 2.5, 0.1, CFG)
            assert -CFG.max_abs_delta <= d <= CFG.max_abs_delta


# ── Direction semantics ──────────────────────────────────────────────────────

def test_overperformance_reduces_home_gain():
    # scored more than xG warranted -> negative correction
    assert compute_xg_delta(3, 0, 1.0, 0.5, CFG) < 0


def test_underperformance_boosts_home():
    # created more than scored -> positive correction
    assert compute_xg_delta(1, 1, 2.0, 0.5, CFG) > 0


def test_exact_match_zero_correction():
    # xg margin == score margin -> zero
    assert compute_xg_delta(1, 0, 1.5, 0.5, CFG) == pytest.approx(0.0)


# ── Missing xG / disabled ────────────────────────────────────────────────────

def test_missing_xg_returns_zero():
    assert compute_xg_delta(2, 0, None, 0.5, CFG) == 0.0
    assert compute_xg_delta(2, 0, 1.5, None, CFG) == 0.0
    assert compute_xg_delta(2, 0, None, None, CFG) == 0.0


def test_disabled_returns_zero():
    cfg = XGAdjustmentConfig(enabled=False)
    assert compute_xg_delta(4, 1, 1.42, 0.54, cfg) == 0.0


# ── Config loading ───────────────────────────────────────────────────────────

def test_config_loads_from_file():
    cfg = XGAdjustmentConfig.from_file(ROOT / "data" / "xg_adjustment_config.json")
    assert cfg.enabled is True
    assert cfg.weight_per_xg_margin == 6.0
    assert cfg.max_abs_delta == 8.0
    assert cfg.do_not_modify_beta_elo is True


def test_config_file_does_not_touch_beta_elo():
    raw = json.loads((ROOT / "data" / "xg_adjustment_config.json").read_text())
    # The config must never carry a beta_elo override key
    assert "beta_elo" not in raw
    assert raw["do_not_modify_beta_elo"] is True


# ── explain record ───────────────────────────────────────────────────────────

def test_explain_record_fields():
    rec = explain_xg_delta("USA", "PAR", 4, 1, 1.42, 0.54, CFG)
    assert rec["capped"] is True
    assert rec["direction"] == "home_gain_reduced"
    assert rec["has_xg"] is True
    assert rec["xg_delta_elo"] == pytest.approx(-8.0)


def test_explain_missing_xg():
    rec = explain_xg_delta("AAA", "BBB", 1, 0, None, None, CFG)
    assert rec["has_xg"] is False
    assert rec["xg_delta_elo"] == 0.0
    assert rec["direction"] == "no_change"


# ── Audit artifact (if generated) ────────────────────────────────────────────

def test_audit_guardrail_passed_if_present():
    p = ROOT / "outputs" / "audit" / "xg_adjustment_audit.json"
    if not p.exists():
        pytest.skip("xg_adjustment_audit.json not generated yet")
    audit = json.loads(p.read_text())
    # The committed config must keep the adjustment within the guardrail.
    assert audit["guardrail_passed"] is True
    assert audit["max_champion_move_pp"] <= audit["guardrail_pp"]
