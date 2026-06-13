#!/usr/bin/env python
"""
P3 tournament simulation runner.

Usage:
  PYTHONPATH=src .venv/bin/python scripts/simulate_models.py --model expert --iterations 100000
  PYTHONPATH=src .venv/bin/python scripts/simulate_models.py --model elo_calibrated --iterations 100000
  PYTHONPATH=src .venv/bin/python scripts/simulate_models.py --model both --iterations 100000

Outputs (--model expert):
  outputs/tournament_run/expert_summary.csv

Outputs (--model elo_calibrated):
  outputs/tournament_run/elo_calibrated_summary.csv

Outputs (--model both / after both run):
  outputs/tournament_run/model_delta_summary.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "tournament_run"
OUT.mkdir(parents=True, exist_ok=True)

from wc2026.data_loader import load_config, load_groups, load_teams
from wc2026.model_factory import make_match_model
from wc2026.tournament import TournamentSimulator
from wc2026.confidence import add_confidence_intervals
from wc2026.utils import ensure_dir, write_json


def run_model_simulation(
    model_name: str,
    iterations: int,
    seed: int,
    verbose: bool = True,
) -> pd.DataFrame:
    """Run tournament simulation for a given model. Returns summary DataFrame."""
    if verbose:
        print(f"\n{'='*50}")
        print(f"Model: {model_name.upper()} — {iterations:,} iterations")
        print(f"{'='*50}")

    teams  = load_teams()
    groups = load_groups()
    config = load_config()

    if model_name == "elo_calibrated":
        # Ensure fitted params exist
        from wc2026.calibrated_elo_model import _PARAMS_FILE, fit_elo_calibrated_params
        if not _PARAMS_FILE.exists():
            print("  Fitting calibrated Elo params...")
            fit_elo_calibrated_params(save=True, verbose=verbose)
        else:
            if verbose:
                print(f"  Using cached params from {_PARAMS_FILE}")

    model = make_match_model(model_name, config)
    if verbose:
        if model_name == "elo_calibrated":
            p = model.params
            print(f"  log_base={p['log_base']:.4f} (xg={p['base_xg']:.3f}), "
                  f"beta_elo={p['beta_elo']:.4f}, rho={p['rho']:.4f}")
        else:
            print(f"  Expert model: analyst priors + StatsBomb features (30/48 real)")

    simulator = TournamentSimulator(teams=teams, groups=groups, config=config, model=model)
    artifacts = simulator.simulate_many(iterations=iterations, seed=seed)

    summary = add_confidence_intervals(artifacts.summary, iterations)
    summary.to_csv(OUT / f"{model_name}_summary.csv", index=False)

    if verbose:
        print(f"\n  Top 10 {model_name}:")
        print(f"  {'Team':<8}  {'P(champion)':<14}  {'P(final)':<12}  {'P(SF)':<10}")
        for _, row in summary.head(10).iterrows():
            print(f"  {row['team']:<8}  {row['champion_prob']:.4f}  {' '*8}"
                  f"  {row['final_prob']:.4f}  {' '*6}  {row['sf_prob']:.4f}")

    # Verify conservation laws
    check_conservation(summary, model_name, verbose)

    return summary


def check_conservation(summary: pd.DataFrame, model_name: str, verbose: bool = True) -> bool:
    """Verify tournament conservation laws. Returns True if all pass."""
    tol = 0.01
    checks = {
        "champion sum = 1":       abs(summary["champion_prob"].sum() - 1.0),
        "final sum = 2":          abs(summary["final_prob"].sum() - 2.0),
        "sf sum = 4":             abs(summary["sf_prob"].sum() - 4.0),
        "qf sum = 8":             abs(summary["qf_prob"].sum() - 8.0),
        "group_survival sum = 32": abs(summary["group_survival_prob"].sum() - 32.0),
    }
    all_ok = True
    for name, error in checks.items():
        ok = error < tol
        if verbose:
            marker = "✓" if ok else "✗"
            print(f"  {marker} {name}: error={error:.6f}")
        if not ok:
            all_ok = False
    return all_ok


def build_delta_summary(
    expert_df: pd.DataFrame,
    elo_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build model comparison table sorted by expert champion rank."""
    ex = expert_df[["team", "champion_prob", "final_prob", "sf_prob"]].copy()
    ex.columns = ["team", "expert_champion_prob", "expert_final_prob", "expert_sf_prob"]
    ex["expert_rank"] = range(1, len(ex) + 1)

    el = elo_df[["team", "champion_prob", "final_prob"]].copy()
    el.columns = ["team", "elo_champion_prob", "elo_final_prob"]
    el = el.sort_values("elo_champion_prob", ascending=False).reset_index(drop=True)
    el["elo_rank"] = range(1, len(el) + 1)

    delta = ex.merge(el, on="team")
    delta["delta_pp"] = (delta["elo_champion_prob"] - delta["expert_champion_prob"]).round(4)
    delta["rank_delta"] = delta["expert_rank"] - delta["elo_rank"]
    delta = delta.sort_values("expert_rank")

    return delta[[
        "team", "expert_champion_prob", "elo_champion_prob", "delta_pp",
        "expert_rank", "elo_rank", "rank_delta",
        "expert_final_prob", "elo_final_prob",
    ]]


