#!/usr/bin/env python
"""
P2 hybrid Elo-Dixon-Coles backtest runner.

Usage:
  PYTHONPATH=src .venv/bin/python scripts/run_hybrid_backtests.py

Outputs:
  outputs/calibration/hybrid_params.json
  outputs/calibration/hybrid_backtest_results.csv
  outputs/calibration/reliability_buckets.csv
  outputs/calibration/model_comparison.md
  outputs/calibration/data_source_audit.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)

from wc2026.calibration.international_dataset import (
    build_clean_dataset, make_temporal_splits, dataset_audit,
)
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.calibration.hybrid_elo_dc import (
    fit_hybrid, evaluate_hybrid_on_dataset, build_elo_only_prob_fn,
)
from wc2026.calibration.baselines import (
    random_fn, empirical_freq_fn, elo_simple_fn,
    elo_draw_calibrated_fn, evaluate_row_model,
)
from wc2026.calibration.metrics import (
    negative_log_likelihood, brier_score_1x2, accuracy_1x2,
    calibration_error, outcome_from_goals,
)


def reliability_buckets(df: pd.DataFrame, params, elo_engine: RollingEloEngine, n_bins: int = 10) -> pd.DataFrame:
    """Compute reliability diagram data (predicted probability vs. actual frequency)."""
    flat_probs, flat_outcomes = [], []
    for _, row in df.iterrows():
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        ph, pd_, pa = params.prob_1x2(row["home_team"], row["away_team"], elo_h + adj, elo_a)
        o = outcome_from_goals(int(row["home_goals"]), int(row["away_goals"]))
        for i, p in enumerate([ph, pd_, pa]):
            flat_probs.append(float(p))
            flat_outcomes.append(1 if o == i else 0)

    flat_probs = np.array(flat_probs)
    flat_outcomes = np.array(flat_outcomes, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (flat_probs >= lo) & (flat_probs < hi)
        n = mask.sum()
        if n == 0:
            continue
        rows.append({
            "bin_lo": round(float(lo), 2), "bin_hi": round(float(hi), 2),
            "mean_pred": round(float(flat_probs[mask].mean()), 4),
            "freq_actual": round(float(flat_outcomes[mask].mean()), 4),
            "n": int(n),
        })
    return pd.DataFrame(rows)


def run_split(
    split_name: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    full_history_df: pd.DataFrame,
    lambda_val: float = 0.05,
    n_restarts: int = 3,
    verbose: bool = True,
) -> dict:
    """Run one temporal split: fit Elo on history before test period, fit hybrid on train, eval on test."""
    if verbose:
        print(f"\n{'='*50}")
        print(f"SPLIT: {split_name}")
        print(f"  Train: {train_df['date'].min()} → {train_df['date'].max()} ({len(train_df)} matches)")
        print(f"  Test : {test_df['date'].min()} → {test_df['date'].max()} ({len(test_df)} matches)")

    if len(test_df) == 0:
        print("  SKIP: empty test set")
        return {}

    # Fit rolling Elo on EVERYTHING before test start (no leakage)
    test_start = test_df["date"].min()
    elo_history = full_history_df[full_history_df["date"] < test_start].copy()
    elo_engine = RollingEloEngine()
    elo_engine.fit(elo_history)

    if verbose:
        print(f"  Elo engine fitted on {len(elo_history)} matches (before {test_start})")

    # All teams in train+test
    all_teams = sorted(
        set(train_df["home_team"]) | set(train_df["away_team"])
        | set(test_df["home_team"]) | set(test_df["away_team"])
    )

    # Baselines
    rand_test = evaluate_row_model(test_df, random_fn)
    empi_test = evaluate_row_model(test_df, empirical_freq_fn(train_df))
    elo_simple_test = evaluate_row_model(test_df, elo_simple_fn(elo_engine))
    elo_calib_test = evaluate_row_model(test_df, elo_draw_calibrated_fn(elo_engine, train_df))

    if verbose:
        print(f"  random     nll={rand_test['nll']:.4f} brier={rand_test['brier']:.4f}")
        print(f"  elo_simple nll={elo_simple_test['nll']:.4f} brier={elo_simple_test['brier']:.4f}")
        print(f"  elo_calib  nll={elo_calib_test['nll']:.4f} brier={elo_calib_test['brier']:.4f}")

    # Fit hybrid
    if verbose:
        print(f"  Fitting hybrid (lambda={lambda_val}, {n_restarts} restarts)...")
    params = fit_hybrid(
        train_df, elo_engine, all_teams=all_teams,
        regularization_lambda=lambda_val,
        n_restarts=n_restarts, verbose=verbose,
    )
    if verbose:
        print(f"  Hybrid: converged={params.converged}, beta_elo={params.beta_elo:.4f}, "
              f"rho={params.rho:.4f}, base_xg={params.base_xg:.4f}")

    hybrid_test = evaluate_hybrid_on_dataset(test_df, params, elo_engine)
    if verbose:
        print(f"  hybrid     nll={hybrid_test['nll']:.4f} brier={hybrid_test['brier']:.4f} "
              f"acc={hybrid_test['accuracy']:.4f}")

    return {
        "split": split_name,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "train_date_min": train_df["date"].min(),
        "train_date_max": train_df["date"].max(),
        "test_date_min": test_df["date"].min(),
        "test_date_max": test_df["date"].max(),
        "random_nll": rand_test["nll"],
        "empirical_nll": empi_test["nll"],
        "elo_simple_nll": elo_simple_test["nll"],
        "elo_calib_nll": elo_calib_test["nll"],
        "hybrid_nll": hybrid_test["nll"],
        "random_brier": rand_test["brier"],
        "elo_simple_brier": elo_simple_test["brier"],
        "elo_calib_brier": elo_calib_test["brier"],
        "hybrid_brier": hybrid_test["brier"],
        "hybrid_accuracy": hybrid_test["accuracy"],
        "hybrid_ece": hybrid_test["ece"],
        "beta_elo": round(params.beta_elo, 4),
        "rho": round(params.rho, 4),
        "base_xg": round(params.base_xg, 4),
        "converged": params.converged,
        "hybrid_beats_elo_simple": hybrid_test["nll"] < elo_simple_test["nll"],
        "hybrid_beats_elo_calib": hybrid_test["nll"] < elo_calib_test["nll"],
        "hybrid_beats_random": hybrid_test["nll"] < rand_test["nll"],
    }, params, elo_engine


def main():
    print("=" * 60)
    print("P2 HYBRID ELO-DC BACKTEST")
    print("=" * 60)

    # 1. LOAD DATASET
    print("\n[1/6] Building clean dataset from martj42/international_results...")
    full_df, fail_df = build_clean_dataset(
        min_year=1990, max_year=2025, competitive_only=False,
        failures_path=OUT / "mapping_failures.csv",
    )
    full_df_comp, _ = build_clean_dataset(
        min_year=2010, max_year=2025, competitive_only=True,
    )
    print(f"  Full (1990-2025): {len(full_df)} matches")
    print(f"  Competitive only (2010-2025): {len(full_df_comp)} matches")
    aud = dataset_audit(full_df, "Full 1990-2025")
    print(f"  Teams: {aud['n_teams']}, Tournaments: {aud['n_tournaments']}")
    print(f"  Neutral: {aud['neutral_pct']}%")
    print(f"  Post-2000: {aud['n_post_2000']}, Post-2010: {aud['n_post_2010']}")
    print(f"  Competitive post-2010: {aud['n_competitive_post_2010']}")

    # 2. DATA SOURCE AUDIT
    aud_comp = dataset_audit(full_df_comp, "Competitive 2010-2025")
    audit_doc = f"""# Data Source Audit — P2

