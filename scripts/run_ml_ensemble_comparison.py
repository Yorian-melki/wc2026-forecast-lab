#!/usr/bin/env python3
"""Before/after tournament simulation: Elo-only vs ML-ensemble.

Identical model, params, Elos, live conditioning, seed, and iterations — the ONLY
difference is use_ml (the DC scoreline PMF reweighting toward the ML/Elo W/D/L
ensemble). This isolates the ML ensemble's effect on tournament probabilities.

Outputs:
  outputs/live/elo_only/stage_probs.csv
  outputs/live/ml_ensemble/stage_probs.csv
  outputs/audit/ml_ensemble_probability_delta.csv
  outputs/audit/ml_ensemble_probability_delta.md
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.data_loader import load_teams, load_config
from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
from wc2026.tournament import TournamentSimulator
from wc2026.group_rules import PlayedMatch
from wc2026.live_state import LiveState, LiveMatchResult

LIVE_FILE = ROOT / "data" / "wc2026_live.json"
GROUPS_FILE = ROOT / "data" / "groups.json"


def build_live_state(completed) -> LiveState:
    state = LiveState(fetched_at=datetime.now())
    for m in completed:
        grp = m.get("group")
        state.completed.append(LiveMatchResult(
            team1=m["home"], team2=m["away"], goals1=m["home_goals"], goals2=m["away_goals"],
            group=grp, round_name="Matchday 1", decided_in="90",
            match_date=date.fromisoformat(m.get("date", "2026-06-11")) if m.get("date") else date(2026, 6, 11)))
        if grp:
            state.group_results.setdefault(grp, []).append(
                PlayedMatch(team_a=m["home"], team_b=m["away"],
                            goals_a=m["home_goals"], goals_b=m["away_goals"],
                            conduct_a=0, conduct_b=0))
    return state


def run(use_ml, teams, groups, cfg, params, live_state, n, seed):
    model = CalibratedEloMatchModel(config=cfg, params=params, use_ml=use_ml)
    sim = TournamentSimulator(teams=teams, groups=groups, model=model)
    return sim.simulate_many_live(iterations=n, seed=seed, live_state=live_state).summary, model.use_ml


def main(n=100_000, seed=20260613):
    t0 = time.monotonic()
    NOW = datetime.now(timezone.utc).isoformat()
    live = json.loads(LIVE_FILE.read_text())
    completed = live.get("completed_matches", [])
    groups = json.loads(GROUPS_FILE.read_text())
    cfg = load_config()
    params = load_calibrated_params()
    teams = load_teams(apply_temporal_form=True)
    live_state = build_live_state(completed)

    print(f"Running {n:,} sims x2 (elo_only, ml_ensemble), seed={seed} ...")
    sum_off, ml_off = run(False, teams, groups, cfg, params, live_state, n, seed)
    sum_on, ml_on = run(True, teams, groups, cfg, params, live_state, n, seed)
    print(f"use_ml: off-run={ml_off}, on-run={ml_on}")
    if not ml_on:
        print("WARNING: ML did not activate (model/config missing) — on-run == off-run.")

    out_off = ROOT / "outputs" / "live" / "elo_only"
    out_on = ROOT / "outputs" / "live" / "ml_ensemble"
    out_off.mkdir(parents=True, exist_ok=True)
    out_on.mkdir(parents=True, exist_ok=True)
    sum_off.to_csv(out_off / "stage_probs.csv", index=False)
    sum_on.to_csv(out_on / "stage_probs.csv", index=False)

    a = sum_off[["team", "champion_prob", "final_prob", "group_survival_prob"]].rename(
        columns={"champion_prob": "champ_elo", "final_prob": "final_elo", "group_survival_prob": "grp_elo"})
    b = sum_on[["team", "champion_prob", "final_prob", "group_survival_prob"]].rename(
        columns={"champion_prob": "champ_ml", "final_prob": "final_ml", "group_survival_prob": "grp_ml"})
    d = a.merge(b, on="team")
    d["champ_delta_pp"] = (d["champ_ml"] - d["champ_elo"]) * 100
    d["final_delta_pp"] = (d["final_ml"] - d["final_elo"]) * 100
    d = d.sort_values("champ_ml", ascending=False).reset_index(drop=True)
    d.to_csv(ROOT / "outputs" / "audit" / "ml_ensemble_probability_delta.csv", index=False)

    max_move = d["champ_delta_pp"].abs().max()
    top = d.head(12)
    lines = ["# ML Ensemble Probability Delta — Elo-only vs ML-ensemble", "",
             f"Generated: {NOW[:19]} · N={n:,} · seed={seed} (same seed both runs)",
             f"Ensemble: 0.5 Elo-Poisson + 0.5 ML logistic, reweighting DC scoreline W/D/L marginals.",
             f"use_ml active: {ml_on}", "",
             f"**Max |champion Δ|: {max_move:.3f} pp**", "",
             "| Team | Champ Elo-only | Champ ML-ens | Δpp | Final Δpp |", "|---|---|---|---|---|"]
    for _, r in top.iterrows():
        lines.append(f"| {r['team']} | {r['champ_elo']*100:.2f}% | {r['champ_ml']*100:.2f}% | "
                     f"{r['champ_delta_pp']:+.3f} | {r['final_delta_pp']:+.3f} |")
    lines += ["", "## Conservation check",
              f"- Σ champion (elo-only) = {sum_off['champion_prob'].sum():.5f}",
              f"- Σ champion (ml-ens)  = {sum_on['champion_prob'].sum():.5f}",
              "", "## Interpretation",
              "ML is more decisive on large Elo gaps, so favorites gain champion share and "
              "longshots lose it. Scoreline structure (goal diff, draws) is preserved — only "
              "W/D/L marginals are reweighted. Rollback: set use_ml_match_model=false in "
              "data/model_stack_config.json (or use_ml=False)."]
    (ROOT / "outputs" / "audit" / "ml_ensemble_probability_delta.md").write_text("\n".join(lines))

    print(f"\nDone in {time.monotonic()-t0:.1f}s · max champion move {max_move:.3f}pp")
    print("\nTop 8 (ML-ensemble):")
    for _, r in d.head(8).iterrows():
        print(f"  {r['team']:4s} {r['champ_ml']*100:5.2f}%  (elo-only {r['champ_elo']*100:5.2f}%, "
              f"Δ{r['champ_delta_pp']:+.3f}pp)")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20260613)
    args = ap.parse_args()
    sys.exit(main(n=args.n, seed=args.seed))
