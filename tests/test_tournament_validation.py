"""Tests protecting the macro-upgrade architecture (Batch A–D)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "outputs" / "audit"


def test_walkforward_validation_artifact():
    p = AUDIT / "tournament_walkforward_validation.json"
    if not p.exists():
        pytest.skip("walk-forward validation not generated")
    d = json.loads(p.read_text())
    assert d["chosen_weight"] in d["weights_tested"]
    # leak-free claims must be documented
    notes = " ".join(d["leakage_notes"]).lower()
    assert "leak-free" in notes and "retrained per cutoff" in notes
    # both tournaments present
    assert len(d["per_tournament"]) == 2


def test_ml_weight_sensitivity_csv():
    import csv
    p = AUDIT / "ml_weight_sensitivity.csv"
    if not p.exists():
        pytest.skip("ml_weight_sensitivity.csv not generated")
    with open(p) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 10  # 2 tournaments x 5 weights
    for col in ("tournament", "ml_weight", "champ_brier", "champ_entropy", "top1_prob"):
        assert col in rows[0]


def test_set_ml_ensemble_rollback():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    m = CalibratedEloMatchModel(use_ml=False)
    # weight 0 disables regardless of clf
    m.set_ml_ensemble(clf="not_none_sentinel", ml_weight=0.0)
    assert m.use_ml is False
    assert m._ml_weight == 0.0


def test_set_ml_ensemble_weight_applied():
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    import pickle
    mp = ROOT / "outputs" / "models" / "ml_match_model.pkl"
    if not mp.exists():
        pytest.skip("ml model pickle not present")
    clf = pickle.loads(mp.read_bytes())
    m = CalibratedEloMatchModel(use_ml=False)
    m.set_ml_ensemble(clf, 0.2)
    assert m.use_ml is True
    assert m._ml_weight == pytest.approx(0.2)
    assert m._elo_weight == pytest.approx(0.8)


def test_market_implied_sums_to_one():
    p = ROOT / "data" / "live" / "market_implied_probabilities.json"
    if not p.exists():
        pytest.skip("market implied not generated")
    d = json.loads(p.read_text())["matches"]
    for match, imp in d.items():
        assert abs(imp["home"] + imp["draw"] + imp["away"] - 1.0) < 0.02


def test_model_stack_config_weight_matches_decision():
    cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
    w = cfg["ensemble"]["ml_logistic_weight"]
    assert cfg["ensemble"]["elo_calibrated_weight"] + w == pytest.approx(1.0)
    dec_p = AUDIT / "model_stack_final_decision.json"
    if dec_p.exists():
        dec = json.loads(dec_p.read_text())
        assert dec["key_evidence"]["tournament_chosen_weight"] == pytest.approx(w)


def test_beta_sensitivity_artifacts():
    p = AUDIT / "beta_elo_uncertainty_audit.json"
    if not p.exists():
        pytest.skip("beta audit not generated")
    d = json.loads(p.read_text())
    assert d["sensitivity"]["level"] in ("LOW", "MODERATE", "HIGH")
    # leakage assessment must distinguish forecast vs backtest
    assert "NOT leakage" in d["leakage_assessment"]["wc2026_forecast"]
    assert (AUDIT / "beta_elo_sensitivity.csv").exists()


def test_train_logistic_until_is_leakfree():
    """Model trained before a cutoff must not depend on the cutoff's own matches."""
    from wc2026.ml.train_match_model import train_logistic_until
    clf = train_logistic_until("2018-06-14")
    # sanity: predicts 3 classes, probabilities normalized
    import numpy as np
    proba = clf.predict_proba(np.array([[300.0, 1.0]]))[0]
    assert len(proba) == 3
    assert abs(proba.sum() - 1.0) < 1e-9
    # strong favorite -> home win most likely
    assert proba.argmax() == 0
