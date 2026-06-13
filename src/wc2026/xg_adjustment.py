"""Bounded live xG adjustment for Elo updates.

Live-conditioning ONLY. This does NOT train a model on xG, does NOT replace goals
with xG, and does NOT modify beta_elo. It applies a small, capped correction to the
score-based Elo delta based on the gap between the xG margin and the score margin.

Rationale: a team that wins by more goals than its xG warranted (finishing variance /
keeper errors / late penalty) gets its Elo gain *reduced*, not reversed. A team that
created more than it scored gets a small boost. The cap (+/-8 Elo/match) guarantees that
with the current tiny sample (4 matches) no single result can swing champion
probabilities by more than ~1pp.

Formula:
    score_margin    = home_goals - away_goals
    xg_margin       = xg_home - xg_away
    performance_gap = xg_margin - score_margin
    xg_delta        = clamp(weight * performance_gap, -max_abs_delta, +max_abs_delta)

xg_delta is ADDED to the home team's net Elo change and SUBTRACTED from the away team's.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class XGAdjustmentConfig:
    enabled: bool = True
    weight_per_xg_margin: float = 6.0
    max_abs_delta: float = 8.0
    missing_xg_behavior: str = "score_only"  # "score_only" => no adjustment when xG missing
    apply_to_completed_matches_only: bool = True
    do_not_modify_beta_elo: bool = True
    guardrail_max_champion_pp_move: float = 1.0

    @classmethod
    def from_file(cls, path: str | Path) -> "XGAdjustmentConfig":
        data = json.loads(Path(path).read_text())
        fields = {
            "enabled", "weight_per_xg_margin", "max_abs_delta",
            "missing_xg_behavior", "apply_to_completed_matches_only",
            "do_not_modify_beta_elo", "guardrail_max_champion_pp_move",
        }
        return cls(**{k: v for k, v in data.items() if k in fields})


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_xg_delta(
    home_goals: int,
    away_goals: int,
    xg_home: Optional[float],
    xg_away: Optional[float],
    config: Optional[XGAdjustmentConfig] = None,
) -> float:
    """Return the bounded Elo correction to ADD to the home team's net Elo change.

    Returns 0.0 when adjustment is disabled or xG is missing (score_only behavior).
    Always within [-max_abs_delta, +max_abs_delta].
    """
    cfg = config or XGAdjustmentConfig()
    if not cfg.enabled:
        return 0.0
    if xg_home is None or xg_away is None:
        # missing_xg_behavior: score_only => no correction
        return 0.0
    score_margin = home_goals - away_goals
    xg_margin = float(xg_home) - float(xg_away)
    performance_gap = xg_margin - score_margin
    raw = cfg.weight_per_xg_margin * performance_gap
    return _clamp(raw, -cfg.max_abs_delta, cfg.max_abs_delta)


def explain_xg_delta(
    home: str,
    away: str,
    home_goals: int,
    away_goals: int,
    xg_home: Optional[float],
    xg_away: Optional[float],
    config: Optional[XGAdjustmentConfig] = None,
) -> dict:
    """Return a per-match record describing the adjustment (for the audit log)."""
    cfg = config or XGAdjustmentConfig()
    delta = compute_xg_delta(home_goals, away_goals, xg_home, xg_away, cfg)
    has_xg = xg_home is not None and xg_away is not None
    score_margin = home_goals - away_goals
    xg_margin = (float(xg_home) - float(xg_away)) if has_xg else None
    performance_gap = (xg_margin - score_margin) if has_xg else None
    capped = has_xg and abs(cfg.weight_per_xg_margin * performance_gap) > cfg.max_abs_delta
    return {
        "home": home,
        "away": away,
        "score": f"{home_goals}-{away_goals}",
        "score_margin": score_margin,
        "xg_home": xg_home,
        "xg_away": xg_away,
        "xg_margin": round(xg_margin, 3) if xg_margin is not None else None,
        "performance_gap": round(performance_gap, 3) if performance_gap is not None else None,
        "xg_delta_elo": round(delta, 3),
        "capped": capped,
        "has_xg": has_xg,
        "direction": (
            "home_gain_reduced" if delta < 0 else
            "home_gain_boosted" if delta > 0 else
            "no_change"
        ),
    }
