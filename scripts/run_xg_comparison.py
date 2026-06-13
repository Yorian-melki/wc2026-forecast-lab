#!/usr/bin/env python3
"""Phase 3 — Score-only vs xG-adjusted live simulation comparison.

Runs two live-conditioned Monte Carlo simulations that are IDENTICAL except for the
live Elo update rule:
  - score_only : Elo updated from goals only (existing pipeline).
  - xg_adjusted: same, plus a bounded xG correction (xg_adjustment.compute_xg_delta).

Both use the same model, same seed (common random numbers), same iterations, and the
same locked group results. The only difference is each team's elo_current. This isolates
the xG adjustment's effect on champion / stage probabilities.

Outputs:
  outputs/live/score_only/stage_probs.csv
  outputs/live/xg_adjusted/stage_probs.csv
  outputs/audit/xg_probability_delta.csv
  outputs/audit/xg_probability_delta.md
  outputs/audit/xg_adjustment_audit.{md,json}
  data/live/xg_adjustment_log.json

Guardrail: if any champion probability moves by more than
config.guardrail_max_champion_pp_move (default 1.0pp), the run FAILS the audit and
prints a recommendation to reduce the coefficient.
"""
from __future__ import annotations

import json
import sys
import time
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.data_loader import load_teams, load_config
from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
from wc2026.tournament import TournamentSimulator
from wc2026.group_rules import PlayedMatch
from wc2026.live_state import LiveState, LiveMatchResult
from wc2026.xg_adjustment import XGAdjustmentConfig, compute_xg_delta, explain_xg_delta

from datetime import date

LIVE_FILE = ROOT / "data" / "wc2026_live.json"
GROUPS_FILE = ROOT / "data" / "groups.json"
XG_CFG_FILE = ROOT / "data" / "xg_adjustment_config.json"

K_FACTOR = 40


def elo_update(elo_a, elo_b, goals_a, goals_b, k=K_FACTOR):
    """Score-based Elo delta with FiveThirtyEight-style MOV multiplier.

    Returns (delta_a, mov_mul). delta_a is added to A, subtracted from B.
    """
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    if goals_a > goals_b:
        score_a, margin = 1.0, goals_a - goals_b
    elif goals_a < goals_b:
        score_a, margin = 0.0, goals_b - goals_a
    else:
        score_a, margin = 0.5, 0
    if margin == 0:
        mov_mul = 1.0
    else:
        elo_diff = elo_a - elo_b if goals_a > goals_b else elo_b - elo_a
        mov_mul = np.log(margin + 1) * (2.2 / (elo_diff * 0.001 + 2.2))
        mov_mul = max(1.0, mov_mul)
    return k * mov_mul * (score_a - expected_a), mov_mul


def build_live_state(completed) -> LiveState:
    state = LiveState(fetched_at=datetime.now())
    for m in completed:
        grp = m.get("group")
        r = LiveMatchResult(
            team1=m["home"], team2=m["away"],
            goals1=m["home_goals"], goals2=m["away_goals"],
            group=grp, round_name="Matchday 1", decided_in="90",
            match_date=date.fromisoformat(m.get("date", "2026-06-11")) if m.get("date") else date(2026, 6, 11),
        )
        state.completed.append(r)
        if grp:
            state.group_results.setdefault(grp, []).append(
                PlayedMatch(team_a=m["home"], team_b=m["away"],
                            goals_a=m["home_goals"], goals_b=m["away_goals"],
                            conduct_a=0, conduct_b=0)
            )
    return state


def updated_elos(base_elos, completed, xg_cfg, apply_xg: bool):
    """Return (elos_dict, per_match_log)."""
    elos = dict(base_elos)
    log = []
    for m in completed:
        ha, hb = m["home"], m["away"]
        ga, gb = m["home_goals"], m["away_goals"]
        ea, eb = elos.get(ha, 1500), elos.get(hb, 1500)
        base_delta, mov = elo_update(ea, eb, ga, gb)
        xg_delta = 0.0
        rec = explain_xg_delta(ha, hb, ga, gb, m.get("xg_home"), m.get("xg_away"), xg_cfg)
        if apply_xg:
            xg_delta = compute_xg_delta(ga, gb, m.get("xg_home"), m.get("xg_away"), xg_cfg)
        total_delta = base_delta + xg_delta
        elos[ha] = ea + total_delta
        elos[hb] = eb - total_delta
        rec.update({
            "base_score_delta": round(base_delta, 3),
            "mov_mul": round(mov, 3),
            "elo_home_before": round(ea, 1),
            "elo_home_after_score_only": round(ea + base_delta, 1),
            "elo_home_after_xg_adjusted": round(ea + base_delta + rec["xg_delta_elo"], 1),
        })
        log.append(rec)
    return elos, log


