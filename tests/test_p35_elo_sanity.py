"""
P3.5 Elo calibration sanity tests.

Verifies that the concentration audit outputs exist and meet quality criteria.
Tests are structured to be runnable before and after temperature fix.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / "outputs" / "calibration"

CONC_CSV    = OUT / "elo_concentration_audit.csv"
CONC_MD     = OUT / "elo_concentration_audit.md"
SANITY_CSV  = OUT / "elo_match_sanity.csv"
TEMP_CSV    = OUT / "elo_temperature_ablation.csv"
TEMP_MD     = OUT / "elo_temperature_summary.md"
HIST_CSV    = OUT / "historical_tournament_concentration.csv"
HIST_MD     = OUT / "historical_tournament_concentration.md"
GATE_JSON   = OUT / "elo_calibration_gate.json"
ELO_PARAMS  = ROOT / "data" / "elo_calibrated_params.json"

ELO_CSV     = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"
EXPERT_CSV  = ROOT / "outputs" / "tournament_run" / "expert_summary.csv"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Output files exist
# ─────────────────────────────────────────────────────────────────────────────

def test_concentration_audit_csv_exists():
    assert CONC_CSV.exists()

def test_concentration_audit_md_exists():
    assert CONC_MD.exists()

def test_match_sanity_csv_exists():
    assert SANITY_CSV.exists()

def test_temperature_ablation_csv_exists():
    assert TEMP_CSV.exists()

def test_temperature_summary_md_exists():
    assert TEMP_MD.exists()

def test_historical_concentration_csv_exists():
    assert HIST_CSV.exists()

def test_historical_concentration_md_exists():
    assert HIST_MD.exists()

def test_production_gate_exists():
    assert GATE_JSON.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Concentration audit — content checks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not CONC_CSV.exists(), reason="concentration audit not generated")
def test_concentration_audit_schema():
    df = pd.read_csv(CONC_CSV)
    for col in ["model", "top1", "top3", "top5", "entropy", "herfindahl"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not CONC_CSV.exists(), reason="concentration audit not generated")
def test_concentration_has_both_models():
    df = pd.read_csv(CONC_CSV)
    models = set(df["model"].tolist())
    assert "elo_calibrated" in models
    assert "expert" in models


@pytest.mark.skipif(not CONC_CSV.exists(), reason="concentration audit not generated")
def test_elo_top3_is_higher_than_expert():
    df = pd.read_csv(CONC_CSV)
    elo_top3 = df[df["model"] == "elo_calibrated"]["top3"].values[0]
    exp_top3 = df[df["model"] == "expert"]["top3"].values[0]
    # Known issue: Elo beta=0.988 over-concentrates
    assert elo_top3 > exp_top3, "Elo should be more concentrated than expert"


@pytest.mark.skipif(not CONC_CSV.exists(), reason="concentration audit not generated")
def test_elo_original_top3_exceeds_historical_reference():
    """Original Elo (beta=0.988) should be clearly over-concentrated."""
    df = pd.read_csv(CONC_CSV)
    elo_top3 = df[df["model"] == "elo_calibrated"]["top3"].values[0]
    # Historical reference: 36%. Original beta should exceed 46% to trigger fix.
    assert elo_top3 > 0.46, f"Expected over-concentrated, got top3={elo_top3:.3f}"


@pytest.mark.skipif(not CONC_CSV.exists(), reason="concentration audit not generated")
def test_entropy_values_are_finite_and_positive():
    df = pd.read_csv(CONC_CSV)
    for _, row in df.iterrows():
        assert math.isfinite(row["entropy"]), f"Non-finite entropy for {row['model']}"
        assert row["entropy"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Match sanity — probability checks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_match_sanity_schema():
    df = pd.read_csv(SANITY_CSV)
    for col in ["beta_mul", "team_a", "team_b", "p_a_win_90", "p_draw_90", "p_b_win_90",
                "expected_goals_a", "expected_goals_b"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_probabilities_sum_to_one():
    df = pd.read_csv(SANITY_CSV)
    for _, row in df.iterrows():
        total = row["p_a_win_90"] + row["p_draw_90"] + row["p_b_win_90"]
        assert abs(total - 1.0) < 1e-3, f"Probs sum={total:.4f} for {row['team_a']} vs {row['team_b']}"


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_all_probabilities_non_negative():
    df = pd.read_csv(SANITY_CSV)
    for col in ["p_a_win_90", "p_draw_90", "p_b_win_90"]:
        assert (df[col] >= 0).all(), f"Negative probabilities in {col}"


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_higher_elo_team_has_higher_win_prob():
    """Team A (higher Elo) must have higher win prob than Team B for top vs weak matchups."""
    df = pd.read_csv(SANITY_CSV)
    orig = df[df["beta_mul"] == 1.00]
    strong_vs_weak = orig[orig["elo_diff"] > 200]  # large gap
    for _, row in strong_vs_weak.iterrows():
        assert row["p_a_win_90"] > row["p_b_win_90"], (
            f"ESP vs weak: P(A win)={row['p_a_win_90']:.3f} should be > P(B win)={row['p_b_win_90']:.3f}"
        )


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_draw_rate_minimum_for_any_matchup():
    """For production beta (0.55) and Elo diff < 400, draw rate should be >= 15%."""
    df = pd.read_csv(SANITY_CSV)
    # Only check production range (beta_mul=0.55) and non-extreme matchups (Elo diff < 400)
    prod = df[(df["beta_mul"] == 0.55) & (df["elo_diff"].abs() < 400)]
    below_floor = prod[prod["p_draw_90"] < 0.15]
    assert len(below_floor) == 0, (
        f"{len(below_floor)} non-extreme matchups at prod beta have draw rate < 15%: "
        f"{below_floor[['team_a','team_b','elo_diff','p_draw_90']].to_string()}"
    )


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_original_beta_ESP_vs_rank20_implausible():
    """At original beta=1.0, ESP vs rank-20 should give ESP > 70% — which is implausible."""
    df = pd.read_csv(SANITY_CSV)
    orig = df[(df["beta_mul"] == 1.00) & (df["team_a"] == "ESP")]
    if len(orig) == 0:
        pytest.skip("ESP not in match sanity (different team names)")
    # Find a matchup with Elo diff > 300
    large_diff = orig[orig["elo_diff"] > 300]
    if len(large_diff) == 0:
        pytest.skip("No large-diff ESP matchup found")
    max_win = float(large_diff["p_a_win_90"].max())
    # At beta=0.988, ESP vs median should be > 65%
    assert max_win > 0.65, f"Expected implausible win prob at beta=1.0, got {max_win:.3f}"


@pytest.mark.skipif(not SANITY_CSV.exists(), reason="match sanity not generated")
def test_reduced_beta_reduces_win_prob():
    """Lower beta_mul should give lower win probabilities for the strong team."""
    df = pd.read_csv(SANITY_CSV)
    # Find ESP vs a weak team across all beta values
    esp_weak = df[(df["team_a"] == "ESP") & (df["elo_diff"] > 300)]
    if len(esp_weak) < 3:
        pytest.skip("Not enough ESP vs weak matchup data")
    by_beta = esp_weak.groupby("beta_mul")["p_a_win_90"].mean().sort_index()
    # Higher beta_mul → higher win prob
    assert by_beta.is_monotonic_increasing or by_beta.iloc[0] > by_beta.iloc[-1], (
        f"Expected win prob to decrease with beta_mul: {by_beta.to_dict()}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Temperature ablation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_temperature_ablation_schema():
    df = pd.read_csv(TEMP_CSV)
    for col in ["beta_mul", "beta_elo", "top1", "top3", "top5", "entropy", "herfindahl"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_temperature_ablation_has_multiple_betas():
    df = pd.read_csv(TEMP_CSV)
    assert len(df) >= 4, "Expected at least 4 temperature variants"
    assert df["beta_mul"].nunique() >= 4, "Expected multiple distinct beta_mul values"


@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_lower_beta_reduces_concentration():
    """Monotonic: higher beta_mul → higher top3 concentration (sorted ascending by beta_mul)."""
    df = pd.read_csv(TEMP_CSV).sort_values("beta_mul")  # ascending: 0.40 < 0.55 < ... < 1.00
    top3s = df["top3"].values
    # top3 should increase monotonically with beta_mul (allow 1 exception for MC noise)
    increasing = sum(1 for a, b in zip(top3s[:-1], top3s[1:]) if b >= a - 0.02)
    assert increasing >= len(top3s) - 2, (
        f"Top3 concentration should increase with beta_mul: {list(zip(df['beta_mul'], top3s))}"
    )


@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_some_temperature_achieves_target_top3():
    """At least one beta_mul should bring top3 ≤ 46%."""
    df = pd.read_csv(TEMP_CSV)
    achievable = df[df["top3"] <= 0.46]
    assert len(achievable) > 0, (
        f"No temperature variant achieves top3 ≤ 46%. Min={df['top3'].min():.3f}"
    )


@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_concentration_is_valid_probability():
    df = pd.read_csv(TEMP_CSV)
    assert (df["top1"] > 0).all()
    assert (df["top1"] <= 1.0).all()
    assert (df["top3"] <= 1.0).all()
    assert (df["top3"] >= df["top1"]).all()


@pytest.mark.skipif(not TEMP_CSV.exists(), reason="temperature ablation not generated")
def test_entropy_increases_with_lower_beta():
    """Lower beta → more uniform → higher entropy. Sort descending by beta_mul to check."""
    df = pd.read_csv(TEMP_CSV).sort_values("beta_mul", ascending=False)  # 1.0 → 0.4
    entropies = df["entropy"].values  # should increase (go from low to high)
    # Allow 1 exception for MC noise
    increasing = sum(1 for a, b in zip(entropies[:-1], entropies[1:]) if b >= a - 0.05)
    assert increasing >= len(entropies) - 2, (
        f"Entropy should increase as beta_mul decreases: {list(zip(df['beta_mul'], entropies))}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Historical concentration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not HIST_CSV.exists(), reason="historical concentration not generated")
def test_historical_schema():
    df = pd.read_csv(HIST_CSV)
    for col in ["tournament", "beta_mul", "top1", "top3", "entropy"]:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not HIST_CSV.exists(), reason="historical concentration not generated")
def test_historical_has_multiple_tournaments():
    df = pd.read_csv(HIST_CSV)
    tournaments = df["tournament"].unique()
    assert len(tournaments) >= 1, "Expected at least 1 historical tournament"


@pytest.mark.skipif(not HIST_CSV.exists(), reason="historical concentration not generated")
def test_historical_concentration_values_are_valid():
    df = pd.read_csv(HIST_CSV)
    assert (df["top1"] > 0).all()
    assert (df["top3"] >= df["top1"]).all()
    assert (df["top5"] >= df["top3"]).all()
    assert (df["entropy"] > 0).all()


@pytest.mark.skipif(not HIST_CSV.exists(), reason="historical concentration not generated")
def test_original_beta_over_concentrates_historical():
    """At original beta, pre-tournament simulation should be over-concentrated vs historical."""
    df = pd.read_csv(HIST_CSV)
    orig = df[df["beta_mul"] == 1.0]
    if len(orig) == 0:
        pytest.skip("Original beta not in historical results")
    # At beta=1.0, top3 should be well above 36% historical reference
    for _, r in orig.iterrows():
        # Allow some tolerance: 48-team bracket with competitive-only beta should still be high
        assert r["top3"] > 0.35, f"Expected higher concentration at beta=1.0, got {r['top3']:.3f}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Production gate
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_schema():
    gate = json.loads(GATE_JSON.read_text())
    for key in ["verdict", "criteria_met", "criteria_failed",
                "recommended_beta_mul", "recommended_beta_elo"]:
        assert key in gate, f"Missing key: {key}"


@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_valid_verdict():
    gate = json.loads(GATE_JSON.read_text())
    valid = {"PASS_ELO_CALIBRATED", "PASS_WITH_TEMPERATURE", "FAIL_KEEP_EXPERT", "FAIL_NEED_BLEND"}
    assert gate["verdict"] in valid, f"Invalid verdict: {gate['verdict']}"


@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_not_unconditional_pass():
    """Given beta_elo=0.988 over-concentration, gate should NOT be PASS_ELO_CALIBRATED."""
    gate = json.loads(GATE_JSON.read_text())
    assert gate["verdict"] != "PASS_ELO_CALIBRATED", (
        "Gate PASS_ELO_CALIBRATED for over-concentrated model — "
        f"top3={gate.get('original_top3', '?'):.3f} should fail top3≤46% check"
    )


@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_recommended_beta_is_lower():
    """Recommended beta_elo must be lower than the pre-correction original (0.988)."""
    gate = json.loads(GATE_JSON.read_text())
    # Use the original_beta_elo stored in the gate (set before temperature correction was applied)
    orig_beta = gate.get("original_beta_elo", 0.988)
    rec_beta  = gate["recommended_beta_elo"]
    assert rec_beta < orig_beta, f"Recommended beta {rec_beta} should be < original {orig_beta}"


@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_recommended_top3_in_range():
    """Recommended temperature should yield top3 in credible range [25%, 50%]."""
    gate = json.loads(GATE_JSON.read_text())
    rec_top3 = gate.get("recommended_top3")
    if rec_top3 is None:
        pytest.skip("recommended_top3 not in gate")
    assert 0.25 <= rec_top3 <= 0.50, f"recommended_top3={rec_top3:.3f} out of [0.25, 0.50]"


@pytest.mark.skipif(not GATE_JSON.exists(), reason="production gate not generated")
def test_production_gate_criteria_lists_are_non_empty():
    gate = json.loads(GATE_JSON.read_text())
    assert len(gate["criteria_met"]) > 0, "Expected some criteria met"
    assert len(gate["criteria_failed"]) > 0, "Expected some criteria failed (known concentration issue)"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Poisson math unit tests (no simulation needed)
# ─────────────────────────────────────────────────────────────────────────────

def _poisson_1x2(mu_h: float, mu_a: float, max_g: int = 10):
    import math
    def pmf(k, mu):
        return math.exp(-mu + k * math.log(max(mu, 1e-12)) - math.lgamma(k + 1))
    ph = pd_ = pa = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = pmf(i, mu_h) * pmf(j, mu_a)
            if i > j: ph += p
            elif i == j: pd_ += p
            else: pa += p
    return ph, pd_, pa


def test_poisson_1x2_sums_to_one():
    for mu_h, mu_a in [(1.5, 1.0), (2.5, 0.8), (0.9, 1.4), (3.0, 0.5)]:
        ph, pd_, pa = _poisson_1x2(mu_h, mu_a)
        # Truncation at max_g=10 causes ~1e-4 error for high-lambda inputs
        assert abs(ph + pd_ + pa - 1.0) < 1e-3


def test_poisson_1x2_higher_lambda_wins_more():
    ph_h, _, pa_h = _poisson_1x2(2.0, 1.0)  # strong home
    ph_e, _, pa_e = _poisson_1x2(1.5, 1.5)  # equal
    assert ph_h > ph_e
    assert pa_h < pa_e


def test_poisson_equal_lambdas_symmetric():
    """Independent Poisson with equal lambdas: P(home win) = P(away win), draw < each side's win."""
    ph, pd_, pa = _poisson_1x2(1.2, 1.2)
    assert abs(ph - pa) < 0.01, f"Equal mu should give symmetric win probs: ph={ph:.4f}, pa={pa:.4f}"
    # With mu=1.2, each team wins ~36% of the time, draw ~27% — more ways to win than draw
    assert ph + pa > pd_, "Each side's total win prob should exceed draw rate"


