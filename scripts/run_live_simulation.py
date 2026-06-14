#!/usr/bin/env python3
"""Regenerate the WC2026 forecast shown on the dashboard (live-conditioned, calibrated).

ONE command — fully offline, no API keys needed:

    PYTHONPATH=src python scripts/run_live_simulation.py            # 100k Monte Carlo
    PYTHONPATH=src python scripts/run_live_simulation.py --n 20000  # faster

What it does:
  * Reads data/wc2026_live.json — the SAME completed matches the dashboard displays.
  * Builds the calibrated Elo -> Dixon-Coles Poisson model with the ML 1X2 ensemble at the
    weight in data/model_stack_config.json (0.20). This is the model the dashboard claims.
  * Conditions the group stage on the real results (locks played matches) and runs the
    tournament Monte Carlo via the supported TournamentSimulator.simulate_many_live API.
  * Writes the three artifacts the dashboard reads (Champion Tracker / Bracket Paths):
        outputs/tournament_run/live_summary.csv
        outputs/tournament_run/live_stage_probs.csv
        outputs/tournament_run/live_group_position_probs.csv

This replaces the previous broken script (it referenced a non-existent CalibratedEloModel
class and a TournamentSimulator.run() method). The forecast is now reproducible from a single
command using only committed data.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.calibrated_elo_model import CalibratedEloMatchModel
from wc2026.confidence import add_confidence_intervals
from wc2026.data_loader import load_groups, load_teams
from wc2026.group_rules import PlayedMatch
from wc2026.live_state import LiveMatchResult, LiveState
from wc2026.tournament import TournamentSimulator

LIVE_FILE = ROOT / "data" / "wc2026_live.json"
OUT_DIR = ROOT / "outputs" / "tournament_run"
N_DEFAULT = 100_000
SEED = 20260613


def build_live_state(live: dict) -> LiveState:
    """Build a LiveState (group-stage conditioning) from data/wc2026_live.json."""
    state = LiveState(fetched_at=datetime.now())
    for m in live.get("completed_matches", []):
        if m.get("home_goals") is None or m.get("away_goals") is None:
            continue
        grp = m.get("group") or None
        try:
            d = date.fromisoformat(str(m.get("date", "")))
        except ValueError:
            d = date.today()
        state.completed.append(LiveMatchResult(
            team1=m["home"], team2=m["away"],
            goals1=int(m["home_goals"]), goals2=int(m["away_goals"]),
            group=grp, round_name="Matchday 1",
            decided_in=str(m.get("decided_in", "90")), match_date=d,
        ))
        if grp:
            state.group_results.setdefault(grp, []).append(PlayedMatch(
                team_a=m["home"], team_b=m["away"],
                goals_a=int(m["home_goals"]), goals_b=int(m["away_goals"]),
                conduct_a=0, conduct_b=0,
            ))
    return state


def main() -> int:
    n = N_DEFAULT
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])

    t0 = time.monotonic()
    live = json.loads(LIVE_FILE.read_text()) if LIVE_FILE.exists() else {}
    state = build_live_state(live)
    print(f"Conditioning on {state.n_completed} completed match(es) "
          f"across {len(state.group_results)} group(s).")

    # use_ml=None -> read use_ml_match_model + ensemble weight from model_stack_config.json
    model = CalibratedEloMatchModel(use_ml=None)
    print(f"Model: CalibratedEloMatchModel (Elo->Dixon-Coles) · "
          f"ML ensemble active={model.use_ml} (weight {model._ml_weight:.2f})")

    sim = TournamentSimulator(
        teams=load_teams(apply_temporal_form=True),
        groups=load_groups(),
        model=model,
    )
    art = sim.simulate_many_live(iterations=n, seed=SEED, live_state=state)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = add_confidence_intervals(art.summary, n)
    summary.to_csv(OUT_DIR / "live_summary.csv", index=False)
    art.stage_probs.to_csv(OUT_DIR / "live_stage_probs.csv", index=False)
    art.group_positions.to_csv(OUT_DIR / "live_group_position_probs.csv", index=False)

    csum = float(summary["champion_prob"].sum())
    assert abs(csum - 1.0) < 1e-6, f"champion probabilities must sum to 1 (got {csum})"
    print(f"Done in {time.monotonic() - t0:.0f}s · Sum champion = {csum:.6f} (conservation OK)")
    print("Top 6 champion probabilities:")
    for _, r in summary.nlargest(6, "champion_prob").iterrows():
        print(f"  {r['team']:4s} {r['champion_prob'] * 100:5.2f}%")
    print(f"Wrote live_summary.csv · live_stage_probs.csv · live_group_position_probs.csv -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
