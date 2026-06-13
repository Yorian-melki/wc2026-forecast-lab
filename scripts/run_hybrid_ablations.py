#!/usr/bin/env python
"""
P2.5 ablation study — Hybrid Elo-DC model decomposition.

Usage:
  PYTHONPATH=src .venv/bin/python scripts/run_hybrid_ablations.py

Ablation variants (A–I):
  A  Random (1/3, 1/3, 1/3)
  B  Empirical home/draw/away frequency
  C  Elo-only, no home advantage, fixed draw=22%
  D  Elo + home advantage, fixed draw=22%
  E  Elo + calibrated draw (draw prob fitted from train)
  F  Independent Poisson, no per-team, no DC [2 params]
  G  Elo + DC rho only, no per-team residuals [3 params]
  H  Hybrid: Elo + per-team residuals, rho=0 forced
  I  Full Hybrid: Elo + per-team residuals + DC rho [current model]

Rule: if a layer degrades Elo-only on holdout → REJECTED or EXPERIMENTAL.
      Δ < 0.01 NLL on large splits treated as noise, not victory.

Outputs:
  outputs/calibration/ablation_results.csv
  outputs/calibration/ablation_summary.md
  outputs/calibration/reliability_buckets_rich.csv
  outputs/calibration/calibration_curve.png
  outputs/calibration/significance_report.csv
  outputs/calibration/production_gate_v2.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)

from wc2026.calibration.international_dataset import build_clean_dataset, make_temporal_splits
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.calibration.hybrid_elo_dc import fit_hybrid, evaluate_hybrid_on_dataset
from wc2026.calibration.baselines import (
    random_fn, empirical_freq_fn, elo_simple_fn,
    elo_draw_calibrated_fn, evaluate_row_model,
)
from wc2026.calibration.metrics import (
    negative_log_likelihood, brier_score_1x2, accuracy_1x2,
    calibration_error, outcome_from_goals,
)
from wc2026.calibration.significance import (
    batch_significance, summary_verdict, compute_significance,
)

# ─────────────────────────────────────────────────────────────────────────────
# Lightweight ablation model fitters (E, F, G)
# ─────────────────────────────────────────────────────────────────────────────

def fit_indep_poisson(train_df, elo_engine):
    """
    F: Independent Poisson, no per-team residuals, no DC.
    Fits log_base + beta_elo (2 params).
    Returns a callable fn(row) -> (p_home, p_draw, p_away).
    """
    from scipy.optimize import minimize

    home_teams = train_df["home_team"].tolist()
    away_teams = train_df["away_team"].tolist()
    dates      = train_df["date"].tolist()
    neutrals   = train_df["neutral"].tolist()
    h_goals    = np.array(train_df["home_goals"].tolist(), dtype=float)
    a_goals    = np.array(train_df["away_goals"].tolist(), dtype=float)
    h_lgamma   = np.array([math.lgamma(int(g)+1) for g in h_goals])
    a_lgamma   = np.array([math.lgamma(int(g)+1) for g in a_goals])

    elo_diffs = np.array([
        (elo_engine.get_elo(h, before_date=d) + (0.0 if n else 100.0)
         - elo_engine.get_elo(a, before_date=d)) / 400.0
        for h, a, d, n in zip(home_teams, away_teams, dates, neutrals)
    ])

    def objective(x):
        log_base, beta = x[0], x[1]
        lmh = log_base + beta * elo_diffs
        lma = log_base - beta * elo_diffs
        mh = np.clip(np.exp(lmh), 0.05, 8.0)
        ma = np.clip(np.exp(lma), 0.05, 8.0)
        ll = -mh + h_goals*np.log(mh) - h_lgamma - ma + a_goals*np.log(ma) - a_lgamma
        ll = np.where(np.isfinite(ll), ll, -30.0)
        return float(-np.mean(ll))

    mean_g = float((h_goals.mean() + a_goals.mean()) / 2)
    res = minimize(objective, [math.log(max(mean_g, 0.5)), 0.3],
                   method="L-BFGS-B",
                   bounds=[(-2.0, 1.5), (0.0, 2.0)],
                   options={"maxiter": 1000})
    log_base, beta = float(res.x[0]), float(res.x[1])

    def prob_1x2_poisson(mu_h, mu_a, max_goals=8):
        def pmf(k, mu):
            return math.exp(-mu + k*math.log(max(mu,1e-12)) - math.lgamma(k+1))
        ph = pd_ = pa = 0.0
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                p = pmf(i, mu_h) * pmf(j, mu_a)
                if i > j: ph += p
                elif i == j: pd_ += p
                else: pa += p
        t = ph + pd_ + pa
        return ph/t, pd_/t, pa/t

    def fn(row):
        eh = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        ea = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        diff = (eh + adj - ea) / 400.0
        mu_h = max(math.exp(log_base + beta*diff), 0.05)
        mu_a = max(math.exp(log_base - beta*diff), 0.05)
        return prob_1x2_poisson(mu_h, mu_a)
    return fn


def fit_elo_dc_rho_only(train_df, elo_engine):
    """
    G: Elo + DC rho correction, no per-team residuals.
    Fits log_base + beta_elo + rho (3 params).
    """
    from scipy.optimize import minimize

    home_teams = train_df["home_team"].tolist()
    away_teams = train_df["away_team"].tolist()
    dates      = train_df["date"].tolist()
    neutrals   = train_df["neutral"].tolist()
    h_goals    = np.array(train_df["home_goals"].tolist(), dtype=int)
    a_goals    = np.array(train_df["away_goals"].tolist(), dtype=int)
    h_lgamma   = np.array([math.lgamma(int(g)+1) for g in h_goals])
    a_lgamma   = np.array([math.lgamma(int(g)+1) for g in a_goals])

    elo_diffs = np.array([
        (elo_engine.get_elo(h, before_date=d) + (0.0 if n else 100.0)
         - elo_engine.get_elo(a, before_date=d)) / 400.0
        for h, a, d, n in zip(home_teams, away_teams, dates, neutrals)
    ])

    low_mask = (h_goals <= 1) & (a_goals <= 1)

    def objective(x):
        log_base, beta, rho = x[0], x[1], x[2]
        lmh = log_base + beta * elo_diffs
        lma = log_base - beta * elo_diffs
        mh = np.clip(np.exp(lmh), 0.05, 8.0)
        ma = np.clip(np.exp(lma), 0.05, 8.0)
        ll = -mh + h_goals*np.log(mh) - h_lgamma - ma + a_goals*np.log(ma) - a_lgamma
        if low_mask.any():
            mhL, maL = mh[low_mask], ma[low_mask]
            hgL, agL = h_goals[low_mask], a_goals[low_mask]
            tau = np.ones(low_mask.sum())
            tau[(hgL==0)&(agL==0)] = np.maximum(1.0 - mhL[(hgL==0)&(agL==0)]*maL[(hgL==0)&(agL==0)]*rho, 1e-9)
            tau[(hgL==1)&(agL==0)] = np.maximum(1.0 + maL[(hgL==1)&(agL==0)]*rho, 1e-9)
            tau[(hgL==0)&(agL==1)] = np.maximum(1.0 + mhL[(hgL==0)&(agL==1)]*rho, 1e-9)
            tau[(hgL==1)&(agL==1)] = np.maximum(1.0 - rho, 1e-9)
            ll[low_mask] += np.log(tau)
        ll = np.where(np.isfinite(ll), ll, -30.0)
        return float(-np.mean(ll))

    mean_g = float((train_df["home_goals"].mean() + train_df["away_goals"].mean()) / 2)
    res = minimize(objective, [math.log(max(mean_g, 0.5)), 0.3, -0.05],
                   method="L-BFGS-B",
                   bounds=[(-2.0, 1.5), (0.0, 2.0), (-0.20, 0.20)],
                   options={"maxiter": 1000})
    log_base, beta, rho = float(res.x[0]), float(res.x[1]), float(res.x[2])

    def prob_1x2_dc(mu_h, mu_a, max_goals=8):
        def pmf(k, mu):
            return math.exp(-mu + k*math.log(max(mu,1e-12)) - math.lgamma(k+1))
        def tau(i, j):
            if i==0 and j==0: return max(1.0 - mu_h*mu_a*rho, 1e-9)
            if i==1 and j==0: return max(1.0 + mu_a*rho, 1e-9)
            if i==0 and j==1: return max(1.0 + mu_h*rho, 1e-9)
            if i==1 and j==1: return max(1.0 - rho, 1e-9)
            return 1.0
        ph = pd_ = pa = 0.0
        for i in range(max_goals+1):
            for j in range(max_goals+1):
                p = pmf(i, mu_h)*pmf(j, mu_a)*tau(i, j)
                if i > j: ph += p
                elif i == j: pd_ += p
                else: pa += p
        t = ph + pd_ + pa
        return ph/t, pd_/t, pa/t

    def fn(row):
        eh = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        ea = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        diff = (eh + adj - ea) / 400.0
        mu_h = max(math.exp(log_base + beta*diff), 0.05)
        mu_a = max(math.exp(log_base - beta*diff), 0.05)
        return prob_1x2_dc(mu_h, mu_a)
    return fn


def make_elo_no_home_fn(elo_engine, draw_bias=0.22):
    """C: Elo-only with no home advantage."""
    def fn(row):
        eh = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        ea = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        p_win = 1.0 / (1.0 + 10.0 ** (-(eh - ea) / 400.0))
        p_lose = 1.0 - p_win
        return (p_win*(1-draw_bias), draw_bias, p_lose*(1-draw_bias))
    return fn


def make_hybrid_fn(params, elo_engine):
    """Callable wrapper for a fitted HybridParams."""
    def fn(row):
        eh = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        ea = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        return params.prob_1x2(row["home_team"], row["away_team"], eh+adj, ea)
    return fn


# ─────────────────────────────────────────────────────────────────────────────
# Reliability buckets (for calibration curve)
# ─────────────────────────────────────────────────────────────────────────────

def compute_reliability_buckets(
    df: pd.DataFrame, fn, model: str, split: str, n_bins: int = 10
) -> list[dict]:
    flat_probs, flat_outcomes = [], []
    for _, row in df.iterrows():
        try:
            ph, pd_, pa = fn(row)
        except Exception:
            ph, pd_, pa = 1/3, 1/3, 1/3
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
        n = int(mask.sum())
        if n == 0:
            continue
        rows.append({
            "model": model,
            "split": split,
            "bucket_min": round(float(lo), 2),
            "bucket_max": round(float(hi), 2),
            "predicted_mean": round(float(flat_probs[mask].mean()), 4),
            "observed_frequency": round(float(flat_outcomes[mask].mean()), 4),
            "count": n,
            "abs_error": round(abs(float(flat_probs[mask].mean()) - float(flat_outcomes[mask].mean())), 4),
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Calibration curve plot
# ─────────────────────────────────────────────────────────────────────────────

def plot_calibration_curve(buckets_df: pd.DataFrame, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = buckets_df["model"].unique()
    colors = {"elo_calib": "#2A9D8F", "hybrid": "#E63946",
              "elo_simple": "#E9C46A", "random": "#aaaaaa"}
    markers = {"elo_calib": "o", "hybrid": "s", "elo_simple": "^", "random": "D"}

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="#1a1a2e")
    for ax in axes:
        ax.set_facecolor("#12121e")
        ax.tick_params(colors="#cccccc")
        for spine in ax.spines.values():
            spine.set_color("#444444")

    # Left: all splits combined (elo_calib vs hybrid)
    ax = axes[0]
    ax.plot([0,1], [0,1], "w--", lw=1.2, alpha=0.5, label="Perfect")
    for model in ["elo_calib", "hybrid"]:
        sub = buckets_df[buckets_df["model"] == model]
        if sub.empty:
            continue
        # Aggregate across splits: weighted mean by count
        grouped = sub.groupby(["bucket_min","bucket_max"]).apply(
            lambda g: pd.Series({
                "predicted_mean": np.average(g["predicted_mean"], weights=g["count"]),
                "observed_frequency": np.average(g["observed_frequency"], weights=g["count"]),
                "count": g["count"].sum(),
            })
        ).reset_index()
        c = colors.get(model, "#888888")
        m = markers.get(model, "o")
        sc = ax.scatter(grouped["predicted_mean"], grouped["observed_frequency"],
                        s=grouped["count"]/10, c=c, marker=m, alpha=0.85,
                        label=model, zorder=5)
        ax.plot(grouped["predicted_mean"], grouped["observed_frequency"],
                color=c, alpha=0.5, lw=1)

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xlabel("Predicted probability", color="#cccccc")
    ax.set_ylabel("Observed frequency", color="#cccccc")
    ax.set_title("Reliability diagram (all splits)\nBubble size ∝ count", color="white", pad=8)
    legend = ax.legend(facecolor="#0c0c14", edgecolor="#444444", labelcolor="#cccccc")

    # Right: per-split delta calibration error (bar chart)
    ax2 = axes[1]
    split_names = sorted(buckets_df["split"].unique())
    x = np.arange(len(split_names))
    width = 0.35

    elo_ece, hybrid_ece = [], []
    for sp in split_names:
        for mdl, store in [("elo_calib", elo_ece), ("hybrid", hybrid_ece)]:
            sub = buckets_df[(buckets_df["model"]==mdl) & (buckets_df["split"]==sp)]
            if sub.empty:
                store.append(0.0)
            else:
                # Weighted ECE
                total = sub["count"].sum()
                ece = float((sub["abs_error"] * sub["count"] / max(total,1)).sum())
                store.append(ece)

    bars1 = ax2.bar(x - width/2, elo_ece,   width, label="elo_calib", color="#2A9D8F", alpha=0.8)
    bars2 = ax2.bar(x + width/2, hybrid_ece, width, label="hybrid",   color="#E63946", alpha=0.8)
    ax2.set_xticks(x)
    short_names = [s.replace("train_pre","t<").replace("_test_","→").replace("wc2022_holdout","WC22 holdout")
                   for s in split_names]
    ax2.set_xticklabels(short_names, rotation=20, ha="right", fontsize=8, color="#cccccc")
    ax2.set_ylabel("ECE (lower = better calibrated)", color="#cccccc")
    ax2.set_title("Expected Calibration Error per split", color="white", pad=8)
    ax2.legend(facecolor="#0c0c14", edgecolor="#444444", labelcolor="#cccccc")

    plt.tight_layout(pad=2.0)
    fig.suptitle("P2.5 Calibration Audit — Hybrid vs Elo-Calibrated", y=1.01,
                 color="white", fontsize=13)
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight",
                facecolor="#1a1a2e")
    plt.close()
    print(f"  Saved calibration curve → {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_split_ablation(
    split_name, train_df, test_df, full_df,
    lambda_val=0.05, n_restarts=2, verbose=True,
) -> dict:
    if verbose:
        print(f"\n{'='*55}")
        print(f"SPLIT: {split_name}  train={len(train_df):,}  test={len(test_df):,}")

    if len(test_df) == 0:
        print("  SKIP: empty test set")
        return {}

    test_start = test_df["date"].min()
    elo_history = full_df[full_df["date"] < test_start].copy()
    elo = RollingEloEngine()
    elo.fit(elo_history)
    if verbose:
        print(f"  Elo fitted on {len(elo_history):,} matches before {test_start}")

    results = {
        "split": split_name,
        "n_train": len(train_df),
        "n_test": len(test_df),
    }
    buckets = []

    # ── A: Random ────────────────────────────────────────────────────────────
    r = evaluate_row_model(test_df, random_fn)
    results["A_random_nll"] = r["nll"]
    results["A_random_brier"] = r["brier"]
    results["A_random_ece"] = r["ece"]
    if verbose: print(f"  A random      NLL={r['nll']:.5f}")

    # ── B: Empirical frequency ────────────────────────────────────────────────
    emp_fn = empirical_freq_fn(train_df)
    r = evaluate_row_model(test_df, emp_fn)
    results["B_empirical_nll"] = r["nll"]
    results["B_empirical_brier"] = r["brier"]
    results["B_empirical_ece"] = r["ece"]
    if verbose: print(f"  B empirical   NLL={r['nll']:.5f}")

    # ── C: Elo no home advantage ───────────────────────────────────────────────
    elo_no_home = make_elo_no_home_fn(elo)
    r = evaluate_row_model(test_df, elo_no_home)
    results["C_elo_nohome_nll"] = r["nll"]
    results["C_elo_nohome_brier"] = r["brier"]
    results["C_elo_nohome_ece"] = r["ece"]
    if verbose: print(f"  C elo_nohome  NLL={r['nll']:.5f}")

    # ── D: Elo + home advantage (elo_simple) ──────────────────────────────────
    elo_home_fn = elo_simple_fn(elo)
    r = evaluate_row_model(test_df, elo_home_fn)
    results["D_elo_home_nll"] = r["nll"]
    results["D_elo_home_brier"] = r["brier"]
    results["D_elo_home_ece"] = r["ece"]
    if verbose: print(f"  D elo_home    NLL={r['nll']:.5f}")

    # ── E: Elo + calibrated draw ──────────────────────────────────────────────
    elo_cal_fn = elo_draw_calibrated_fn(elo, train_df)
    r = evaluate_row_model(test_df, elo_cal_fn)
    results["E_elo_calib_nll"] = r["nll"]
    results["E_elo_calib_brier"] = r["brier"]
    results["E_elo_calib_ece"] = r["ece"]
    buckets += compute_reliability_buckets(test_df, elo_cal_fn, "elo_calib", split_name)
    if verbose: print(f"  E elo_calib   NLL={r['nll']:.5f}")

    # ── F: Independent Poisson (global, no per-team) ──────────────────────────
    ip_fn = fit_indep_poisson(train_df, elo)
    r = evaluate_row_model(test_df, ip_fn)
    results["F_indep_poisson_nll"] = r["nll"]
    results["F_indep_poisson_brier"] = r["brier"]
    results["F_indep_poisson_ece"] = r["ece"]
    if verbose: print(f"  F indep_pois  NLL={r['nll']:.5f}")

    # ── G: Elo + DC rho only (no per-team) ────────────────────────────────────
    dc_rho_fn = fit_elo_dc_rho_only(train_df, elo)
    r = evaluate_row_model(test_df, dc_rho_fn)
    results["G_elo_dc_rho_nll"] = r["nll"]
    results["G_elo_dc_rho_brier"] = r["brier"]
    results["G_elo_dc_rho_ece"] = r["ece"]
    if verbose: print(f"  G elo_dc_rho  NLL={r['nll']:.5f}")

    # ── H: Hybrid, rho=0 forced ────────────────────────────────────────────────
    if verbose: print(f"  H hybrid_norho fitting...")
    params_h = fit_hybrid(
        train_df, elo,
        regularization_lambda=lambda_val,
        rho_bounds=(0.0, 0.0),   # forces rho=0
        n_restarts=n_restarts, verbose=False,
    )
    hybrid_norho_fn = make_hybrid_fn(params_h, elo)
    r = evaluate_row_model(test_df, hybrid_norho_fn)
    results["H_hybrid_norho_nll"] = r["nll"]
    results["H_hybrid_norho_brier"] = r["brier"]
    results["H_hybrid_norho_ece"] = r["ece"]
    if verbose: print(f"  H hybrid_norho NLL={r['nll']:.5f}  (beta_elo={params_h.beta_elo:.3f})")

    # ── I: Full Hybrid ──────────────────────────────────────────────────────────
    if verbose: print(f"  I hybrid_full fitting...")
    params_i = fit_hybrid(
        train_df, elo,
        regularization_lambda=lambda_val,
        rho_bounds=(-0.20, 0.20),
        n_restarts=n_restarts, verbose=False,
    )
    hybrid_full_fn = make_hybrid_fn(params_i, elo)
    r = evaluate_row_model(test_df, hybrid_full_fn)
    results["I_hybrid_full_nll"] = r["nll"]
    results["I_hybrid_full_brier"] = r["brier"]
    results["I_hybrid_full_ece"] = r["ece"]
    results["I_hybrid_full_beta_elo"] = round(params_i.beta_elo, 4)
    results["I_hybrid_full_rho"] = round(params_i.rho, 4)
    buckets += compute_reliability_buckets(test_df, hybrid_full_fn, "hybrid", split_name)
    if verbose: print(f"  I hybrid_full  NLL={r['nll']:.5f}  (beta_elo={params_i.beta_elo:.3f}, rho={params_i.rho:.4f})")

    results["_buckets"] = buckets
    return results


def make_ablation_summary(rows: list[dict]) -> str:
    """Build ablation_summary.md content."""
    models = [
        ("A_random", "Random (1/3, 1/3, 1/3)"),
        ("B_empirical", "Empirical frequency"),
        ("C_elo_nohome", "Elo only (no home adv)"),
        ("D_elo_home", "Elo + home advantage"),
        ("E_elo_calib", "Elo + calibrated draw"),
        ("F_indep_poisson", "Independent Poisson (global)"),
        ("G_elo_dc_rho", "Elo + DC rho only (no residuals)"),
        ("H_hybrid_norho", "Hybrid, rho=0 (residuals, no DC)"),
        ("I_hybrid_full", "Full Hybrid (residuals + DC rho)"),
    ]

    header = "# P2.5 Ablation Study\n\n"
    header += "Additive decomposition of model components across 4 temporal splits.\n"
    header += "Rule: Δ < 0.01 NLL on large splits treated as noise, not victory.\n\n"

    # NLL table
    lines = ["## NLL per split (lower = better)\n"]
    split_names = [r["split"] for r in rows]
    col_header = "| Model | " + " | ".join(split_names) + " | Avg |"
    separator  = "|:------|" + " | ".join([":---:"] * len(split_names)) + " | :---: |"
    lines.append(col_header)
    lines.append(separator)
    for key, label in models:
        vals = []
        for r in rows:
            col = f"{key}_nll"
            v = r.get(col)
            vals.append(f"{v:.5f}" if v is not None else "—")
        avg = [r.get(f"{key}_nll") for r in rows]
        avg_v = sum(x for x in avg if x is not None) / max(len([x for x in avg if x is not None]), 1)
        lines.append(f"| {label} | " + " | ".join(vals) + f" | **{avg_v:.5f}** |")
    lines.append("")

    # Brier table
    lines.append("## Brier score per split (lower = better)\n")
    lines.append(col_header.replace("NLL", "Brier"))
    lines.append(separator)
    for key, label in models:
        vals = []
        for r in rows:
            col = f"{key}_brier"
            v = r.get(col)
            vals.append(f"{v:.5f}" if v is not None else "—")
        avg = [r.get(f"{key}_brier") for r in rows]
        avg_v = sum(x for x in avg if x is not None) / max(len([x for x in avg if x is not None]), 1)
        lines.append(f"| {label} | " + " | ".join(vals) + f" | **{avg_v:.5f}** |")
    lines.append("")

    # Incremental gains analysis
    lines.append("## Incremental contribution of each component\n")
    lines.append("Average NLL gain from adding each layer to the previous:\n")

    def avg_nll(key):
        vals = [r.get(f"{key}_nll") for r in rows if r.get(f"{key}_nll") is not None]
        return sum(vals)/max(len(vals),1)

    pairs = [
        ("A→D: +home advantage",              avg_nll("D_elo_home") - avg_nll("A_random")),
        ("D→E: +calibrated draw",             avg_nll("E_elo_calib") - avg_nll("D_elo_home")),
        ("E→F: Poisson vs logistic (global)", avg_nll("F_indep_poisson") - avg_nll("E_elo_calib")),
        ("F→G: +DC rho (no residuals)",       avg_nll("G_elo_dc_rho") - avg_nll("F_indep_poisson")),
        ("E→H: +per-team residuals (no DC)",  avg_nll("H_hybrid_norho") - avg_nll("E_elo_calib")),
        ("H→I: +DC rho correction",           avg_nll("I_hybrid_full") - avg_nll("H_hybrid_norho")),
        ("E→I: full hybrid vs Elo-calib",     avg_nll("I_hybrid_full") - avg_nll("E_elo_calib")),
    ]
    lines.append("| Layer change | Avg ΔNLL | Direction |")
    lines.append("|:-------------|:--------:|:---------:|")
    for name, delta in pairs:
        direction = "✓ improves" if delta < -0.001 else ("~ noise" if abs(delta) < 0.005 else "✗ degrades")
        lines.append(f"| {name} | {delta:+.5f} | {direction} |")
    lines.append("")

    # Production candidates
    lines.append("## Production candidates\n")
    lines.append("Model is marked PRODUCTION_CANDIDATE if it beats E (elo_calib) on avg NLL.\n")
    lines.append("| Model | Avg NLL | vs elo_calib | Status |")
    lines.append("|:------|:-------:|:------------:|:------:|")
    ref = avg_nll("E_elo_calib")
    for key, label in models:
        v = avg_nll(key)
        delta = v - ref
        if key == "E_elo_calib":
            status = "REFERENCE"
        elif delta < -0.003:
            status = "PRODUCTION_CANDIDATE"
        elif delta < 0.003:
            status = "EXPERIMENTAL"
        else:
            status = "REJECTED"
        lines.append(f"| {label} | {v:.5f} | {delta:+.5f} | {status} |")
    lines.append("")

    return header + "\n".join(lines)


def compute_production_gate_v2(
    rows: list[dict],
    sig_df: pd.DataFrame,
) -> dict:
    def avg_nll(key):
        vals = [r.get(f"{key}_nll") for r in rows if r.get(f"{key}_nll") is not None]
        return sum(vals)/max(len(vals),1)

    elo_avg = avg_nll("E_elo_calib")
    hybrid_avg = avg_nll("I_hybrid_full")
    delta_avg = hybrid_avg - elo_avg

    sig_summary = summary_verdict(sig_df) if len(sig_df) > 0 else {}
    n_clear    = sig_summary.get("n_clear_win", 0)
    n_marginal = sig_summary.get("n_marginal_win", 0)
    n_loss     = sig_summary.get("n_loss", 0)

    # Stability: coefficient of variation of beta_elo across splits
    betas = [r.get("I_hybrid_full_beta_elo") for r in rows if r.get("I_hybrid_full_beta_elo")]
    beta_cv = np.std(betas)/max(np.mean(betas),1e-6) if len(betas) >= 2 else 1.0
    beta_stable = bool(beta_cv < 0.20)

    # Rho check: not stuck at boundary
    rhos = [r.get("I_hybrid_full_rho") for r in rows if r.get("I_hybrid_full_rho") is not None]
    rho_not_boundary = all(-0.18 < float(r) < 0.18 for r in rhos) if rhos else False

    # ECE check: hybrid ECE not worse than elo_calib by >5%
    ece_elo_vals = [r.get("E_elo_calib_ece") for r in rows if r.get("E_elo_calib_ece") is not None]
    ece_hyb_vals = [r.get("I_hybrid_full_ece") for r in rows if r.get("I_hybrid_full_ece") is not None]
    if ece_elo_vals and ece_hyb_vals:
        avg_ece_elo = sum(ece_elo_vals)/len(ece_elo_vals)
        avg_ece_hyb = sum(ece_hyb_vals)/len(ece_hyb_vals)
        ece_ok = bool(avg_ece_hyb <= avg_ece_elo * 1.05)
    else:
        avg_ece_elo = avg_ece_hyb = None
        ece_ok = True

    # Residuals add signal: H (norho) vs E (elo_calib)
    norho_avg = avg_nll("H_hybrid_norho")
    residuals_add_signal = bool(norho_avg < elo_avg - 0.002)

    # WC2022 holdout: catastrophic loss if Δ > 0.05
    wc_row = next((r for r in rows if "wc2022" in r.get("split","").lower()), None)
    wc_delta = None
    wc_ok = True
    if wc_row:
        wc_elo = wc_row.get("E_elo_calib_nll")
        wc_hyb = wc_row.get("I_hybrid_full_nll")
        if wc_elo and wc_hyb:
            wc_delta = round(wc_hyb - wc_elo, 5)
            wc_ok = bool(wc_delta < 0.05)

    # Final verdict
    criteria_met = []
    criteria_failed = []

    if delta_avg < 0:
        criteria_met.append(f"hybrid beats elo_calib average NLL ({delta_avg:+.5f})")
    else:
        criteria_failed.append(f"hybrid does NOT beat elo_calib average NLL ({delta_avg:+.5f})")

    if wc_ok:
        criteria_met.append("no catastrophic loss on WC2022 holdout")
    else:
        criteria_failed.append(f"WC2022 holdout loss: Δ={wc_delta:+.5f}")

    if n_clear >= 1:
        criteria_met.append(f"at least one clear_win split (n_clear={n_clear})")
    else:
        criteria_failed.append(f"no clear_win split (only marginal: {n_marginal})")

    if ece_ok:
        criteria_met.append("hybrid ECE not worse than elo_calib by >5%")
    else:
        criteria_failed.append(f"hybrid ECE worse (elo={avg_ece_elo:.4f}, hyb={avg_ece_hyb:.4f})")

    if rho_not_boundary:
        criteria_met.append("rho not stuck at ±0.20 boundary")
    else:
        criteria_failed.append("rho hitting ±0.18 boundary in some splits")

    if beta_stable:
        criteria_met.append(f"beta_elo stable across splits (CV={beta_cv:.3f})")
    else:
        criteria_failed.append(f"beta_elo unstable (CV={beta_cv:.3f})")

    if residuals_add_signal:
        criteria_met.append("per-team residuals add signal beyond Elo-only")
    else:
        criteria_failed.append("per-team residuals show no clear signal beyond Elo-only")

    n_met = len(criteria_met)
    n_fail = len(criteria_failed)

    if n_met >= 6 and n_clear >= 2:
        verdict = "PASS"
    elif n_met >= 4 and n_fail <= 3:
        verdict = "BORDERLINE_EXPERIMENTAL"
    else:
        verdict = "FAIL"

    return {
        "verdict": verdict,
        "criteria_met": criteria_met,
        "criteria_failed": criteria_failed,
        "n_criteria_met": n_met,
        "n_criteria_failed": n_fail,
        "avg_nll": {
            "elo_calib": round(elo_avg, 5),
            "hybrid": round(hybrid_avg, 5),
            "delta": round(delta_avg, 5),
        },
        "significance_summary": sig_summary,
        "beta_elo_cv": round(float(beta_cv), 4),
        "rho_not_boundary": rho_not_boundary,
        "ece": {
            "elo_calib": round(avg_ece_elo, 5) if avg_ece_elo else None,
            "hybrid": round(avg_ece_hyb, 5) if avg_ece_hyb else None,
            "ok": ece_ok,
        },
        "wc2022_holdout_delta": wc_delta,
        "wc2022_ok": wc_ok,
        "residuals_add_signal": residuals_add_signal,
        "note": (
            "PASS → integrate into production CalibratedHybridMatchModel"
            if verdict == "PASS"
            else "BORDERLINE_EXPERIMENTAL → keep expert model, document hybrid as experimental"
            if verdict == "BORDERLINE_EXPERIMENTAL"
            else "FAIL → do not integrate, stick with Elo-calibrated baseline"
        ),
    }


def main():
    print("=" * 60)
    print("P2.5 Ablation Study")
    print("=" * 60)

    print("\n[1/7] Loading dataset...")
    df, _ = build_clean_dataset(min_year=1990, max_year=2025)
    splits = make_temporal_splits(df)
    print(f"  {len(df):,} matches, {df['tournament'].nunique()} tournaments")

    print("\n[2/7] Running ablation across splits...")
    all_results = []
    all_buckets = []

    for split_name, (train_df, test_df) in splits.items():
        if len(test_df) == 0:
            print(f"  SKIP {split_name}: empty test")
            continue
        r = run_split_ablation(
            split_name, train_df, test_df, df,
            lambda_val=0.05, n_restarts=2, verbose=True,
        )
        if r:
            buckets = r.pop("_buckets", [])
            all_results.append(r)
            all_buckets.extend(buckets)

    print(f"\n[3/7] Saving ablation results...")
    # Save ablation CSV (exclude internal keys)
    abl_df = pd.DataFrame(all_results)
    abl_df.to_csv(OUT / "ablation_results.csv", index=False)
    print(f"  Saved ablation_results.csv ({len(abl_df)} splits)")

    # Save reliability buckets
    buck_df = pd.DataFrame(all_buckets)
    buck_df.to_csv(OUT / "reliability_buckets.csv", index=False)
    print(f"  Saved reliability_buckets.csv ({len(buck_df)} rows)")

    print("\n[4/7] Computing significance tests...")
    sig_rows = []
    for r in all_results:
        res = compute_significance(
            split=r["split"],
            n_test=r["n_test"],
            model_a="elo_calib",
            model_b="hybrid_full",
            nll_a=r.get("E_elo_calib_nll", float("nan")),
            nll_b=r.get("I_hybrid_full_nll", float("nan")),
        )
        sig_rows.append(res.to_dict())
    sig_df = pd.DataFrame(sig_rows)
    sig_df.to_csv(OUT / "significance_report.csv", index=False)
    print("  Saved significance_report.csv")
    print(f"  Verdicts: {sig_df['verdict'].value_counts().to_dict()}")

    print("\n[5/7] Generating calibration curve...")
    if not buck_df.empty:
        plot_calibration_curve(buck_df, OUT / "calibration_curve.png")
    else:
        print("  WARNING: no reliability buckets, skipping plot")

    print("\n[6/7] Computing production gate v2...")
    gate_v2 = compute_production_gate_v2(all_results, sig_df)
    (OUT / "production_gate_v2.json").write_text(json.dumps(gate_v2, indent=2))
    print(f"  Verdict: {gate_v2['verdict']}")
    print(f"  Criteria met: {gate_v2['n_criteria_met']}/{gate_v2['n_criteria_met']+gate_v2['n_criteria_failed']}")

    print("\n[7/7] Writing ablation summary...")
    summary_md = make_ablation_summary(all_results)
    (OUT / "ablation_summary.md").write_text(summary_md)
    print("  Saved ablation_summary.md")

    # Final report
    print("\n" + "="*60)
    print("P2.5 RESULTS")
    print("="*60)
    def avg_nll(key):
        vals = [r.get(f"{key}_nll") for r in all_results if r.get(f"{key}_nll") is not None]
        return sum(vals)/max(len(vals),1)

    models_summary = [
        ("A  Random",                   "A_random"),
        ("B  Empirical",                "B_empirical"),
        ("C  Elo (no home adv)",        "C_elo_nohome"),
        ("D  Elo + home adv",           "D_elo_home"),
        ("E  Elo + calib draw",         "E_elo_calib"),
        ("F  Indep Poisson (global)",   "F_indep_poisson"),
        ("G  Elo + DC rho only",        "G_elo_dc_rho"),
        ("H  Hybrid, rho=0",            "H_hybrid_norho"),
        ("I  Full Hybrid",              "I_hybrid_full"),
    ]
    print("\nAverage NLL across splits:")
    ref_nll = avg_nll("E_elo_calib")
    for label, key in models_summary:
        v = avg_nll(key)
        delta = v - ref_nll
        marker = "◀" if key == "E_elo_calib" else (" ✓" if delta < -0.001 else "")
        print(f"  {label:35s}  {v:.5f}  ({delta:+.5f}){marker}")

    print(f"\nSignificance (hybrid vs elo_calib):")
    for _, row in sig_df.iterrows():
        print(f"  {row['split']:45s}  {row['verdict']:20s}  z={row['z_score']:+.2f}")

    print(f"\nProduction Gate V2: {gate_v2['verdict']}")
    print(f"  {gate_v2['note']}")

    return gate_v2


if __name__ == "__main__":
    main()
