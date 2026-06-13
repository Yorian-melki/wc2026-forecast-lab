"""Schema + safety tests for data/model_stack_config.json."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_stack_config_schema():
    p = ROOT / "data" / "model_stack_config.json"
    if not p.exists():
        pytest.skip("model_stack_config.json not generated")
    c = json.loads(p.read_text())
    for key in ["use_xg_live_adjustment", "use_ml_match_model",
                "use_isotonic_calibrator", "ensemble", "rollback_to_score_only"]:
        assert key in c
    assert isinstance(c["use_ml_match_model"], bool)
    # rollback must always be available
    assert c["rollback_to_score_only"] is True
    # ensemble weights present and non-negative
    e = c["ensemble"]
    assert e["elo_calibrated_weight"] >= 0
    assert e["ml_logistic_weight"] >= 0


def test_xg_adjustment_never_modifies_beta_elo():
    p = ROOT / "data" / "xg_adjustment_config.json"
    c = json.loads(p.read_text())
    assert c["do_not_modify_beta_elo"] is True
    assert "beta_elo" not in c