def main():
    parser = argparse.ArgumentParser(description="WC2026 model comparison simulation")
    parser.add_argument("--model", default="both",
                        choices=["expert", "elo_calibrated", "both"],
                        help="Which model to simulate (default: both)")
    parser.add_argument("--iterations", type=int, default=100_000,
                        help="Monte Carlo iterations (default: 100000)")
    parser.add_argument("--seed", type=int, default=20260609,
                        help="RNG seed")
    args = parser.parse_args()

    models_to_run = ["expert", "elo_calibrated"] if args.model == "both" else [args.model]

    results: dict[str, pd.DataFrame] = {}

    # Load any already-computed results (skip re-running if both aren't requested)
    for m in ["expert", "elo_calibrated"]:
        cached = OUT / f"{m}_summary.csv"
        if cached.exists() and m not in models_to_run:
            results[m] = pd.read_csv(cached)
            print(f"  Loaded cached {m} results from {cached}")

    # Run requested simulations
    for model_name in models_to_run:
        results[model_name] = run_model_simulation(
            model_name, args.iterations, args.seed, verbose=True
        )

    # Build delta table if both are available
    if "expert" in results and "elo_calibrated" in results:
        delta = build_delta_summary(results["expert"], results["elo_calibrated"])
        delta.to_csv(OUT / "model_delta_summary.csv", index=False)

        print(f"\n{'='*60}")
        print("MODEL COMPARISON: Expert vs Elo-Calibrated")
        print(f"{'='*60}")
        print(f"\n{'Team':<8} {'Expert%':>10} {'Elo%':>10} {'Δpp':>8} {'ExRk':>6} {'EloRk':>6} {'ΔRk':>5}")
        print("-" * 60)
        for _, r in delta.head(20).iterrows():
            arrow = "↑" if r["rank_delta"] > 0 else ("↓" if r["rank_delta"] < 0 else "→")
            print(f"{r['team']:<8} {r['expert_champion_prob']*100:>9.2f}% "
                  f"{r['elo_champion_prob']*100:>9.2f}% "
                  f"{r['delta_pp']*100:>+7.2f}pp "
                  f"{int(r['expert_rank']):>5}  {int(r['elo_rank']):>5}  "
                  f"{arrow}{abs(int(r['rank_delta'])):>2}")

        risers  = delta.nlargest(5, "delta_pp")
        fallers = delta.nsmallest(5, "delta_pp")
        print("\n  Biggest risers (Elo > Expert):")
        for _, r in risers.iterrows():
            print(f"    {r['team']}: {r['delta_pp']*100:+.2f}pp (Elo rank={int(r['elo_rank'])})")
        print("  Biggest fallers (Expert > Elo):")
        for _, r in fallers.iterrows():
            print(f"    {r['team']}: {r['delta_pp']*100:+.2f}pp (Expert rank={int(r['expert_rank'])})")

        print(f"\n  Saved: outputs/tournament_run/model_delta_summary.csv")

    print("\n✓ Done")


if __name__ == "__main__":
    main()
