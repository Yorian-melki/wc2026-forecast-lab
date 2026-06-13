"""
P4 publication package tests.

Verifies that all publication-required files exist, contain correct data,
and are free of forbidden claims.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

# --- Required file paths ---
MODEL_CARD    = ROOT / "MODEL_CARD.md"
MODEL_FREEZE  = ROOT / "MODEL_FREEZE.md"
README        = ROOT / "README.md"
MANIFEST      = ROOT / "data" / "model_freeze_manifest.json"
CHART         = ROOT / "outputs" / "public" / "wc2026_final_forecast_chart.png"
REPORT        = ROOT / "outputs" / "public" / "model_selection_report.md"
TECH_SUMMARY  = ROOT / "outputs" / "public" / "technical_summary.md"
CLAIMS_CHECK  = ROOT / "outputs" / "public" / "claims_checklist.md"
LINKEDIN      = ROOT / "outputs" / "public" / "linkedin_post.md"
CLAIMS_AUDIT  = ROOT / "outputs" / "public" / "claims_audit.md"
REPRO_LOG     = ROOT / "outputs" / "public" / "reproducibility_log.txt"
REPRO_SCRIPT  = ROOT / "scripts" / "reproduce_public_outputs.py"
CHART_SCRIPT  = ROOT / "scripts" / "generate_public_final_chart.py"
ELO_PARAMS    = ROOT / "data" / "elo_calibrated_params.json"
ELO_CSV       = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"

FROZEN_BETA_ELO  = 0.543593
FROZEN_SEED      = 20260609
FROZEN_ITERS     = 100_000
TOP3_UPPER_BOUND = 0.50  # hard ceiling — over 50% is clearly wrong


# ─────────────────────────────────────────────────────────────────────────────
# 1. Required files exist
# ─────────────────────────────────────────────────────────────────────────────

def test_model_card_exists():           assert MODEL_CARD.exists()
def test_model_freeze_exists():         assert MODEL_FREEZE.exists()
def test_readme_exists():               assert README.exists()
def test_manifest_exists():             assert MANIFEST.exists()
def test_final_chart_exists():          assert CHART.exists()
def test_model_selection_report_exists(): assert REPORT.exists()
def test_technical_summary_exists():    assert TECH_SUMMARY.exists()
def test_claims_checklist_exists():     assert CLAIMS_CHECK.exists()
def test_linkedin_post_exists():        assert LINKEDIN.exists()
def test_claims_audit_exists():         assert CLAIMS_AUDIT.exists()
def test_reproducibility_log_exists():  assert REPRO_LOG.exists()
def test_reproduce_script_exists():     assert REPRO_SCRIPT.exists()
def test_chart_script_exists():         assert CHART_SCRIPT.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 2. beta_elo unchanged from freeze value
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not ELO_PARAMS.exists(), reason="params missing")
def test_beta_elo_unchanged():
    params = json.loads(ELO_PARAMS.read_text())
    assert abs(params["beta_elo"] - FROZEN_BETA_ELO) < 1e-6, (
        f"beta_elo={params['beta_elo']} differs from frozen {FROZEN_BETA_ELO}"
    )


@pytest.mark.skipif(not ELO_PARAMS.exists(), reason="params missing")
def test_temperature_mul_is_055():
    params = json.loads(ELO_PARAMS.read_text())
    assert abs(params.get("temperature_mul", 0) - 0.55) < 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# 3. Simulation output integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_champion_prob_sum_to_one():
    df = pd.read_csv(ELO_CSV)
    assert abs(df["champion_prob"].sum() - 1.0) < 0.001


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_final_prob_sum_to_two():
    df = pd.read_csv(ELO_CSV)
    assert abs(df["final_prob"].sum() - 2.0) < 0.01


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_sf_prob_sum_to_four():
    df = pd.read_csv(ELO_CSV)
    assert abs(df["sf_prob"].sum() - 4.0) < 0.01


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_top3_concentration_below_ceiling():
    df = pd.read_csv(ELO_CSV)
    top3 = float(df.head(3)["champion_prob"].sum())
    assert top3 < TOP3_UPPER_BOUND, f"top3={top3:.3f} exceeds ceiling {TOP3_UPPER_BOUND}"


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_top1_below_25_percent():
    df = pd.read_csv(ELO_CSV)
    top1 = float(df.head(1)["champion_prob"].sum())
    assert top1 < 0.25, f"top1={top1:.3f} — single team over 25% is implausible"


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_simulation_has_48_teams():
    df = pd.read_csv(ELO_CSV)
    assert len(df) == 48


@pytest.mark.skipif(not ELO_CSV.exists(), reason="elo summary missing")
def test_all_champion_probs_non_negative():
    df = pd.read_csv(ELO_CSV)
    assert (df["champion_prob"] >= 0).all()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Model freeze manifest
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_schema():
    m = json.loads(MANIFEST.read_text())
    for key in ["beta_elo", "simulation_seed", "iterations", "top10_probs",
                "concentration_metrics", "forbidden_claims_checked"]:
        assert key in m, f"Missing key: {key}"


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_beta_matches_params():
    m = json.loads(MANIFEST.read_text())
    assert abs(m["beta_elo"] - FROZEN_BETA_ELO) < 1e-6


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_seed_is_frozen():
    m = json.loads(MANIFEST.read_text())
    assert m["simulation_seed"] == FROZEN_SEED


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_iterations_is_100k():
    m = json.loads(MANIFEST.read_text())
    assert m["iterations"] == FROZEN_ITERS


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_forbidden_claims_checked():
    m = json.loads(MANIFEST.read_text())
    assert m["forbidden_claims_checked"] is True


@pytest.mark.skipif(not MANIFEST.exists(), reason="manifest missing")
def test_manifest_has_top10_probs():
    m = json.loads(MANIFEST.read_text())
    assert len(m["top10_probs"]) == 10
    total = sum(m["top10_probs"].values())
    assert total < 1.01, f"Top-10 prob sum={total:.4f} implausible"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Forbidden claims absent from public documents
# ─────────────────────────────────────────────────────────────────────────────

FORBIDDEN_PHRASES = [
    "hedge-fund-grade",
    "beats betting markets",
    "guaranteed edge",
    "ai predicts winner",
    "production betting model",
    "sure prediction",
    "will win",
    "peer-reviewed methodology",
    "fully calibrated",
]

# Files that LIST forbidden items explicitly — check only their body before the list
_EXCLUDE_AFTER_FORBIDDEN_HEADER = {
    "claims_checklist.md",
    "claims_audit.md",
    "model_selection_report.md",
    "model_card.md",
}


def _body_for_check(path: Path) -> str:
    """Return only the portion of the file before any 'forbidden' section."""
    text = path.read_text().lower()
    if path.name.lower() in _EXCLUDE_AFTER_FORBIDDEN_HEADER:
        parts = text.split("forbidden")
        return parts[0] if len(parts) > 1 else text
    return text


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_model_card_no_forbidden(phrase):
    if not MODEL_CARD.exists(): pytest.skip("MODEL_CARD.md missing")
    assert phrase not in _body_for_check(MODEL_CARD), f"Found '{phrase}' in MODEL_CARD.md"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_readme_no_forbidden(phrase):
    if not README.exists(): pytest.skip("README.md missing")
    assert phrase not in _body_for_check(README), f"Found '{phrase}' in README.md"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_linkedin_no_forbidden(phrase):
    if not LINKEDIN.exists(): pytest.skip("linkedin_post.md missing")
    assert phrase not in _body_for_check(LINKEDIN), f"Found '{phrase}' in linkedin_post.md"


@pytest.mark.parametrize("phrase", FORBIDDEN_PHRASES)
def test_technical_summary_no_forbidden(phrase):
    if not TECH_SUMMARY.exists(): pytest.skip("technical_summary.md missing")
    assert phrase not in _body_for_check(TECH_SUMMARY), f"Found '{phrase}' in technical_summary.md"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Allowed claims present in public documents
# ─────────────────────────────────────────────────────────────────────────────

def test_model_card_mentions_49450():
    if not MODEL_CARD.exists(): pytest.skip()
    assert "49,450" in MODEL_CARD.read_text()


def test_model_card_mentions_100k_simulations():
    if not MODEL_CARD.exists(): pytest.skip()
    text = MODEL_CARD.read_text()
    assert "100,000" in text or "100K" in text


def test_model_card_mentions_hybrid_rejection():
    if not MODEL_CARD.exists(): pytest.skip()
    assert "rejected" in MODEL_CARD.read_text().lower()


def test_model_card_mentions_ece_degradation():
    if not MODEL_CARD.exists(): pytest.skip()
    assert "17%" in MODEL_CARD.read_text()


def test_readme_mentions_conservation_law():
    if not README.exists(): pytest.skip()
    text = README.read_text()
    assert "1.000" in text or "conservation" in text.lower()


def test_claims_audit_mentions_exact_match_count():
    if not CLAIMS_AUDIT.exists(): pytest.skip()
    assert "49,450" in CLAIMS_AUDIT.read_text()


def test_claims_audit_mentions_n_train_matches():
    if not CLAIMS_AUDIT.exists(): pytest.skip()
    assert "10,555" in CLAIMS_AUDIT.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# 7. LinkedIn post length is reasonable
# ─────────────────────────────────────────────────────────────────────────────

def test_linkedin_post_length():
    if not LINKEDIN.exists(): pytest.skip()
    text = LINKEDIN.read_text()
    # Content section length (strip headers)
    content_lines = [l for l in text.splitlines() if not l.startswith("#") and l.strip()]
    content = " ".join(content_lines)
    char_count = len(content)
    assert 500 <= char_count <= 5000, f"LinkedIn post content length={char_count} unusual"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Reproducibility log exists and indicates pass
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not REPRO_LOG.exists(), reason="repro log not generated")
def test_reproducibility_log_mentions_beta():
    text = REPRO_LOG.read_text()
    assert "beta_elo" in text.lower() or "0.543" in text


@pytest.mark.skipif(not REPRO_LOG.exists(), reason="repro log not generated")
def test_reproducibility_log_mentions_conservation():
    text = REPRO_LOG.read_text()
    assert "champion" in text.lower()
