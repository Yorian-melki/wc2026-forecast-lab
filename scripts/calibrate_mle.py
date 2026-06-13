#!/usr/bin/env python
"""
P1 MLE calibration runner.

Usage:
  PYTHONPATH=src .venv/bin/python scripts/calibrate_mle.py

Outputs:
  outputs/calibration/mle_params.json
  outputs/calibration/comparison_table.csv
  outputs/calibration/mapping_failures.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)

from wc2026.calibration.datasets import load_calibration_dataset
from wc2026.calibration.dixon_coles_mle import fit_dixon_coles, grid_search_lambda, DCParams
from wc2026.calibration.metrics import (
    evaluate_model_on_dataset,
    random_baseline_probs,
    elo_baseline_probs,
    indep_poisson_probs,
)


def build_elo_map() -> dict[str, float]:
    elo_path = ROOT / "data" / "elo_snapshot.csv"
    if not elo_path.exists():
        print("  [WARN] elo_snapshot.csv not found — using 1500 for all teams")
        return {}
    df = pd.read_csv(elo_path)
    col_code = "code" if "code" in df.columns else df.columns[0]
    col_elo = "elo_current" if "elo_current" in df.columns else df.columns[1]
    return dict(zip(df[col_code], df[col_elo]))


def build_indep_poisson_prob_fn(train_df: pd.DataFrame, all_teams: list[str]):
    """
    Fit team strengths as simple attack/defense from goal averages.
    log_mu_h = log_base + atk_h - def_a  (independent Poisson, no DC).
    """
    import math, numpy as np
    from scipy.optimize import minimize

    team_idx = {t: i for i, t in enumerate(all_teams)}
    n = len(all_teams)
    h_idx = [team_idx[r["home_code"]] for _, r in train_df.iterrows()]
    a_idx = [team_idx[r["away_code"]] for _, r in train_df.iterrows()]
    h_goals = [int(r["home_goals"]) for _, r in train_df.iterrows()]
    a_goals = [int(r["away_goals"]) for _, r in train_df.iterrows()]

    def obj(x):
        log_base = x[0]; atk = x[1:n+1]; dfs = x[n+1:]
        nll = 0.0
        for k in range(len(h_goals)):
            mu_h = math.exp(log_base + atk[h_idx[k]] - dfs[a_idx[k]])
            mu_a = math.exp(log_base + atk[a_idx[k]] - dfs[h_idx[k]])
            mu_h = min(max(mu_h, 0.05), 8.0); mu_a = min(max(mu_a, 0.05), 8.0)
            nll -= (-mu_h + h_goals[k]*math.log(mu_h) - math.lgamma(h_goals[k]+1))
            nll -= (-mu_a + a_goals[k]*math.log(mu_a) - math.lgamma(a_goals[k]+1))
        reg = 0.05 * (np.sum(atk**2) + np.sum(dfs**2))
        ident = 100.0 * np.sum(atk)**2
        return nll + reg + ident

    mean_g = (train_df["home_goals"].mean() + train_df["away_goals"].mean()) / 2
    x0 = np.zeros(1 + 2*n)
    x0[0] = math.log(max(mean_g, 0.5))
    bounds = [(-2.0, 1.0)] + [(-3, 3)] * (2*n)
    res = minimize(obj, x0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 1000})
    log_base = res.x[0]; atk = res.x[1:n+1]; dfs = res.x[n+1:]
    mean_atk = float(np.mean(atk)); atk -= mean_atk; log_base += mean_atk

    def prob_fn(home_code, away_code):
        hi = team_idx.get(home_code, -1); ai = team_idx.get(away_code, -1)
        a_h = atk[hi] if hi >= 0 else 0.0
        d_h = dfs[hi] if hi >= 0 else 0.0
        a_a = atk[ai] if ai >= 0 else 0.0
        d_a = dfs[ai] if ai >= 0 else 0.0
        mu_h = math.exp(log_base + a_h - d_a)
        mu_a = math.exp(log_base + a_a - d_h)
        return indep_poisson_probs(min(max(mu_h, 0.05), 6.0), min(max(mu_a, 0.05), 6.0))

    return prob_fn


def main():
    print("=" * 60)
    print("P1 MLE CALIBRATION — Dixon-Coles")
    print("=" * 60)

    # 1. LOAD DATASET
    print("\n[1/5] Loading StatsBomb WC2018+WC2022...")
    ds = load_calibration_dataset(
        time_decay=False,
        failures_path=OUT / "mapping_failures.csv",
    )
    print(f"  TRAIN  (WC2018): {ds.train_summary['n_matches']} matches, "
          f"{ds.train_summary['n_teams']} teams, "
          f"map success {ds.train_summary['mapping_success_pct']}%")
    print(f"  HOLDOUT(WC2022): {ds.holdout_summary['n_matches']} matches, "
          f"{ds.holdout_summary['n_teams']} teams, "
          f"map success {ds.holdout_summary['mapping_success_pct']}%")
    print(f"  Unique teams: {len(ds.all_teams)}")
    print(f"  WARN: ~{len(ds.train) / max(len(ds.all_teams), 1):.1f} matches/team — SPARSE, L2 required")

    if len(ds.train) < 30:
        print("FATAL: fewer than 30 training matches — abort MLE")
        sys.exit(1)

    # 2. BASELINES
    print("\n[2/5] Building baselines...")
    elo_map = build_elo_map()
    print(f"  Elo map: {len(elo_map)} teams loaded")
    elo_prob_fn = lambda h, a: elo_baseline_probs(h, a, elo_map)
    indep_prob_fn = build_indep_poisson_prob_fn(ds.train, ds.all_teams)

    baselines = {
        "random": lambda h, a: random_baseline_probs(h, a),
        "elo_only": elo_prob_fn,
        "indep_poisson": indep_prob_fn,
    }
    baseline_results = {}
    for name, fn in baselines.items():
        tr = evaluate_model_on_dataset(ds.train, fn)
        ho = evaluate_model_on_dataset(ds.holdout, fn)
        baseline_results[name] = {"train": tr, "holdout": ho}
        print(f"  {name:20s} train_nll={tr['nll']:.4f} holdout_nll={ho['nll']:.4f} "
              f"holdout_brier={ho['brier']:.4f}")

    # 3. GRID SEARCH lambda
    print("\n[3/5] Grid search on regularization lambda (by holdout NLL)...")
    best_lambda, grid_results = grid_search_lambda(
        ds.train, ds.holdout, ds.all_teams,
        lambdas=[0.01, 0.05, 0.10, 0.20],
        n_restarts=3,
        verbose=True,
    )
    print(f"\n  Best lambda by holdout NLL: {best_lambda}")

    # 4. FIT FINAL MODEL
    print(f"\n[4/5] Fitting final DC model (lambda={best_lambda}, 5 restarts)...")
    params = fit_dixon_coles(
        ds.train, ds.all_teams,
        regularization_lambda=best_lambda,
        n_restarts=5,
        verbose=True,
    )
    print(f"  converged: {params.converged}")
    print(f"  rho: {params.rho:.4f}")
    print(f"  base_xg: {params.base_xg:.4f}  (log_base={params.log_base_xg:.4f})")
    print(f"  NLL on train (no regularization): {params.final_nll:.4f}")
    for w in params.warnings:
        print(f"  [WARN] {w}")

    # 5. EVALUATE + COMPARISON
    print("\n[5/5] Evaluating all models on train + holdout...")
    dc_prob_fn = lambda h, a: params.prob_1x2(h, a)
    dc_train = evaluate_model_on_dataset(ds.train, dc_prob_fn)
    dc_holdout = evaluate_model_on_dataset(ds.holdout, dc_prob_fn)

    print("\n" + "=" * 60)
    print("COMPARISON TABLE")
    print("=" * 60)
    header = f"{'Model':25s} {'Train NLL':>10} {'Hold NLL':>10} {'Hold Brier':>12} {'Hold Acc':>10} {'Hold ECE':>10}"
    print(header)
    print("-" * len(header))

    rows = []
    for name, res in baseline_results.items():
        tr, ho = res["train"], res["holdout"]
        print(f"  {name:23s} {tr['nll']:>10.4f} {ho['nll']:>10.4f} {ho['brier']:>12.4f} {ho['accuracy']:>10.4f} {ho['ece']:>10.4f}")
        rows.append({
            "model": name, "train_nll": tr["nll"], "holdout_nll": ho["nll"],
            "holdout_brier": ho["brier"], "holdout_acc": ho["accuracy"], "holdout_ece": ho["ece"],
        })

    print(f"  {'dc_mle_experimental':23s} {dc_train['nll']:>10.4f} {dc_holdout['nll']:>10.4f} {dc_holdout['brier']:>12.4f} {dc_holdout['accuracy']:>10.4f} {dc_holdout['ece']:>10.4f}")
    rows.append({
        "model": "dc_mle_experimental", "train_nll": dc_train["nll"],
        "holdout_nll": dc_holdout["nll"], "holdout_brier": dc_holdout["brier"],
        "holdout_acc": dc_holdout["accuracy"], "holdout_ece": dc_holdout["ece"],
    })

    print("-" * len(header))
    random_hold_nll = baseline_results["random"]["holdout"]["nll"]
    elo_hold_nll = baseline_results["elo_only"]["holdout"]["nll"]
    print(f"  Random baseline NLL: {random_hold_nll:.4f}")
    print(f"  Elo-only baseline NLL: {elo_hold_nll:.4f}")
    dc_beats_random = dc_holdout["nll"] < random_hold_nll
    dc_beats_elo = dc_holdout["nll"] < elo_hold_nll
    print(f"\n  DC MLE beats random:   {'YES ✓' if dc_beats_random else 'NO ✗'}")
    print(f"  DC MLE beats Elo-only: {'YES ✓' if dc_beats_elo else 'NO ✗'}")

    verdict_prod_ready = dc_beats_elo and params.converged
    print(f"\n  PRODUCTION CANDIDATE: {'YES' if verdict_prod_ready else 'NO — holdout improvement insufficient'}")

    # Attack/defense top lists
    atk_sorted = sorted(params.attack.items(), key=lambda x: -x[1])
    def_sorted = sorted(params.defense.items(), key=lambda x: x[1])  # lower defense = easier to score against
    print(f"\n  Top 10 attack (offense strength): {[f'{t}={v:.3f}' for t,v in atk_sorted[:10]]}")
    print(f"  Worst 10 defense (concede most): {[f'{t}={v:.3f}' for t,v in def_sorted[:10]]}")

    # Save outputs
    comp_df = pd.DataFrame(rows)
    comp_df.to_csv(OUT / "comparison_table.csv", index=False)
    print(f"\n  Saved: {OUT / 'comparison_table.csv'}")

    # Build mle_params.json
    mle_output = {
        "schema_version": "p1_mle_v1",
        "WARNING": "EXPERIMENTAL — do not overwrite production model without holdout proof",
        "params": {
            "log_base_xg": round(params.log_base_xg, 6),
            "base_xg": round(params.base_xg, 5),
            "rho": round(params.rho, 6),
            "team_attack": {t: round(v, 6) for t, v in sorted(params.attack.items())},
            "team_defense": {t: round(v, 6) for t, v in sorted(params.defense.items())},
        },
        "training": {
            "dataset": "WC2018 (StatsBomb competition_id=43 season_id=3)",
            "n_matches": ds.train_summary["n_matches"],
            "n_teams": ds.train_summary["n_teams"],
            "regularization_lambda": best_lambda,
        },
        "holdout": {
            "dataset": "WC2022 (StatsBomb competition_id=43 season_id=106)",
            "n_matches": ds.holdout_summary["n_matches"],
        },
        "train_metrics": dc_train,
        "holdout_metrics": dc_holdout,
        "baselines": {k: v["holdout"] for k, v in baseline_results.items()},
        "grid_search": {str(k): v for k, v in grid_results.items()},
        "convergence_status": "converged" if params.converged else "not_converged",
        "n_iterations": params.n_iterations,
        "optimizer_message": params.message,
        "warnings": params.warnings + (
            ["DC MLE does NOT beat Elo-only baseline — DO NOT deploy"] if not dc_beats_elo else []
        ),
        "verdict": {
            "beats_random": dc_beats_random,
            "beats_elo_only": dc_beats_elo,
            "converged": params.converged,
            "production_candidate": verdict_prod_ready,
        },
    }
    params_path = OUT / "mle_params.json"
    params_path.write_text(json.dumps(mle_output, indent=2))
    print(f"  Saved: {params_path}")
    print("\n[DONE] P1 MLE calibration complete.")
    return mle_output


if __name__ == "__main__":
    main()
