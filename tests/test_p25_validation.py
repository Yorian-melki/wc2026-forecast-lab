"""
P2.5 validation tests — ablation proof, calibration curve, significance, production gate v2.

These tests verify:
1. All output files exist and have correct schema
2. Significance report is honest (no inflation of weak results)
3. Production gate v2 is consistent with ablation data
4. No production integration happened (MatchModel unchanged)
5. Calibration artifacts are complete
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "outputs" / "calibration"

ABLATION_CSV     = OUT / "ablation_results.csv"
ABLATION_MD      = OUT / "ablation_summary.md"
BUCKETS_CSV      = OUT / "reliability_buckets.csv"
CALIB_CURVE_PNG  = OUT / "calibration_curve.png"
SIG_CSV          = OUT / "significance_report.csv"
GATE_V2_JSON     = OUT / "production_gate_v2.json"

# ─────────────────────────────────────────────────────────────────────────────
# 1. File existence
# ─────────────────────────────────────────────────────────────────────────────

def test_ablation_csv_exists():
    assert ABLATION_CSV.exists(), "ablation_results.csv not generated"


def test_ablation_summary_exists():
    assert ABLATION_MD.exists(), "ablation_summary.md not generated"


def test_calibration_curve_exists():
    assert CALIB_CURVE_PNG.exists(), "calibration_curve.png not generated"


def test_significance_report_exists():
    assert SIG_CSV.exists(), "significance_report.csv not generated"


def test_production_gate_v2_exists():
    assert GATE_V2_JSON.exists(), "production_gate_v2.json not generated"


def test_reliability_buckets_exists():
    assert BUCKETS_CSV.exists(), "reliability_buckets.csv not generated"


# ─────────────────────────────────────────────────────────────────────────────
# 2. ablation_results.csv schema + data sanity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_ablation_schema():
    df = pd.read_csv(ABLATION_CSV)
    required_cols = [
        "split", "n_train", "n_test",
        "A_random_nll", "B_empirical_nll",
        "C_elo_nohome_nll", "D_elo_home_nll",
        "E_elo_calib_nll", "F_indep_poisson_nll",
        "G_elo_dc_rho_nll", "H_hybrid_norho_nll",
        "I_hybrid_full_nll",
        "E_elo_calib_ece", "I_hybrid_full_ece",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_ablation_has_4_splits():
    df = pd.read_csv(ABLATION_CSV)
    assert len(df) == 4, f"Expected 4 splits, got {len(df)}"


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_ablation_nll_values_finite():
    df = pd.read_csv(ABLATION_CSV)
    nll_cols = [c for c in df.columns if c.endswith("_nll")]
    for col in nll_cols:
        assert df[col].notna().all(), f"NaN in {col}"
        assert (df[col] > 0).all(), f"Negative NLL in {col}"
        assert (df[col] < 5.0).all(), f"Implausibly large NLL in {col}"


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_random_nll_is_log3():
    """Random baseline must be log(3) ≈ 1.0986."""
    import math
    df = pd.read_csv(ABLATION_CSV)
    for v in df["A_random_nll"]:
        assert abs(v - math.log(3)) < 0.01, f"Random NLL {v} deviates from log(3)"


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_elo_beats_random():
    """Elo must always beat random in average NLL."""
    df = pd.read_csv(ABLATION_CSV)
    assert df["D_elo_home_nll"].mean() < df["A_random_nll"].mean()


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_elo_home_beats_elo_nohome():
    """Home advantage adds signal: D must beat C on average."""
    df = pd.read_csv(ABLATION_CSV)
    assert df["D_elo_home_nll"].mean() < df["C_elo_nohome_nll"].mean()


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_beta_elo_stable():
    """beta_elo coefficient of variation must be < 30% across splits (stable signal)."""
    import numpy as np
    df = pd.read_csv(ABLATION_CSV)
    betas = df["I_hybrid_full_beta_elo"].dropna()
    if len(betas) >= 2:
        cv = float(betas.std() / max(betas.mean(), 1e-6))
        assert cv < 0.30, f"beta_elo unstable across splits: CV={cv:.3f}"


@pytest.mark.skipif(not ABLATION_CSV.exists(), reason="ablation_results.csv absent")
def test_rho_not_at_boundary():
    """rho must not be stuck at ±0.20 (model has room to calibrate DC correction)."""
    df = pd.read_csv(ABLATION_CSV)
    for rho in df["I_hybrid_full_rho"].dropna():
        assert abs(rho) < 0.199, f"rho hit boundary: {rho}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. significance_report.csv — honest reporting
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not SIG_CSV.exists(), reason="significance_report.csv absent")
def test_significance_schema():
    df = pd.read_csv(SIG_CSV)
    for col in ["split","n_test","model_a","model_b","nll_a","nll_b",
                "delta_nll","approx_se","z_score","verdict","note"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not SIG_CSV.exists(), reason="significance_report.csv absent")
def test_significance_wc2022_not_overclaimed():
    """WC2022 holdout has n=64 → SE ≈ 0.079; any |Δ| < 0.05 must be 'tie'."""
    df = pd.read_csv(SIG_CSV)
    wc = df[df["split"].str.contains("wc2022")]
    for _, row in wc.iterrows():
        if abs(row["delta_nll"]) < 0.05:
            assert row["verdict"] == "tie", (
                f"WC2022 holdout Δ={row['delta_nll']:.4f} on n=64 "
                f"claimed as '{row['verdict']}' — should be 'tie' (noise floor too high)"
            )


@pytest.mark.skipif(not SIG_CSV.exists(), reason="significance_report.csv absent")
def test_significance_verdicts_valid():
    df = pd.read_csv(SIG_CSV)
    valid = {"clear_win", "marginal_win", "tie", "loss"}
    for v in df["verdict"]:
        assert v in valid, f"Unknown verdict: {v}"


@pytest.mark.skipif(not SIG_CSV.exists(), reason="significance_report.csv absent")
def test_z_score_consistent_with_verdict():
    """Verify z_score brackets match verdict labels."""
    df = pd.read_csv(SIG_CSV)
    for _, row in df.iterrows():
        z = row["z_score"]
        v = row["verdict"]
        if z >= 2.0:
            assert v == "clear_win", f"z={z:.2f} but verdict={v}"
        elif z >= 0.5:
            assert v == "marginal_win", f"z={z:.2f} but verdict={v}"
        elif z >= -0.5:
            assert v == "tie", f"z={z:.2f} but verdict={v}"
        else:
            assert v == "loss", f"z={z:.2f} but verdict={v}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. reliability_buckets.csv
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not BUCKETS_CSV.exists(), reason="reliability_buckets.csv absent")
def test_reliability_buckets_schema():
    df = pd.read_csv(BUCKETS_CSV)
    for col in ["model","split","bucket_min","bucket_max",
                "predicted_mean","observed_frequency","count","abs_error"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not BUCKETS_CSV.exists(), reason="reliability_buckets.csv absent")
def test_reliability_buckets_both_models():
    df = pd.read_csv(BUCKETS_CSV)
    models = set(df["model"].unique())
    assert "elo_calib" in models, "elo_calib missing from reliability buckets"
    assert "hybrid" in models, "hybrid missing from reliability buckets"


@pytest.mark.skipif(not BUCKETS_CSV.exists(), reason="reliability_buckets.csv absent")
def test_reliability_buckets_probabilities_valid():
    df = pd.read_csv(BUCKETS_CSV)
    assert (df["predicted_mean"] >= 0).all()
    assert (df["predicted_mean"] <= 1).all()
    assert (df["observed_frequency"] >= 0).all()
    assert (df["observed_frequency"] <= 1).all()
    assert (df["count"] > 0).all()


# ─────────────────────────────────────────────────────────────────────────────
# 5. production_gate_v2.json
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not GATE_V2_JSON.exists(), reason="production_gate_v2.json absent")
def test_gate_v2_schema():
    d = json.loads(GATE_V2_JSON.read_text())
    required = ["verdict", "criteria_met", "criteria_failed",
                "n_criteria_met", "n_criteria_failed",
                "avg_nll", "significance_summary", "note"]
    for k in required:
        assert k in d, f"Missing key: {k}"


@pytest.mark.skipif(not GATE_V2_JSON.exists(), reason="production_gate_v2.json absent")
def test_gate_v2_verdict_valid():
    d = json.loads(GATE_V2_JSON.read_text())
    assert d["verdict"] in ("PASS", "BORDERLINE_EXPERIMENTAL", "FAIL"), \
        f"Unknown verdict: {d['verdict']}"


@pytest.mark.skipif(not GATE_V2_JSON.exists(), reason="production_gate_v2.json absent")
def test_gate_v2_nll_direction_consistent():
    """If hybrid avg NLL > elo avg NLL, the gate must not be PASS."""
    d = json.loads(GATE_V2_JSON.read_text())
    nll_info = d["avg_nll"]
    delta = nll_info["delta"]   # hybrid - elo (negative = hybrid better)
    if delta > 0:
        assert d["verdict"] != "PASS", \
            f"Hybrid avg NLL is worse (+{delta}) but gate says PASS"


@pytest.mark.skipif(not GATE_V2_JSON.exists(), reason="production_gate_v2.json absent")
def test_gate_v2_borderline_not_integrated():
    """
    If verdict != PASS, verify no hybrid production flag is enabled in the
    production match model. We check MatchModel source for CalibratedHybrid
    references that would indicate premature integration.
    """
    d = json.loads(GATE_V2_JSON.read_text())
    if d["verdict"] == "PASS":
        pytest.skip("Gate PASS — integration may proceed")

    match_model_path = ROOT / "src" / "wc2026" / "match_model.py"
    if not match_model_path.exists():
        pytest.skip("match_model.py not found")

    source = match_model_path.read_text()
    assert "hybrid_params.json" not in source, \
        "hybrid_params.json referenced in match_model.py — production integration happened without PASS gate"
    assert "CalibratedHybridMatchModel" not in source, \
        "CalibratedHybridMatchModel in match_model.py — premature production integration"


@pytest.mark.skipif(not GATE_V2_JSON.exists(), reason="production_gate_v2.json absent")
def test_gate_v2_criteria_counts_consistent():
    d = json.loads(GATE_V2_JSON.read_text())
    assert d["n_criteria_met"] == len(d["criteria_met"])
    assert d["n_criteria_failed"] == len(d["criteria_failed"])
    total = d["n_criteria_met"] + d["n_criteria_failed"]
    assert total >= 5, f"Only {total} criteria evaluated — too few for a rigorous gate"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Significance module unit tests (offline, no script required)
# ─────────────────────────────────────────────────────────────────────────────

def test_significance_module_imports():
    from wc2026.calibration.significance import (
        compute_significance, approx_se_nll, summary_verdict,
        batch_significance, classify_verdict,
    )


def test_approx_se_nll_decreases_with_n():
    from wc2026.calibration.significance import approx_se_nll
    se_100  = approx_se_nll(100)
    se_1000 = approx_se_nll(1000)
    se_5000 = approx_se_nll(5000)
    assert se_100 > se_1000 > se_5000
    assert se_100 > 0


def test_wc2022_se_is_high():
    """n=64 → SE should be high enough that Δ=0.005 is noise."""
    from wc2026.calibration.significance import approx_se_nll, classify_verdict
    se = approx_se_nll(64)
    verdict, _ = classify_verdict(0.005, se)
    assert verdict == "tie", f"Δ=0.005 on n=64 should be 'tie', got '{verdict}'"


def test_large_improvement_is_clear_win():
    """Δ=-0.05 on n=3000 → clear_win."""
    from wc2026.calibration.significance import approx_se_nll, classify_verdict
    se = approx_se_nll(3000)
    verdict, _ = classify_verdict(-0.05, se)
    assert verdict == "clear_win", f"Expected clear_win, got {verdict}"


def test_tiny_improvement_is_tie():
    """Δ=-0.002 on n=3000 → tie or marginal_win, not clear_win."""
    from wc2026.calibration.significance import approx_se_nll, classify_verdict
    se = approx_se_nll(3000)
    verdict, _ = classify_verdict(-0.002, se)
    assert verdict in ("tie", "marginal_win"), f"Expected tie/marginal, got {verdict}"


def test_compute_significance_returns_dataclass():
    from wc2026.calibration.significance import compute_significance
    r = compute_significance("test_split", 1000, "model_A", "model_B", 0.95, 0.93)
    assert r.delta_nll < 0
    assert r.verdict in ("clear_win", "marginal_win", "tie", "loss")
    assert math.isfinite(r.z_score)
    assert math.isfinite(r.approx_se)