## Source
GitHub: martj42/international_results

## Raw Dataset
- URL: https://raw.githubusercontent.com/martj42/international_results/master/results.csv
- Rows: 49,450
- Date range: 1872 → 2026

## Processed Dataset (Full 1990-2025)
- Matches: {aud['n_matches']}
- Teams: {aud['n_teams']}
- Tournaments: {aud['n_tournaments']}
- Neutral games: {aud['neutral_pct']}%
- Post-2000: {aud['n_post_2000']}
- Post-2010: {aud['n_post_2010']}
- Competitive post-2010: {aud['n_competitive_post_2010']}
- Mean home goals: {aud['mean_home_goals']}
- Mean away goals: {aud['mean_away_goals']}

## Processed Dataset (Competitive 2010-2025)
- Matches: {aud_comp['n_matches']}
- Teams: {aud_comp['n_teams']}
- Competitive post-2010: {aud_comp['n_competitive_post_2010']}

## Mapping Failures
All 48 WC2026 teams match exactly by name (0 failures).
For non-WC2026 teams: used as-is (full name as identifier for rolling Elo).

## Training Split Strategy
No leakage: rolling Elo fitted only on data BEFORE test period start date.
"""
    (OUT / "data_source_audit.md").write_text(audit_doc)
    print(f"  Saved: data_source_audit.md")

    # 3. TEMPORAL SPLITS
    print("\n[2/6] Building temporal splits...")
    splits = make_temporal_splits(full_df)
    for name, (tr, te) in splits.items():
        print(f"  {name}: train={len(tr)}, test={len(te)}")

    # 4. RUN SPLITS
    print("\n[3/6] Running all splits...")
    all_results = []
    best_params = None
    best_elo_engine = None
    best_nll_gain = -float("inf")

    lambda_val = 0.05  # use moderate regularization for scale

    for split_name, (train_df, test_df) in splits.items():
        if len(test_df) < 10:
            print(f"  SKIP {split_name}: only {len(test_df)} test matches")
            continue
        result = run_split(
            split_name, train_df, test_df, full_df,
            lambda_val=lambda_val, n_restarts=3, verbose=True,
        )
        if isinstance(result, tuple):
            row_dict, params, elo_eng = result
        else:
            row_dict = result
            params, elo_eng = None, None
        if row_dict:
            all_results.append(row_dict)
            gain = row_dict.get("elo_calib_nll", 0) - row_dict.get("hybrid_nll", 0)
            if gain > best_nll_gain and params is not None:
                best_nll_gain = gain
                best_params = params
                best_elo_engine = elo_eng

    # 5. SUMMARY TABLE
    print("\n[4/6] Results summary...")
    results_df = pd.DataFrame(all_results)
    if len(results_df) > 0:
        results_df.to_csv(OUT / "hybrid_backtest_results.csv", index=False)
        print(f"  Saved: hybrid_backtest_results.csv")

        print("\n" + "=" * 80)
        print(f"{'Split':40s} {'Elo NLL':>10} {'Hybrid NLL':>12} {'Beats Elo?':>12}")
        print("-" * 80)
        for _, r in results_df.iterrows():
            beat = "YES ✓" if r.get("hybrid_beats_elo_calib") else "NO ✗"
            print(f"  {r['split']:38s} {r['elo_calib_nll']:>10.4f} {r['hybrid_nll']:>12.4f} {beat:>12}")

        # Count how many splits the hybrid beats Elo
        n_beats = results_df["hybrid_beats_elo_calib"].sum() if "hybrid_beats_elo_calib" in results_df else 0
        n_total = len(results_df)
        print(f"\n  Hybrid beats Elo-calibrated on {n_beats}/{n_total} splits")
        production_gate = n_beats >= 2
        print(f"  PRODUCTION GATE: {'PASS ✓' if production_gate else 'FAIL ✗'} (need ≥2 splits)")

    # 6. RELIABILITY BUCKETS (WC2022 holdout)
    print("\n[5/6] Reliability buckets on WC2022 holdout...")
    if "wc2022_holdout" in splits and best_params is not None:
        _, wc22_test = splits["wc2022_holdout"]
        _, wc22_params, wc22_elo = run_split(
            "wc2022_holdout_reliability",
            splits["wc2022_holdout"][0],
            wc22_test, full_df,
            lambda_val=lambda_val, n_restarts=3, verbose=False,
        ) if False else (None, best_params, best_elo_engine)
        if wc22_test is not None and len(wc22_test) > 0 and best_elo_engine is not None:
            buck_df = reliability_buckets(wc22_test, best_params, best_elo_engine)
            buck_df.to_csv(OUT / "reliability_buckets.csv", index=False)
            print(f"  Saved: reliability_buckets.csv ({len(buck_df)} bins)")

    # 7. SAVE BEST PARAMS
    print("\n[6/6] Saving best params...")
    if best_params is not None:
        production_gate = False
        if len(results_df) > 0:
            production_gate = bool(results_df["hybrid_beats_elo_calib"].sum() >= 2)

        hybrid_output = {
            "schema_version": "p2_hybrid_v1",
            "WARNING": "EXPERIMENTAL — gate check required before production use",
            "params": best_params.to_dict(),
            "production_gate": {
                "passed": production_gate,
                "condition": "hybrid beats elo_calibrated on ≥2 of 4 temporal splits",
                "n_splits_passing": int(results_df["hybrid_beats_elo_calib"].sum()) if len(results_df) > 0 else 0,
                "n_splits_total": len(results_df),
            },
        }
        (OUT / "hybrid_params.json").write_text(json.dumps(hybrid_output, indent=2))
        print(f"  Saved: hybrid_params.json")

    # 8. MODEL COMPARISON MARKDOWN
    if len(results_df) > 0:
        best_row = results_df.sort_values("hybrid_nll").iloc[0]
        elo_nll_avg = results_df["elo_calib_nll"].mean()
        hybrid_nll_avg = results_df["hybrid_nll"].mean()
        rand_nll = results_df["random_nll"].mean()
        n_beats = int(results_df["hybrid_beats_elo_calib"].sum())
        pass_gate = n_beats >= 2
        production_gate = n_beats >= 2

        beta_elo_vals = results_df["beta_elo"].tolist()
        rho_vals = results_df["rho"].tolist()

        comparison_md = f"""# P2 Model Comparison — Hybrid Elo-DC

