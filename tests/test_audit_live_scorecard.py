"""Phase 1B guarantees for the scorecard metric audit:
- it is DETERMINISTIC (same input → identical metrics),
- metrics are in valid bounds / internally consistent,
- it is READ-ONLY: running it does NOT modify any model / config / forecast / live data file.
"""
import hashlib
import importlib.util
from pathlib import Path

import pytest

from wc2026.scorecard import get_model_and_teams

ROOT = Path(__file__).resolve().parents[1]

# load scripts/audit_live_scorecard.py by path (scripts/ is not a package)
_spec = importlib.util.spec_from_file_location("audit_live_scorecard", ROOT / "scripts" / "audit_live_scorecard.py")
audit_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit_mod)

FIXED = [
    {"home": "ESP", "away": "RSA", "home_goals": 2, "away_goals": 0, "group": "X"},
    {"home": "BRA", "away": "MAR", "home_goals": 1, "away_goals": 1, "group": "Y"},
    {"home": "USA", "away": "PAR", "home_goals": 4, "away_goals": 1, "group": "Z"},
    {"home": "QAT", "away": "SUI", "home_goals": 1, "away_goals": 1, "group": "W"},
]

_PROTECTED = [
    "data/model_stack_config.json", "data/elo_calibrated_params.json", "data/elo_live_params.json",
    "src/wc2026/calibrated_elo_model.py", "src/wc2026/scorecard.py", "data/wc2026_live.json",
]


@pytest.fixture(scope="module")
def engine():
    return get_model_and_teams()


def test_audit_is_deterministic(engine):
    model, teams = engine
    a1 = audit_mod.compute_audit(FIXED, model, teams)
    a2 = audit_mod.compute_audit(FIXED, model, teams)
    assert a1 == a2


def test_audit_metrics_in_bounds(engine):
    model, teams = engine
    a = audit_mod.compute_audit(FIXED, model, teams)
    assert a["n_matches"] == len(FIXED)
    for k in ("outcome_accuracy", "rps", "rps_uniform_baseline",
              "exact_top1", "exact_top3", "exact_top5", "exact_top10"):
        assert 0.0 <= a[k] <= 1.0, k
    # nested top-k must be monotone, rank >= 1
    assert a["exact_top1"] <= a["exact_top3"] <= a["exact_top5"] <= a["exact_top10"]
    assert a["avg_rank_real_score"] >= 1.0
    # confusion matrix counts sum to n
    assert sum(sum(row) for row in a["confusion_matrix_pred_x_actual"]["counts"]) == a["n_matches"]


def test_audit_does_not_modify_model_or_config(engine):
    model, teams = engine

    def shas():
        return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in _PROTECTED}

    before = shas()
    audit_mod.compute_audit(FIXED, model, teams)          # measure only
    audit_mod._load_completed(None)                       # read the live json
    after = shas()
    assert before == after, "audit must not modify any model/config/forecast/live file"