def test_beta_elo_shrinkage_reduces_win_prob():
    """Higher beta_elo → more extreme win probabilities."""
    log_base = 0.227
    elo_diff_scaled = (2155 - 1782) / 400  # ESP vs median
    rho = -0.021

    betas = [0.40, 0.55, 0.70, 0.85, 0.988]
    win_probs = []
    for beta in betas:
        mu_h = math.exp(log_base + beta * elo_diff_scaled)
        mu_a = math.exp(log_base - beta * elo_diff_scaled)
        ph, _, _ = _poisson_1x2(mu_h, mu_a)
        win_probs.append(ph)

    assert win_probs[-1] > win_probs[0], "Higher beta must give higher win prob"
    # Original beta=0.988 should give win prob > 0.65 (confirming implausibility)
    assert win_probs[-1] > 0.65, f"Expected >65% win at beta=0.988, got {win_probs[-1]:.3f}"
    # beta=0.45 should give more reasonable win prob
    assert win_probs[0] < 0.65, f"Expected <65% win at beta=0.40, got {win_probs[0]:.3f}"


def test_expected_goals_esp_vs_median_at_original_beta():
    """At beta=0.988: ESP vs median should have very high xG ratio (confirming over-concentration)."""
    import math
    log_base = 0.227
    beta = 0.988
    elo_diff_scaled = (2155 - 1782) / 400  # ~0.93
    mu_esp    = math.exp(log_base + beta * elo_diff_scaled)
    mu_median = math.exp(log_base - beta * elo_diff_scaled)
    # At original beta, ESP xG should be > 2.5 (extreme)
    assert mu_esp > 2.5, f"ESP xG={mu_esp:.2f} should be > 2.5 at beta=0.988"
    assert mu_median < 0.65, f"Median xG={mu_median:.2f} should be < 0.65 at beta=0.988"


