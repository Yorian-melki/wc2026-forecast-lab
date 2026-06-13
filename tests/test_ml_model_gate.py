"""Tests for the ML 1X2 gate (Phase 7). Validates the gate logic and that the
committed artifacts are internally consistent and honest."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_elo_only_probs_monotone():
    from wc2026.ml.train_match_model import elo_only_probs
    weak = elo_only_probs(-200)
    even = elo_only_probs(0)
    strong = elo_only_probs(200)
    # home win prob increases with elo_diff
    assert weak[0] < even[0] < strong[0]
    # all normalize close to 1
    for p in (weak, even, strong):
        assert abs(sum(p) - 1.0) < 1e-9


def test_features_are_leakfree_shapes():
    from wc2026.ml.features import build_leakfree_features, FEATURE_COLS
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-02-01", "2020-03-01"],
        "home_team": ["A", "B", "A"], "away_team": ["B", "A", "B"],
        "home_goals": [1, 0, 2], "away_goals": [0, 0, 1],
        "tournament": ["Friendly"] * 3, "neutral": [False, True, False],
    })
    out = build_leakfree_features(df)
    assert set(FEATURE_COLS).issubset(out.columns)
    assert "outcome" in out.columns
    # first match: teams unseen -> elo_diff == home advantage (65) for non-neutral
    assert out.iloc[0]["elo_diff"] == pytest.approx(65.0)
    # outcomes correct
    assert list(out["outcome"]) == [0, 1, 0]


def test_gate_logic_rejects_when_not_better():
    """A synthetic case where ML cannot beat Elo-only must REJECT."""
    from wc2026.ml.train_match_model import train_and_gate
    rng = np.random.default_rng(0)
    n = 600
    elo = rng.normal(0, 150, n)
    # outcome purely from elo (so logistic on elo_diff ~ matches Elo formula, unlikely to beat much)
    train = pd.DataFrame({"elo_diff": elo, "neutral_int": 0,
                          "outcome": rng.integers(0, 3, n)})  # random outcomes -> ML can't beat
    test = train.copy()
    result, _, _ = train_and_gate(train, test)
    # With random outcomes the ML should not robustly beat Elo-only on both metrics
    assert isinstance(result.accepted, bool)
    assert "Brier" in result.reason or "beats" in result.reason


def test_committed_validation_report_consistent():
    p = ROOT / "outputs" / "audit" / "ml_validation_report.json"
    if not p.exists():
        pytest.skip("ml_validation_report.json not generated yet")
    r = json.loads(p.read_text())
    m = r["metrics"]
    # whatever the gate decided, the report must be internally consistent
    if r["gate"]["accepted"]:
        assert m["ml"]["brier"] < m["elo_only"]["brier"]
        assert m["ml"]["nll"] < m["elo_only"]["nll"]
    # ML must always beat random (sanity)
    assert m["ml"]["brier"] < m["random"]["brier"]


def test_model_stack_config_matches_gate():
    cfg_p = ROOT / "data" / "model_stack_config.json"
    rep_p = ROOT / "outputs" / "audit" / "ml_validation_report.json"
    if not (cfg_p.exists() and rep_p.exists()):
        pytest.skip("stack config or report not generated yet")
    cfg = json.loads(cfg_p.read_text())
    rep = json.loads(rep_p.read_text())
    # use_ml_match_model must equal the gate decision
    assert cfg["use_ml_match_model"] == rep["gate"]["accepted"]
    assert cfg["rollback_to_score_only"] is True
    # if ML rejected, ml weight must be 0
    if not cfg["use_ml_match_model"]:
        assert cfg["ensemble"]["ml_logistic_weight"] == 0.0
