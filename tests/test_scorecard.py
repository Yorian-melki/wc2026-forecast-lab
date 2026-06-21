"""Locks the scorecard scoring math (the 'absolument véridique' formula)."""
import numpy as np

from wc2026.scorecard import _rps_ordered, _wdl_from_flat, compute_scorecard


def test_rps_known_values():
    # Perfect prediction of the outcome -> RPS 0.
    assert _rps_ordered((1.0, 0.0, 0.0), 0) == 0.0
    # Uniform 1/3 on a home win -> 5/18 ; on a draw -> 1/9 (standard ordered-RPS values).
    assert abs(_rps_ordered((1 / 3, 1 / 3, 1 / 3), 0) - 5 / 18) < 1e-9
    assert abs(_rps_ordered((1 / 3, 1 / 3, 1 / 3), 1) - 1 / 9) < 1e-9
    assert 0.0 <= _rps_ordered((0.2, 0.3, 0.5), 2) <= 1.0


def test_wdl_partition_sums_to_one():
    flat = np.array([0.1, 0.2, 0.05, 0.15, 0.1, 0.05, 0.1, 0.1, 0.15])  # 3x3, sums to 1
    h, d, a = _wdl_from_flat(flat, 3)
    assert abs(h + d + a - 1.0) < 1e-9
    # rows = home goals: index (1,0)=0.15 and (2,0),(2,1) are home wins -> home>0
    assert h > 0 and d > 0 and a > 0


def test_compute_scorecard_end_to_end():
    completed = [{"home": "ESP", "away": "RSA", "home_goals": 2, "away_goals": 0, "group": "X"}]
    sc = compute_scorecard(completed)
    s = sc["summary"]
    assert s["n_matches"] == 1
    for k in ("mean_prob_actual_score", "outcome_accuracy", "mean_rps",
              "exact_hit_top1", "exact_hit_top3", "rps_baseline_uniform"):
        assert 0.0 <= s[k] <= 1.0
    m = sc["matches"][0]
    assert m["rank"] >= 1 and len(m["top_scores"]) == 5
    assert m["score"] == "2-0"