def run_mode(base_teams, groups, base_params, cfg, live_state, elos, n, seed):
    # Fresh model per mode: _dc_cache must not bleed between Elo sets.
    params = deepcopy(base_params)
    params["team_elos"] = {k: round(v, 4) for k, v in elos.items()}
    model = CalibratedEloMatchModel(config=cfg, params=params)
    sim = TournamentSimulator(teams=base_teams, groups=groups, model=model)
    art = sim.simulate_many_live(iterations=n, seed=seed, live_state=live_state)
    return art.summary


def main(n=100_000, seed=20260613):
    t0 = time.monotonic()
    live = json.loads(LIVE_FILE.read_text())
    completed = live.get("completed_matches", [])
    groups = json.loads(GROUPS_FILE.read_text())
    xg_cfg = XGAdjustmentConfig.from_file(XG_CFG_FILE)
    cfg = load_config()

    base_teams = load_teams(apply_temporal_form=True)
    base_params = load_calibrated_params()
    base_elos = {k: float(v) for k, v in base_params["team_elos"].items()}

    live_state = build_live_state(completed)

    elos_score, log_score = updated_elos(base_elos, completed, xg_cfg, apply_xg=False)
    elos_xg, log_xg = updated_elos(base_elos, completed, xg_cfg, apply_xg=True)

    print(f"Running {n:,} sims x2 (score_only, xg_adjusted), seed={seed} ...")
    sum_score = run_mode(base_teams, groups, base_params, cfg, live_state, elos_score, n, seed)
    sum_xg = run_mode(base_teams, groups, base_params, cfg, live_state, elos_xg, n, seed)

    out_so = ROOT / "outputs" / "live" / "score_only"
    out_xg = ROOT / "outputs" / "live" / "xg_adjusted"
    out_so.mkdir(parents=True, exist_ok=True)
    out_xg.mkdir(parents=True, exist_ok=True)
    sum_score.to_csv(out_so / "stage_probs.csv", index=False)
    sum_xg.to_csv(out_xg / "stage_probs.csv", index=False)

    # Delta table
    a = sum_score[["team", "champion_prob", "final_prob", "sf_prob"]].rename(
        columns={"champion_prob": "champ_score", "final_prob": "final_score", "sf_prob": "sf_score"})
    b = sum_xg[["team", "champion_prob", "final_prob", "sf_prob"]].rename(
        columns={"champion_prob": "champ_xg", "final_prob": "final_xg", "sf_prob": "sf_xg"})
    d = a.merge(b, on="team")
    d["champ_delta_pp"] = (d["champ_xg"] - d["champ_score"]) * 100
    d["final_delta_pp"] = (d["final_xg"] - d["final_score"]) * 100
    d = d.sort_values("champ_xg", ascending=False).reset_index(drop=True)
    d.to_csv(ROOT / "outputs" / "audit" / "xg_probability_delta.csv", index=False)

    max_move = d["champ_delta_pp"].abs().max()
    guardrail = xg_cfg.guardrail_max_champion_pp_move
    passed = max_move <= guardrail

    # Elo deltas for log
    elo_delta_summary = {c: round(elos_xg[c] - elos_score[c], 2)
                         for c in elos_xg if abs(elos_xg[c] - elos_score[c]) > 0.01}

    # xg_adjustment_log.json
    (ROOT / "data" / "live" / "xg_adjustment_log.json").write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "weight_per_xg_margin": xg_cfg.weight_per_xg_margin,
            "max_abs_delta": xg_cfg.max_abs_delta,
            "enabled": xg_cfg.enabled,
        },
        "per_match": log_xg,
        "elo_delta_xg_vs_score": elo_delta_summary,
    }, indent=2))

    # Markdown
    top = d.head(12)
    lines = ["# xG Probability Delta — score-only vs xG-adjusted", "",
             f"Generated: {datetime.now(timezone.utc).isoformat()[:19]}  ·  N={n:,}  ·  seed={seed} (common random numbers)",
             f"Config: weight={xg_cfg.weight_per_xg_margin}, cap=±{xg_cfg.max_abs_delta} Elo/match", "",
             f"**Max |champion Δ|: {max_move:.3f} pp**  ·  guardrail {guardrail} pp  ·  "
             f"**{'PASS' if passed else 'FAIL'}**", "",
             "| Team | Champ score-only | Champ xG-adj | Δpp | Elo Δ |", "|---|---|---|---|---|"]
    for _, r in top.iterrows():
        ed = elo_delta_summary.get(r["team"], 0.0)
        lines.append(f"| {r['team']} | {r['champ_score']*100:.2f}% | {r['champ_xg']*100:.2f}% | "
                     f"{r['champ_delta_pp']:+.3f} | {ed:+.1f} |")
    lines += ["", "## Per-match xG adjustment", "",
              "| Match | Score | xG | perf_gap | xG Δ Elo | capped | direction |",
              "|---|---|---|---|---|---|---|"]
    for rec in log_xg:
        lines.append(f"| {rec['home']}-{rec['away']} | {rec['score']} | "
                     f"{rec['xg_home']}-{rec['xg_away']} | {rec['performance_gap']} | "
                     f"{rec['xg_delta_elo']:+.2f} | {rec['capped']} | {rec['direction']} |")
    if not passed:
        lines += ["", f"## GUARDRAIL FAILED",
                  f"Max champion move {max_move:.3f}pp > {guardrail}pp. Reduce weight_per_xg_margin "
                  f"in data/xg_adjustment_config.json and rerun. Suggested: "
                  f"{xg_cfg.weight_per_xg_margin * guardrail / max_move:.2f}"]
    (ROOT / "outputs" / "audit" / "xg_probability_delta.md").write_text("\n".join(lines))

    # Audit json + md
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n": n, "seed": seed,
        "config": {"weight_per_xg_margin": xg_cfg.weight_per_xg_margin,
                   "max_abs_delta": xg_cfg.max_abs_delta},
        "max_champion_move_pp": round(float(max_move), 4),
        "guardrail_pp": guardrail,
        "guardrail_passed": bool(passed),
        "default_mode_recommendation": "xg_adjusted" if passed else "score_only",
        "n_matches_with_xg": sum(1 for r in log_xg if r["has_xg"]),
        "elo_delta_xg_vs_score": elo_delta_summary,
    }
    (ROOT / "outputs" / "audit" / "xg_adjustment_audit.json").write_text(json.dumps(audit, indent=2))
    (ROOT / "outputs" / "audit" / "xg_adjustment_audit.md").write_text(
        f"# xG Adjustment Audit\n\n"
        f"- N={n:,}, seed={seed} (common random numbers → delta is adjustment-only)\n"
        f"- weight={xg_cfg.weight_per_xg_margin}, cap=±{xg_cfg.max_abs_delta} Elo/match\n"
        f"- matches with xG: {audit['n_matches_with_xg']}/{len(log_xg)}\n"
        f"- **max champion move: {max_move:.3f}pp** (guardrail {guardrail}pp) → "
        f"**{'PASS' if passed else 'FAIL'}**\n"
        f"- default mode: **{audit['default_mode_recommendation']}**\n"
        f"- beta_elo: UNCHANGED (xG adjustment never touches it)\n\n"
        f"See xg_probability_delta.md for per-team and per-match detail.\n")

    elapsed = time.monotonic() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"Max champion move: {max_move:.3f}pp (guardrail {guardrail}pp) -> {'PASS' if passed else 'FAIL'}")
    print(f"Default mode recommendation: {audit['default_mode_recommendation']}")
    print("\nTop 8 (xG-adjusted):")
    for _, r in d.head(8).iterrows():
        print(f"  {r['team']:4s} {r['champ_xg']*100:5.2f}%  (score-only {r['champ_score']*100:5.2f}%, "
              f"Δ{r['champ_delta_pp']:+.3f}pp)")
    return 0 if passed else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20260613)
    args = ap.parse_args()
    sys.exit(main(n=args.n, seed=args.seed))