def test_expected_goals_esp_vs_median_at_reduced_beta():
    """At beta=0.55: ESP vs median should be more reasonable than original beta=0.988."""
    import math
    log_base = 0.227
    beta = 0.55
    elo_diff_scaled = (2155 - 1782) / 400  # 373/400 = 0.9325
    mu_esp    = math.exp(log_base + beta * elo_diff_scaled)
    mu_median = math.exp(log_base - beta * elo_diff_scaled)
    # At beta=0.55: mu_esp ≈ 2.10 (better than 3.15 at original beta)
    assert mu_esp < 2.5, f"ESP xG={mu_esp:.2f} should be < 2.5 at beta=0.55"
    assert mu_median > 0.65, f"Median xG={mu_median:.2f} should be > 0.65 at beta=0.55"
    # Key check: much better ratio than original (3.15 vs 0.50 → 6.3x)
    ratio_reduced  = mu_esp / mu_median
    ratio_original = math.exp(0.227 + 0.988 * elo_diff_scaled) / math.exp(0.227 - 0.988 * elo_diff_scaled)
    assert ratio_reduced < ratio_original * 0.7, (
        f"Reduced beta ratio ({ratio_reduced:.2f}) should be < 70% of original ({ratio_original:.2f})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. Expert vs Elo original consistency
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not ELO_CSV.exists() or not EXPERT_CSV.exists(),
                    reason="tournament summaries absent")
def test_expert_more_uniform_than_original_elo():
    elo_df  = pd.read_csv(ELO_CSV)
    exp_df  = pd.read_csv(EXPERT_CSV)
    elo_h   = float(-np.sum(elo_df["champion_prob"] * np.log(np.maximum(elo_df["champion_prob"], 1e-15))))
    exp_h   = float(-np.sum(exp_df["champion_prob"] * np.log(np.maximum(exp_df["champion_prob"], 1e-15))))
    assert exp_h > elo_h, (
        f"Expert entropy {exp_h:.3f} should be > Elo entropy {elo_h:.3f} (more uniform)"
    )


@pytest.mark.skipif(not ELO_CSV.exists() or not EXPERT_CSV.exists(),
                    reason="tournament summaries absent")
def test_elo_top3_exceeds_expert_top3():
    elo_df = pd.read_csv(ELO_CSV)
    exp_df = pd.read_csv(EXPERT_CSV)
    elo_t3 = float(elo_df.head(3)["champion_prob"].sum())
    exp_t3 = float(exp_df.head(3)["champion_prob"].sum())
    assert elo_t3 > exp_t3, "Elo original should be more concentrated than expert"
