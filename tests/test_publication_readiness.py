"""Tests protecting publication-grade + deployment-readiness artifacts (Batch A–H)."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "outputs" / "audit"
DEPLOY = ROOT / "outputs" / "deploy"
PUBLIC = ROOT / "outputs" / "public"


# ── A: reproducibility ───────────────────────────────────────────────────────

def test_reproducibility_script_exists():
    assert (ROOT / "scripts" / "rebuild_publication_forecast.py").exists()


def test_reproducibility_pack_smoke_passed():
    p = AUDIT / "reproducibility_pack.json"
    if not p.exists():
        pytest.skip("pack not generated")
    d = json.loads(p.read_text())
    assert d["smoke_result"]["smoke_pass"] is True
    assert d["smoke_result"]["conservation_ok"] is True
    assert "NONE" in d["env_required_for_reproduction"]


# ── C: model card ────────────────────────────────────────────────────────────

def test_model_card_sections():
    p = AUDIT / "model_card_public.md"
    assert p.exists()
    txt = p.read_text().lower()
    for section in ["purpose", "intended use", "not intended", "limitation",
                    "uncertainty", "failure mode", "data source"]:
        assert section in txt, f"model card missing '{section}'"


# ── B: data lineage ──────────────────────────────────────────────────────────

def test_data_lineage_covers_key_numbers():
    p = AUDIT / "data_lineage_map.json"
    assert p.exists()
    nums = " ".join(x["number"].lower() for x in json.loads(p.read_text())["lineage"])
    for key in ["champion probability", "interval", "xg", "odds", "ml validation",
                "tournament validation", "beta", "market", "maturity"]:
        assert key in nums, f"lineage missing '{key}'"


# ── D: reviewer audit ────────────────────────────────────────────────────────

def test_reviewer_attack_audit():
    p = AUDIT / "reviewer_attack_audit.json"
    assert p.exists()
    d = json.loads(p.read_text())
    assert d["n_objections"] >= 20
    for o in d["objections"]:
        assert o["severity"] in ("LOW", "MEDIUM", "HIGH")
        assert o["action_needed"]


# ── E: stale claims gone ─────────────────────────────────────────────────────

def test_readme_not_stale():
    txt = (ROOT / "README.md").read_text()
    assert "278 automated tests" not in txt and "278 tests" not in txt
    assert "571" in txt
    assert "0.20" in txt  # current ML weight mentioned


def test_artifact_consistency_canonical():
    p = AUDIT / "artifact_consistency_audit.json"
    assert p.exists()
    c = json.loads(p.read_text())["canonical_truth"]
    assert c["ml_weight"] == 0.20
    assert c["tests"] >= 558  # current truth: 571 (allow growth)


# ── G: deployment ────────────────────────────────────────────────────────────

def test_deployment_audits_exist():
    for f in ["domain_dns_audit.json", "deployment_architecture_audit.json",
              "deploy_readiness_checklist.md", "env_var_inventory.md", "runbook.md",
              "portfolio_architecture_plan.md"]:
        assert (DEPLOY / f).exists(), f"missing deploy/{f}"


def test_dns_audit_made_no_changes():
    d = json.loads((DEPLOY / "domain_dns_audit.json").read_text())
    assert "no DNS changes" in d["no_action_taken"].lower() or "read-only" in d["no_action_taken"].lower()


def test_env_inventory_has_no_secret_values():
    txt = (DEPLOY / "env_var_inventory.md").read_text()
    # names must be present
    assert "THESTATSAPI_KEY" in txt and "API_FOOTBALL_KEY" in txt
    # no actual key-like values (fapi_ prefix, or 32+ char hex/alnum tokens)
    assert "fapi_" not in txt
    assert not re.search(r"=\s*[A-Za-z0-9]{24,}", txt)


def test_env_is_gitignored():
    gi = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in [line.strip() for line in gi]


# ── H: portfolio ─────────────────────────────────────────────────────────────

def test_portfolio_case_study_exists():
    for f in ["portfolio_wc2026_case_study.md", "portfolio_wc2026_short.md",
              "linkedin_wc2026_project_post.md", "project_readme_public.md"]:
        assert (PUBLIC / f).exists(), f"missing public/{f}"


def test_public_docs_no_overclaim():
    forbidden = ["guaranteed", "perfect model", "unbeatable", "institutional-grade",
                 "more than opta", "quantum"]
    for f in PUBLIC.glob("portfolio_*.md"):
        low = f.read_text().lower()
        for w in forbidden:
            assert w not in low, f"{f.name} contains forbidden '{w}'"
    # model card too
    mc = (AUDIT / "model_card_public.md").read_text().lower()
    for w in forbidden:
        assert w not in mc
