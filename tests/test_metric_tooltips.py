"""Phase 1E — static assertions that jargon metrics carry plain-language tooltips.

Display-only copy checks. No model / config / forecast / scorecard / data involved.
Deterministic source-text assertions (no browser, no AppTest).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")


def test_ece_defined_for_non_experts():
    assert "Expected Calibration Error" in APP_PY


def test_nll_defined_for_non_experts():
    assert "Negative Log-Likelihood" in APP_PY


def test_rho_dixon_coles_has_help():
    assert "Dixon-Coles low-score correction" in APP_PY


def test_log_base_has_help():
    assert "Baseline scoring rate" in APP_PY


def test_brier_glossary_caption_present():
    # One-line glossary under the ablation comparison table.
    assert "mean squared probability error" in APP_PY


def test_champion_brier_metric_has_help():
    assert "averaged over 48 teams" in APP_PY
