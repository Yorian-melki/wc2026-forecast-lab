#!/usr/bin/env python3
"""
Bootstrap confidence interval for β_elo.

Approach: fix pre-computed Elo diffs as features (treats Elo computation as known),
resample match indices, refit β_elo via MLE on resampled data.

This gives CI for β conditional on the rolling Elo values (not jointly with Elo
hyperparameters). Full joint bootstrap would require refitting rolling Elo for each
resample — computationally too expensive (~30min for 200 iterations).

Usage: PYTHONPATH=src python scripts/bootstrap_beta_ci.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine

N_BOOTSTRAP = 200
SEED = 20260613


def fit_beta_given_features(
    elo_diffs: np.ndarray,
    h_goals: np.ndarray,
    a_goals: np.ndarray,
    h_lgamma: np.ndarray,
    a_lgamma: np.ndarray,
    low_mask: np.ndarray,
    init_log_base: float = 0.227,
    init_beta: float = 0.544,
    init_rho: float = -0.021,
) -> tuple[float, float, float, float]:
    """Fit log_base, beta_elo, rho on given features. Returns (log_base, beta, rho, nll)."""

    def objective(x):
        log_base, beta, rho = x[0], x[1], x[2]
        lmh = log_base + beta * elo_diffs
        lma = log_base - beta * elo_diffs
        mh = np.clip(np.exp(lmh), 0.05, 8.0)
        ma = np.clip(np.exp(lma), 0.05, 8.0)
        ll = (-mh + h_goals * np.log(mh) - h_lgamma
              - ma + a_goals * np.log(ma) - a_lgamma)
        if low_mask.any():
            mhL, maL = mh[low_mask], ma[low_mask]
            hgL, agL = h_goals[low_mask], a_goals[low_mask]
            tau = np.ones(low_mask.sum())
            tau[(hgL == 0) & (agL == 0)] = np.maximum(
                1.0 - mhL[(hgL == 0) & (agL == 0)] * maL[(hgL == 0) & (agL == 0)] * rho, 1e-9)
            tau[(hgL == 1) & (agL == 0)] = np.maximum(1.0 + maL[(hgL == 1) & (agL == 0)] * rho, 1e-9)
            tau[(hgL == 0) & (agL == 1)] = np.maximum(1.0 + mhL[(hgL == 0) & (agL == 1)] * rho, 1e-9)
            tau[(hgL == 1) & (agL == 1)] = np.maximum(1.0 - rho, 1e-9)
            ll[low_mask] += np.log(tau)
        ll = np.where(np.isfinite(ll), ll, -30.0)
        return float(-np.mean(ll))

    res = minimize(
        objective,
        [init_log_base, init_beta, init_rho],
        method="L-BFGS-B",
        bounds=[(-2.0, 1.5), (0.0, 2.0), (-0.20, 0.20)],
        options={"maxiter": 500, "ftol": 1e-9, "gtol": 1e-7},
    )
    lb, b, r = float(res.x[0]), float(res.x[1]), float(res.x[2])
    return lb, b, r, float(res.fun)


def main() -> None:
    print(f"Bootstrap β_elo CI: {N_BOOTSTRAP} iterations, seed={SEED}")
    t_start = time.monotonic()

    # Load and prepare dataset
    print("  Loading dataset...")
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    print(f"  Dataset: {len(df):,} competitive matches")

    # Compute rolling Elo ONCE (fixed features)
    print("  Computing rolling Elo...")
    engine = RollingEloEngine()
    engine.fit(df)

    home_teams = df["home_team"].tolist()
    away_teams = df["away_team"].tolist()
    dates      = df["date"].tolist()
    neutrals   = df["neutral"].tolist()
    h_goals    = np.array(df["home_goals"].tolist(), dtype=float)
    a_goals    = np.array(df["away_goals"].tolist(), dtype=float)
    h_lgamma   = np.array([math.lgamma(int(g) + 1) for g in h_goals])
    a_lgamma   = np.array([math.lgamma(int(g) + 1) for g in a_goals])
    low_mask   = (h_goals <= 1) & (a_goals <= 1)

    elo_diffs = np.array([
        (engine.get_elo(h, before_date=d) + (0.0 if n else 100.0)
         - engine.get_elo(a, before_date=d)) / 400.0
        for h, a, d, n in zip(home_teams, away_teams, dates, neutrals)
    ])

    # Fit on full dataset (production estimate)
    print("  Fitting on full dataset (production point estimate)...")
    lb_full, b_full, r_full, nll_full = fit_beta_given_features(
        elo_diffs, h_goals, a_goals, h_lgamma, a_lgamma, low_mask
    )
    print(f"  Production: log_base={lb_full:.4f} β_elo={b_full:.4f} ρ={r_full:.4f} NLL={nll_full:.5f}")

    # Bootstrap
    print(f"  Running {N_BOOTSTRAP} bootstrap iterations...")
    rng = np.random.default_rng(SEED)
    n = len(df)

    betas = []
    log_bases = []
    rhos = []

    for i in range(N_BOOTSTRAP):
        idx = rng.integers(0, n, size=n)  # resample with replacement
        b_lb, b_beta, b_rho, _ = fit_beta_given_features(
            elo_diffs[idx], h_goals[idx], a_goals[idx],
            h_lgamma[idx], a_lgamma[idx], low_mask[idx],
            init_log_base=lb_full, init_beta=b_full, init_rho=r_full,
        )
        betas.append(b_beta)
        log_bases.append(b_lb)
        rhos.append(b_rho)

        if (i + 1) % 20 == 0:
            elapsed = time.monotonic() - t_start
            eta = elapsed / (i + 1) * (N_BOOTSTRAP - i - 1)
            print(f"    {i+1}/{N_BOOTSTRAP}  β={b_beta:.4f}  ETA {eta:.0f}s")

    # Compute statistics
    betas = np.array(betas)
    log_bases = np.array(log_bases)
    rhos = np.array(rhos)

    def ci(arr, alpha=0.05):
        return float(np.percentile(arr, alpha/2*100)), float(np.percentile(arr, (1-alpha/2)*100))

    beta_ci = ci(betas)
    lb_ci = ci(log_bases)
    rho_ci = ci(rhos)

    elapsed = time.monotonic() - t_start
    print(f"\n  Results ({N_BOOTSTRAP} bootstrap iterations, {elapsed:.0f}s):")
    print(f"  β_elo:    {b_full:.4f}  95% CI [{beta_ci[0]:.4f}, {beta_ci[1]:.4f}]")
    print(f"  log_base: {lb_full:.4f}  95% CI [{lb_ci[0]:.4f}, {lb_ci[1]:.4f}]")
    print(f"  ρ:        {r_full:.4f}  95% CI [{rho_ci[0]:.4f}, {rho_ci[1]:.4f}]")
    print(f"  β_elo std: {betas.std():.4f}")

    # Stability check: how wide is the CI in % of the estimate?
    ci_width_pct = (beta_ci[1] - beta_ci[0]) / b_full * 100
    print(f"  β CI width: {ci_width_pct:.1f}% of estimate")
    if ci_width_pct < 20:
        stability = "STABLE"
    elif ci_width_pct < 40:
        stability = "ACCEPTABLE"
    else:
        stability = "WIDE — model sensitive to training data"
    print(f"  Stability: {stability}")

    # Save results
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_bootstrap": N_BOOTSTRAP,
        "seed": SEED,
        "n_train_matches": n,
        "method": "Residual bootstrap (fixed rolling-Elo features, resample match indices)",
        "limitation": (
            "Elo diffs treated as fixed — does not capture uncertainty from rolling Elo "
            "hyperparameters (K-factor, home advantage). Full joint bootstrap ~30min, not run."
        ),
        "full_dataset_fit": {
            "log_base": round(lb_full, 6),
            "beta_elo": round(b_full, 6),
            "rho": round(r_full, 6),
            "nll": round(nll_full, 6),
        },
        "bootstrap_results": {
            "beta_elo": {
                "mean": round(float(betas.mean()), 4),
                "std":  round(float(betas.std()), 4),
                "ci_95_lo": round(beta_ci[0], 4),
                "ci_95_hi": round(beta_ci[1], 4),
                "all_samples": [round(float(b), 4) for b in betas],
            },
            "log_base": {
                "mean": round(float(log_bases.mean()), 4),
                "std":  round(float(log_bases.std()), 4),
                "ci_95_lo": round(lb_ci[0], 4),
                "ci_95_hi": round(lb_ci[1], 4),
            },
            "rho": {
                "mean": round(float(rhos.mean()), 4),
                "std":  round(float(rhos.std()), 4),
                "ci_95_lo": round(rho_ci[0], 4),
                "ci_95_hi": round(rho_ci[1], 4),
            },
        },
        "stability_assessment": stability,
        "ci_width_pct": round(ci_width_pct, 1),
        "elapsed_seconds": round(elapsed, 1),
    }

    out_path = ROOT / "outputs" / "audit" / "beta_bootstrap_ci.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n  Saved → {out_path}")

    # Also update maturity files
    maturity_note = (
        f"β_elo bootstrap 95% CI: [{beta_ci[0]:.4f}, {beta_ci[1]:.4f}] "
        f"({N_BOOTSTRAP} iterations). "
        f"Stability: {stability}. CI width: {ci_width_pct:.1f}% of estimate."
    )
    print(f"  Maturity note: {maturity_note}")


if __name__ == "__main__":
    main()
