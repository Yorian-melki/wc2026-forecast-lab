"""Tests for Dixon-Coles correction and Wilson CI."""
import math
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from wc2026.data_loader import load_config, load_teams
from wc2026.match_model import MatchModel
from wc2026.confidence import wilson_ci, add_confidence_intervals
import pandas as pd


@pytest.fixture
def model():
    config = load_config()
    return MatchModel(config)


@pytest.fixture
def teams():
    return load_teams()


def test_dc_flat_sums_to_one(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    mu_a, mu_b = model.expected_goals(fra, esp, knockout=False)
    flat = model._build_dc_flat(mu_a, mu_b)
    assert abs(flat.sum() - 1.0) < 1e-9


def test_dc_flat_all_nonnegative(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    mu_a, mu_b = model.expected_goals(fra, esp, knockout=False)
    flat = model._build_dc_flat(mu_a, mu_b)
    assert np.all(flat >= 0.0)


def test_dc_reduces_0_0_vs_raw_poisson(model, teams):
    """P(0-0) with DC (rho=0.08) must be lower than raw Poisson."""
    fra, esp = teams["FRA"], teams["ESP"]
    mu_a, mu_b = model.expected_goals(fra, esp, knockout=False)
    flat_dc = model._build_dc_flat(mu_a, mu_b)
    g = model.dc_max_goals + 1
    p00_dc = flat_dc[0]  # index 0*g+0=0

    # Raw Poisson
    p00_raw = math.exp(-mu_a) * math.exp(-mu_b)
    # Renormalise truncated Poisson (same truncation)
    assert p00_dc < p00_raw, f"DC P(0-0)={p00_dc:.4f} should be < raw {p00_raw:.4f}"


def test_dc_increases_1_0_vs_raw_poisson(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    mu_a, mu_b = model.expected_goals(fra, esp, knockout=False)
    flat_dc = model._build_dc_flat(mu_a, mu_b)
    g = model.dc_max_goals + 1
    p10_dc = flat_dc[1 * g + 0]  # goals_a=1, goals_b=0

    p10_raw = (math.exp(-mu_a) * mu_a) * math.exp(-mu_b)
    assert p10_dc > p10_raw, f"DC P(1-0)={p10_dc:.4f} should be > raw {p10_raw:.4f}"


def test_dc_cache_populated_after_match(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    rng = np.random.default_rng(0)
    assert len(model._dc_cache) == 0
    model.simulate_group_match(fra, esp, rng)
    assert ("FRA", "ESP", "group") in model._dc_cache


def test_dc_cache_reused(model, teams):
    fra, esp = teams["FRA"], teams["ESP"]
    rng = np.random.default_rng(0)
    for _ in range(10):
        model.simulate_group_match(fra, esp, rng)
    # Cache should still have exactly one entry for this pair+context
    group_entries = [k for k in model._dc_cache if k[2] == "group"]
    fra_esp_entries = [k for k in group_entries if k[0] == "FRA" and k[1] == "ESP"]
    assert len(fra_esp_entries) == 1


def test_wilson_ci_contains_p():
    for p in [0.01, 0.05, 0.10, 0.50, 0.90]:
        lo, hi = wilson_ci(p, n=100000)
        assert lo <= p <= hi


def test_wilson_ci_width_decreases_with_n():
    p = 0.08
    lo1, hi1 = wilson_ci(p, n=1000)
    lo2, hi2 = wilson_ci(p, n=100000)
    assert (hi2 - lo2) < (hi1 - lo1)


def test_add_confidence_intervals_adds_columns():
    df = pd.DataFrame({
        "team": ["FRA", "ESP"],
        "champion_prob": [0.076, 0.068],
        "final_prob": [0.12, 0.11],
        "sf_prob": [0.20, 0.19],
        "group_survival_prob": [0.82, 0.84],
    })
    out = add_confidence_intervals(df, iterations=100000)
    for col in ["champion_ci_low", "champion_ci_high", "final_ci_low", "final_ci_high"]:
        assert col in out.columns
    # CI must bracket the point estimate
    for _, r in out.iterrows():
        assert r["champion_ci_low"] <= r["champion_prob"] <= r["champion_ci_high"]
