"""Read-only model version manifest + helpers for the version/changelog UI panel.

PURE METADATA. This module reads files; it never touches model math, probabilities, or forecast
generation. It exists so the app can show users which engine/parameters are live and what changed,
and so releases are archived + rollback-able (Phase 1A versioning infrastructure).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = ROOT / "configs" / "model_version.json"
_CHANGELOG = ROOT / "CHANGELOG_MODEL.md"
_CONFIG = ROOT / "data" / "model_stack_config.json"
_PARAMS = ROOT / "data" / "elo_calibrated_params.json"


def get_manifest() -> dict:
    """The version manifest (configs/model_version.json). Empty dict if missing."""
    try:
        return json.loads(_MANIFEST.read_text())
    except Exception:
        return {}


def get_active_config() -> dict:
    """The LIVE computational config + key params, read-only, for display only."""
    out: dict = {}
    try:
        cfg = json.loads(_CONFIG.read_text())
        out["use_ml_match_model"] = cfg.get("use_ml_match_model")
        out["use_xg_live_adjustment"] = cfg.get("use_xg_live_adjustment")
        out["ml_weight"] = (cfg.get("ensemble") or {}).get("ml_logistic_weight")
    except Exception:
        pass
    try:
        p = json.loads(_PARAMS.read_text())
        out["beta_elo"] = p.get("beta_elo")
        out["rho"] = p.get("rho")
        out["log_base"] = p.get("log_base")
    except Exception:
        pass
    return out


def get_changelog(max_chars: int = 8000) -> str:
    """The model changelog markdown (CHANGELOG_MODEL.md), truncated for the panel."""
    try:
        return _CHANGELOG.read_text()[:max_chars]
    except Exception:
        return ""
