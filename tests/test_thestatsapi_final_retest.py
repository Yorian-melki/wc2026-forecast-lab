"""Tests for the TheStatsAPI final-retest audit + extracted artifacts (Phase 1)."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "outputs" / "audit"
LIVE = ROOT / "data" / "live"


def test_retest_audit_active_status():
    p = AUDIT / "thestatsapi_final_retest.json"
    if not p.exists():
        pytest.skip("thestatsapi_final_retest.json not generated")
    a = json.loads(p.read_text())
    assert a["final_status"] == "ACTIVE_CONFIRMED_AFTER_STATS_API_SUBSCRIPTION"
    # honest independence caveat must be present
    assert "xg_independence_finding" in a
    assert a["xg_independence_finding"]["honest_label"] == "single_upstream_xg_likely"


def test_status_file_consistent():
    p = LIVE / "thestatsapi_status.json"
    if not p.exists():
        pytest.skip("thestatsapi_status.json not generated")
    s = json.loads(p.read_text())
    assert s["status"] == "ACTIVE_CONFIRMED_AFTER_STATS_API_SUBSCRIPTION"
    assert s["xg_available"] is True
    assert s["per_shot_xg"] is True


def test_shotmap_has_per_shot_xg_and_coords():
    p = LIVE / "thestatsapi_shotmap.json"
    if not p.exists():
        pytest.skip("thestatsapi_shotmap.json not generated")
    data = json.loads(p.read_text())["matches"]
    # at least one match with shots carrying xG + coordinates
    found = False
    for mid, shots in data.items():
        if shots:
            s = shots[0]
            assert "expected_goals" in s and "x" in s and "y" in s
            found = True
            break
    assert found, "no shotmap shots found"


def test_xg_cross_check_documents_upstream_overlap():
    p = AUDIT / "xg_cross_check.json"
    if not p.exists():
        pytest.skip("xg_cross_check.json not generated")
    rows = json.loads(p.read_text())["matches"]
    # On at least 2 matches, TSA team-xG equals Highlightly xG (same upstream signal)
    exact = 0
    for r in rows:
        tt = r.get("tsa_team")
        hl = r.get("highlightly")
        if tt and hl and tt[0] == hl[0] and tt[1] == hl[1]:
            exact += 1
    assert exact >= 2, f"expected >=2 exact TSA==Highlightly xG matches, got {exact}"


def test_odds_implied_probs_normalized():
    p = LIVE / "thestatsapi_odds_implied.json"
    if not p.exists():
        pytest.skip("thestatsapi_odds_implied.json not generated")
    rows = json.loads(p.read_text())["matches"]
    for r in rows:
        imp = r["implied"]
        assert abs(imp["home"] + imp["draw"] + imp["away"] - 1.0) < 0.02