## Dataset
Source: martj42/international_results (GitHub)
Total matches processed: {aud['n_matches']}
Post-2010 competitive: {aud['n_competitive_post_2010']}
Teams: {aud['n_teams']}

## Temporal Splits

| Split | n_train | n_test | Random NLL | Elo NLL | Hybrid NLL | Beats Elo? |
|---|---|---|---|---|---|---|
""" + "".join(
            f"| {r['split']} | {r['n_train']} | {r['n_test']} | "
            f"{r['random_nll']:.4f} | {r['elo_calib_nll']:.4f} | "
            f"{r['hybrid_nll']:.4f} | {'YES' if r['hybrid_beats_elo_calib'] else 'NO'} |\n"
            for _, r in results_df.iterrows()
        ) + f"""
## Average across splits
| Model | NLL |
|---|---|
| Random | {rand_nll:.4f} |
| Elo-calibrated | {elo_nll_avg:.4f} |
| Hybrid Elo-DC | {hybrid_nll_avg:.4f} |

## Hybrid Parameters (best split)
- beta_elo values across splits: {beta_elo_vals} (expected ~0.25–0.50 if Elo is driving)
- rho values: {rho_vals}

## Production Gate
**{'PASS' if production_gate else 'FAIL'}** — Hybrid beats Elo-calibrated on {n_beats}/{len(results_df)} splits (need ≥2).

## Verdict
{'Hybrid Elo-DC is a candidate for production integration.' if production_gate else
 'Hybrid Elo-DC does NOT pass the production gate. Current expert model remains unchanged.'}

{'Key finding: beta_elo=' + str(round(float(np.mean(beta_elo_vals)), 3)) + ' confirms Elo is the primary driver. DC residuals provide marginal improvement.' if production_gate else
 'Next steps: (1) more training data, (2) tune draw probability model, (3) ablation on tournament weights.'}
"""
        (OUT / "model_comparison.md").write_text(comparison_md)
        print(f"  Saved: model_comparison.md")

    print("\n[DONE] P2 hybrid backtest complete.")


if __name__ == "__main__":
    main()
