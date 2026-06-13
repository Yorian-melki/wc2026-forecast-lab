#!/usr/bin/env python3
"""
Live-conditioned WC2026 simulation.
Reads wc2026_live.json, updates Elo from played matches, locks in group results,
and re-runs 100K Monte Carlo simulations.

Output: outputs/tournament_run/live_summary.csv
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from copy import deepcopy

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from wc2026.data_loader import load_teams
from wc2026.calibrated_elo_model import CalibratedEloModel
from wc2026.tournament import TournamentSimulator
from wc2026.group_rules import PlayedMatch

PARAMS_FILE = ROOT / 'data' / 'elo_calibrated_params.json'
LIVE_FILE   = ROOT / 'data' / 'wc2026_live.json'
GROUPS_FILE = ROOT / 'data' / 'groups.json'
OUT_DIR     = ROOT / 'outputs' / 'tournament_run'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Elo update k-factor for WC matches (higher stakes = larger k)
K_FACTOR = 40  # Standard FIFA-equivalent for WC


def elo_update(elo_a: float, elo_b: float, goals_a: int, goals_b: int, k: float = K_FACTOR):
    """
    Update Elo ratings after a match result.
    Uses margin-of-victory multiplier (FIFA/ClubElo style).
    """
    expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
    if goals_a > goals_b:
        score_a = 1.0
        margin = goals_a - goals_b
    elif goals_a < goals_b:
        score_a = 0.0
        margin = goals_b - goals_a
    else:
        score_a = 0.5
        margin = 0

    # Margin-of-victory multiplier (logarithmic, as used by FiveThirtyEight)
    if margin == 0:
        mov_mul = 1.0
    else:
        # MOV multiplier: log(margin+1) * (2.2 / (elo_diff*0.001 + 2.2))
        elo_diff = elo_a - elo_b if goals_a > goals_b else elo_b - elo_a
        mov_mul = np.log(margin + 1) * (2.2 / (elo_diff * 0.001 + 2.2))
        mov_mul = max(1.0, mov_mul)  # floor at 1.0

    delta_a = k * mov_mul * (score_a - expected_a)
    return elo_a + delta_a, elo_b - delta_a


def build_played_matches_from_live(live_data: dict) -> dict[str, list[PlayedMatch]]:
    """Convert completed matches in live_data to PlayedMatch objects per group."""
    group_results: dict[str, list[PlayedMatch]] = {}
    for m in live_data.get('completed_matches', []):
        grp = m['group']
        if grp not in group_results:
            group_results[grp] = []
        # Conduct (red cards etc.) set to 0 for now — WC2026 doesn't track per-team granularity
        pm = PlayedMatch(
            team_a=m['home'],
            team_b=m['away'],
            goals_a=m['home_goals'],
            goals_b=m['away_goals'],
            conduct_a=0,
            conduct_b=0,
        )
        group_results[grp].append(pm)
    return group_results


def main():
    t0 = time.monotonic()
    print("=== WC2026 Live-Conditioned Simulation ===")

    # Load frozen params
    params = json.loads(PARAMS_FILE.read_text())
    print(f"beta_elo: {params['beta_elo']} (frozen)")

    # Load live state
    live = json.loads(LIVE_FILE.read_text())
    completed = live.get('completed_matches', [])
    print(f"Completed matches: {len(completed)}")

    # Load teams with current Elo
    teams = load_teams(apply_temporal_form=True)

    # Apply Elo updates from completed WC2026 matches
    updated_elos: dict[str, float] = {code: t.elo_current for code, t in teams.items()}
    for m in completed:
        ha, hb = m['home'], m['away']
        ga, gb = m['home_goals'], m['away_goals']
        ea, eb = updated_elos.get(ha, 1500), updated_elos.get(hb, 1500)
        new_ea, new_eb = elo_update(ea, eb, ga, gb)
        print(f"  Elo update: {ha} {ea:.0f}→{new_ea:.0f} | {hb} {eb:.0f}→{new_eb:.0f}  ({ga}–{gb})")
        updated_elos[ha] = new_ea
        updated_elos[hb] = new_eb

    # Rebuild teams dict with updated Elos
    from dataclasses import replace
    teams_updated = {}
    for code, team in teams.items():
        new_elo = updated_elos.get(code, team.elo_current)
        teams_updated[code] = replace(team, elo_current=new_elo)

    # Build played matches for conditioning
    played_per_group = build_played_matches_from_live(live)

    # Load groups
    with GROUPS_FILE.open() as f:
        groups = json.load(f)

    # Build model with updated Elos
    model = CalibratedEloModel(
        beta_elo=params['beta_elo'],
        log_base=params['log_base'],
        rho=params['rho'],
    )

    # Run conditioned simulation
    print(f"\nRunning 100,000 conditioned Monte Carlo simulations...")
    sim = TournamentSimulator(
        model=model,
        teams=teams_updated,
        groups=groups,
    )

    N = 100_000
    SEED = 20260613  # Updated seed for live run

    # Pass pre-played group matches as conditioning
    results = sim.run(
        n=N,
        seed=SEED,
        played_matches=played_per_group,
    )

    # Save results
    out_path = OUT_DIR / 'live_summary.csv'
    results.to_csv(out_path, index=False)
    elapsed = time.monotonic() - t0
    print(f"\nDone in {elapsed:.1f}s → {out_path}")

    # Verify conservation
    print(f"\nConservation check:")
    print(f"  Σ P(champion) = {results['champion_prob'].sum():.6f}")
    print(f"  Σ P(finalist) = {results['final_prob'].sum():.6f}")

    # Top 10
    print(f"\nTop 10 champion probabilities (post-{len(completed)} WC2026 matches):")
    top10 = results.nlargest(10, 'champion_prob')
    for _, r in top10.iterrows():
        old = params['team_elos'].get(r['team'], updated_elos.get(r['team'], 1500))
        new = updated_elos.get(r['team'], old)
        delta = new - old
        flag = f" (Elo {new:.0f}, Δ{delta:+.0f})" if abs(delta) > 0.01 else f" (Elo {new:.0f})"
        print(f"  {r['team']:4s} {r['champion_prob']*100:5.2f}%{flag}")

    # Also write updated Elo snapshot
    elo_snap_rows = [{'team': code, 'elo_pre': params['team_elos'].get(code, updated_elos.get(code, 1500)),
                      'elo_post': updated_elos.get(code, 1500),
                      'matches_played': sum(1 for m in completed if code in (m['home'], m['away']))}
                     for code in teams.keys()]
    elo_snap = pd.DataFrame(elo_snap_rows)
    elo_snap.to_csv(OUT_DIR / 'live_elo_snapshot.csv', index=False)
    print(f"\nElo snapshot → {OUT_DIR / 'live_elo_snapshot.csv'}")


if __name__ == '__main__':
    main()
