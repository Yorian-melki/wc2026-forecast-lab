"""
P2 Hybrid Elo-DC model tests.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
HYBRID_JSON = ROOT / "outputs" / "calibration" / "hybrid_params.json"
BACKTEST_CSV = ROOT / "outputs" / "calibration" / "hybrid_backtest_results.csv"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_matches() -> pd.DataFrame:
    """20-match synthetic dataset with sensible structure."""
    rows = [
        ("2015-06-10", "France", "Germany", 2, 0, "UEFA Euro qualification", False, 0.75),
        ("2015-07-15", "Brazil", "Argentina", 1, 1, "Friendly", True, 0.35),
        ("2016-06-15", "Spain", "Portugal", 3, 3, "UEFA Euro", True, 0.90),
        ("2016-06-20", "England", "France", 1, 2, "UEFA Euro", True, 0.90),
        ("2017-03-25", "Germany", "England", 1, 0, "FIFA World Cup qualification", False, 0.80),
        ("2017-06-11", "Argentina", "Brazil", 0, 0, "FIFA World Cup qualification", True, 0.80),
        ("2018-06-16", "France", "Australia", 2, 1, "FIFA World Cup", True, 1.00),
        ("2018-06-17", "Argentina", "Iceland", 1, 1, "FIFA World Cup", True, 1.00),
        ("2018-06-18", "Germany", "Mexico", 0, 1, "FIFA World Cup", True, 1.00),
        ("2018-06-19", "Brazil", "Switzerland", 1, 1, "FIFA World Cup", True, 1.00),
        ("2018-06-20", "England", "Tunisia", 2, 1, "FIFA World Cup", True, 1.00),
        ("2018-06-21", "Spain", "Iran", 1, 0, "FIFA World Cup", True, 1.00),
        ("2019-06-10", "France", "Germany", 2, 2, "UEFA Nations League", True, 0.70),
        ("2019-06-15", "Brazil", "Argentina", 2, 0, "Copa América", True, 0.90),
        ("2020-10-07", "England", "Belgium", 2, 1, "UEFA Nations League", True, 0.70),
        ("2021-06-15", "Portugal", "Germany", 2, 4, "UEFA Euro", True, 0.90),
        ("2021-06-23", "France", "Portugal", 2, 2, "UEFA Euro", True, 0.90),
        ("2022-03-29", "Germany", "Argentina", 2, 0, "Friendly", True, 0.35),
        ("2022-06-06", "Spain", "France", 1, 2, "UEFA Nations League", True, 0.70),
        ("2022-11-22", "France", "Australia", 4, 1, "FIFA World Cup", True, 1.00),
    ]
    return pd.DataFrame(rows, columns=[
        "date", "home_team", "away_team", "home_goals", "away_goals",
        "tournament", "neutral", "weight"
    ])


@pytest.fixture(scope="module")
def elo_engine_fitted(sample_matches) -> "RollingEloEngine":
    from wc2026.calibration.rolling_elo import RollingEloEngine
    engine = RollingEloEngine()
    engine.fit(sample_matches[sample_matches["date"] < "2018-01-01"])
    return engine


@pytest.fixture(scope="module")
def hybrid_params(sample_matches, elo_engine_fitted):
    from wc2026.calibration.hybrid_elo_dc import fit_hybrid
    train = sample_matches[sample_matches["date"] < "2018-01-01"]
    all_teams = sorted(set(sample_matches["home_team"]) | set(sample_matches["away_team"]))
    return fit_hybrid(
        train, elo_engine_fitted, all_teams=all_teams,
        regularization_lambda=0.1, n_restarts=2, verbose=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dataset
# ─────────────────────────────────────────────────────────────────────────────

def test_raw_dataset_loads():
    raw = ROOT / "data" / "external" / "international_results" / "results.csv"
    assert raw.exists(), "martj42 results.csv not downloaded"
    df = pd.read_csv(raw)
    assert len(df) > 40000
    assert "home_score" in df.columns
    assert "neutral" in df.columns


def test_no_duplicate_matches():
    raw = ROOT / "data" / "external" / "international_results" / "results.csv"
    df = pd.read_csv(raw).dropna(subset=["home_score", "away_score"])
    dedup = df.drop_duplicates(subset=["date", "home_team", "away_team"])
    n_dups = len(df) - len(dedup)
    # martj42 dataset has 2 known duplicates (Tahiti 1974 + Gibraltar 2026); allow ≤5
    assert n_dups <= 5, f"Unexpected duplicate count: {n_dups}"


def test_scores_valid():
    raw = ROOT / "data" / "external" / "international_results" / "results.csv"
    df = pd.read_csv(raw).dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    assert (df["home_score"] >= 0).all()
    assert (df["away_score"] >= 0).all()
    # Max known: AUS 31-0 American Samoa (2001), Tahiti 0-21 type results exist
    assert (df["home_score"] <= 50).all(), "Implausibly high score (>50)"
    assert (df["away_score"] <= 50).all(), "Implausibly high score (>50)"


def test_wc2026_teams_all_mapped():
    from wc2026.calibration.international_dataset import _name_to_fifa3_map
    raw = ROOT / "data" / "external" / "international_results" / "results.csv"
    df = pd.read_csv(raw)
    wc = pd.read_csv(ROOT / "data" / "teams.csv")
    mapping = _name_to_fifa3_map()
    missing = [name for name in wc["name"] if name not in mapping]
    assert not missing, f"WC2026 teams missing from mapping: {missing}"


def test_dataset_builder_runs():
    from wc2026.calibration.international_dataset import build_clean_dataset
    df, fail_df = build_clean_dataset(min_year=2018, max_year=2022)
    assert len(df) > 1000
    assert "home_goals" in df.columns
    assert "neutral" in df.columns
    assert "weight" in df.columns


def test_no_missing_goals_in_clean_dataset():
    from wc2026.calibration.international_dataset import build_clean_dataset
    df, _ = build_clean_dataset(min_year=2018, max_year=2022)
    assert df["home_goals"].notna().all()
    assert df["away_goals"].notna().all()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rolling Elo
# ─────────────────────────────────────────────────────────────────────────────

def test_rolling_elo_fits(sample_matches):
    from wc2026.calibration.rolling_elo import RollingEloEngine
    engine = RollingEloEngine()
    engine.fit(sample_matches)
    assert len(engine.ratings) >= 6
    assert all(math.isfinite(v) for v in engine.ratings.values())


def test_rolling_elo_no_leakage(sample_matches):
    """Pre-match Elo must not include the match itself."""
    from wc2026.calibration.rolling_elo import RollingEloEngine
    engine = RollingEloEngine()
    # Fit up to just before a known date
    train = sample_matches[sample_matches["date"] < "2018-06-16"]
    engine.fit(train)
    # After France vs Australia on 2018-06-16, France's Elo should be higher
    # But pre-match Elo for that game should be the value BEFORE it
    elo_before = engine.get_elo("France", before_date="2018-06-16")
    engine.fit(sample_matches[sample_matches["date"] == "2018-06-16"])
    elo_after = engine.get_elo("France")
    # France won 2-1, so their Elo should increase
    assert elo_after > elo_before


def test_temporal_split_no_leakage(sample_matches):
    from wc2026.calibration.international_dataset import make_temporal_splits
    splits = make_temporal_splits(sample_matches)
    for split_name, (train, test) in splits.items():
        if len(train) == 0 or len(test) == 0:
            continue
        max_train_date = train["date"].max()
        min_test_date = test["date"].min()
        assert max_train_date < min_test_date, (
            f"Temporal leakage in {split_name}: "
            f"train max={max_train_date}, test min={min_test_date}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Hybrid model
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_probs_sum_to_one(hybrid_params, sample_matches):
    from wc2026.calibration.rolling_elo import RollingEloEngine
    engine = RollingEloEngine()
    engine.fit(sample_matches)
    pairs = [("France", "Germany"), ("Brazil", "Argentina"), ("Spain", "England")]
    for h, a in pairs:
        elo_h = engine.get_elo(h)
        elo_a = engine.get_elo(a)
        ph, pd_, pa = hybrid_params.prob_1x2(h, a, elo_h, elo_a)
        assert abs(ph + pd_ + pa - 1.0) < 1e-5, f"{h} vs {a}: probs don't sum to 1"
        assert ph >= 0 and pd_ >= 0 and pa >= 0


def test_higher_elo_diff_increases_win_prob(hybrid_params):
    """Team with higher Elo should have higher win probability."""
    ph_strong, _, pa_strong = hybrid_params.prob_1x2(
        "France", "Germany", elo_home=2100, elo_away=1800
    )
    ph_equal, _, pa_equal = hybrid_params.prob_1x2(
        "France", "Germany", elo_home=1900, elo_away=1900
    )
    ph_weak, _, pa_weak = hybrid_params.prob_1x2(
        "France", "Germany", elo_home=1700, elo_away=2000
    )
    assert ph_strong > ph_equal > ph_weak
    assert pa_strong < pa_equal < pa_weak


def test_rho_bounded(hybrid_params):
    assert -0.20 <= hybrid_params.rho <= 0.20


def test_beta_elo_non_negative(hybrid_params):
    assert hybrid_params.beta_elo >= 0.0


def test_attack_residuals_centered(hybrid_params):
    mean_atk = sum(hybrid_params.attack_res.values()) / max(len(hybrid_params.attack_res), 1)
    assert abs(mean_atk) < 0.1, f"Attack residuals not centered: mean={mean_atk:.4f}"


def test_hybrid_finite_nll(hybrid_params):
    assert math.isfinite(hybrid_params.final_nll)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Output files (require run_hybrid_backtests.py to have been run)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not HYBRID_JSON.exists(), reason="hybrid_params.json not yet generated")
def test_hybrid_params_json_schema():
    d = json.loads(HYBRID_JSON.read_text())
    assert "params" in d
    assert "production_gate" in d
    p = d["params"]
    assert "beta_elo" in p
    assert "rho" in p
    assert "log_base" in p
    assert "team_attack_res" in p
    assert isinstance(d["production_gate"]["passed"], bool)


@pytest.mark.skipif(not HYBRID_JSON.exists(), reason="hybrid_params.json not yet generated")
def test_hybrid_rho_valid():
    d = json.loads(HYBRID_JSON.read_text())
    rho = d["params"]["rho"]
    assert -0.20 <= rho <= 0.20


@pytest.mark.skipif(not BACKTEST_CSV.exists(), reason="hybrid_backtest_results.csv not generated")
def test_backtest_results_schema():
    df = pd.read_csv(BACKTEST_CSV)
    required = ["split", "n_train", "n_test", "hybrid_nll", "elo_calib_nll",
                "hybrid_beats_elo_calib", "beta_elo", "rho"]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.skipif(not BACKTEST_CSV.exists(), reason="hybrid_backtest_results.csv not generated")
def test_production_gate_documented():
    """Production gate result must be honestly documented."""
    if not HYBRID_JSON.exists():
        pytest.skip("hybrid_params.json not generated")
    d = json.loads(HYBRID_JSON.read_text())
    gate = d["production_gate"]
    df = pd.read_csv(BACKTEST_CSV)
    n_splits = len(df)
    n_passing = int(df["hybrid_beats_elo_calib"].sum())
    expected_pass = n_passing >= 2
    assert gate["passed"] == expected_pass, (
        f"Production gate mismatch: {n_passing}/{n_splits} beats Elo but "
        f"gate says passed={gate['passed']}"
    )
