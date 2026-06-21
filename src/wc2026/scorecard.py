"""Live model scorecard — how well the model's PRE-MATCH score forecasts match reality.

For every finished (and in-progress) WC2026 match we take the SAME scoreline distribution the
model simulates (`CalibratedEloMatchModel.scoreline_probs`) and measure where the real score
falls in it:

  • p_actual  — probability the model assigned to the score that actually happened
  • rank      — where the real score sits among ALL predicted scorelines (1 = the model's #1 pick)
  • top1/top3 — was the real score the model's most-likely / in its top-3 scorelines
  • outcome   — was the most-likely result (home win / draw / away win) correct
  • RPS       — Ranked Probability Score over the ordered W/D/L outcome (the standard proper
                scoring rule for football forecasts; lower = better)

Everything accumulates across the tournament and updates live as scores change. Honest by
construction: we judge the FULL ranked distribution (not just the single likeliest score), and
we report RPS next to the same-matches uniform-1/3 baseline — no inflated 'skill %'.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


def _wdl_from_flat(flat: np.ndarray, g: int) -> tuple[float, float, float]:
    """(P home win, P draw, P away win) from a flat g×g scoreline grid (rows = home goals)."""
    m = flat.reshape(g, g)
    home = float(np.tril(m, -1).sum())   # home goals > away goals
    draw = float(np.trace(m))
    away = float(np.triu(m, 1).sum())    # home goals < away goals
    return home, draw, away


def _rps_ordered(p: tuple[float, float, float], outcome: int) -> float:
    """RPS for 3 ordered categories (home, draw, away). outcome in {0,1,2}. Range [0,1], lower better."""
    obs = [0.0, 0.0, 0.0]
    obs[outcome] = 1.0
    cum_p = cum_o = s = 0.0
    for k in range(2):  # first 2 of the 3 ordered categories
        cum_p += p[k]
        cum_o += obs[k]
        s += (cum_p - cum_o) ** 2
    return s / 2.0


def score_match(model, teams: dict, home: str, away: str, ha: int, ab: int,
                knockout: bool = False) -> Optional[dict]:
    """Score one real result against the model's pre-match scoreline distribution."""
    if home not in teams or away not in teams:
        return None
    flat = model.scoreline_probs(teams[home], teams[away], knockout=knockout)
    g = int(round(len(flat) ** 0.5))
    cap = g - 1
    idx = min(ha, cap) * g + min(ab, cap)
    p_actual = float(flat[idx])
    order = np.argsort(flat)[::-1]                       # most-likely scoreline first
    rank = int(np.where(order == idx)[0][0]) + 1
    top = [{"s": f"{int(o // g)}-{int(o % g)}", "p": float(flat[o])} for o in order[:5]]
    p_wdl = _wdl_from_flat(flat, g)
    actual_outcome = 0 if ha > ab else (1 if ha == ab else 2)
    return {
        "home": home, "away": away, "score": f"{ha}-{ab}",
        "p_actual": p_actual, "rank": rank, "top_scores": top,
        "outcome_ok": int(np.argmax(p_wdl)) == actual_outcome,
        "p_wdl": {"home": p_wdl[0], "draw": p_wdl[1], "away": p_wdl[2]},
        "rps": _rps_ordered(p_wdl, actual_outcome),
        "rps_uniform": _rps_ordered((1 / 3, 1 / 3, 1 / 3), actual_outcome),
    }


def predicted_scores(model, teams: dict, home: str, away: str, k: int = 3,
                     knockout: bool = False) -> list[dict]:
    """Top-k most-likely scorelines for a fixture (used for upcoming matches with no result yet)."""
    if home not in teams or away not in teams:
        return []
    flat = model.scoreline_probs(teams[home], teams[away], knockout=knockout)
    g = int(round(len(flat) ** 0.5))
    order = np.argsort(flat)[::-1][:k]
    return [{"s": f"{int(o // g)}-{int(o % g)}", "p": float(flat[o])} for o in order]


def get_model_and_teams():
    """Build the production model + pre-tournament teams (cache this at the app layer)."""
    from .calibrated_elo_model import CalibratedEloMatchModel
    from .data_loader import load_teams
    return CalibratedEloMatchModel(use_ml=None), load_teams(apply_temporal_form=True)


def compute_scorecard(completed, live=None, model=None, teams=None) -> dict:
    """Accumulate the scorecard over completed (and optionally live in-progress) matches."""
    if model is None:
        from .calibrated_elo_model import CalibratedEloMatchModel
        model = CalibratedEloMatchModel(use_ml=None)
    if teams is None:
        from .data_loader import load_teams
        teams = load_teams(apply_temporal_form=True)

    rows = []
    for m in (completed or []):
        if m.get("home_goals") is None:
            continue
        r = score_match(model, teams, m["home"], m["away"],
                        int(m["home_goals"]), int(m["away_goals"]), knockout=not m.get("group"))
        if r:
            r["live"] = False
            rows.append(r)
    for m in (live or []):
        if m.get("home_goals") is None:
            continue
        r = score_match(model, teams, m["home"], m["away"],
                        int(m["home_goals"]), int(m["away_goals"]), knockout=not m.get("group"))
        if r:
            r["live"] = True
            r["minute"] = m.get("minute")
            rows.append(r)

    fin = [r for r in rows if not r["live"]]
    n = len(fin)

    def avg(key):
        return float(np.mean([r[key] for r in fin])) if n else 0.0

    summary = {
        "n_matches": n,
        "n_live": sum(1 for r in rows if r["live"]),
        "mean_prob_actual_score": avg("p_actual"),
        "exact_hit_top1": (sum(r["rank"] == 1 for r in fin) / n) if n else 0.0,
        "exact_hit_top3": (sum(r["rank"] <= 3 for r in fin) / n) if n else 0.0,
        "mean_score_rank": avg("rank"),
        "outcome_accuracy": (sum(r["outcome_ok"] for r in fin) / n) if n else 0.0,
        "mean_rps": avg("rps"),
        "rps_baseline_uniform": avg("rps_uniform"),
    }
    return {
        "summary": summary,
        "best": max(fin, key=lambda r: r["p_actual"], default=None),
        "worst": min(fin, key=lambda r: r["p_actual"], default=None),
        "matches": sorted(rows, key=lambda r: (not r["live"], r["rank"])),  # live first, then best-ranked
    }
