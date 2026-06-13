#!/usr/bin/env python3
"""Batch A — beta_elo uncertainty -> champion probability intervals.

1. Rebuild the exact fitting dataset (martj42 competitive 2010-2025) and the
   pre-match elo_diffs. Rolling Elo is INDEPENDENT of beta, so refitting beta on a
   resampled set is a fast vectorized 3-param minimize (no Elo recompute).
2. Nonparametric bootstrap: resample matches with replacement B times, refit
   (log_base, beta, rho) each time -> bootstrap distribution of beta_elo.
   (iid match bootstrap; residual match dependence makes this a LOWER bound on
   uncertainty — documented.)
3. Propagate: run WC2026 tournament sims at beta P5 / P50 / P95 with the production
   model (ML ensemble @ config weight). Per team the interval is
   [min(p_lo,p_hi), p_base, max(p_lo,p_hi)] (handles non-monotonicity: favorites rise
   with beta, underdogs fall).

Outputs: beta_uncertainty_bootstrap.{md,json}, champion_probability_intervals.csv,
data/live/champion_probability_intervals.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
from wc2026.data_loader import load_teams, load_config, load_groups
from wc2026.tournament import TournamentSimulator

B = 300          # bootstrap resamples
N_SIM = 50_000   # tournament sims per beta band
SEED = 20260613


def build_arrays():
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine()
    elo.fit(df)
    h, a, dts, nu = (df["home_team"].tolist(), df["away_team"].tolist(),
                     df["date"].tolist(), df["neutral"].tolist())
    hg = np.array(df["home_goals"].tolist(), dtype=int)
    ag = np.array(df["away_goals"].tolist(), dtype=int)
    hlg = np.array([math.lgamma(int(g) + 1) for g in hg])
    alg = np.array([math.lgamma(int(g) + 1) for g in ag])
    ediff = np.array([(elo.get_elo(hh, before_date=d) + (0.0 if n else 100.0)
                       - elo.get_elo(aa, before_date=d)) / 400.0
                      for hh, aa, d, n in zip(h, a, dts, nu)])
    return ediff, hg, ag, hlg, alg


def make_objective(ediff, hg, ag, hlg, alg):
    low = (hg <= 1) & (ag <= 1)
    h00 = low & (hg == 0) & (ag == 0); h10 = low & (hg == 1) & (ag == 0)
    h01 = low & (hg == 0) & (ag == 1); h11 = low & (hg == 1) & (ag == 1)

    def obj(x):
        lb, beta, rho = x
        mh = np.clip(np.exp(lb + beta * ediff), 0.05, 8.0)
        ma = np.clip(np.exp(lb - beta * ediff), 0.05, 8.0)
        ll = -mh + hg * np.log(mh) - hlg - ma + ag * np.log(ma) - alg
        tau = np.ones_like(mh)
        tau = np.where(h00, np.maximum(1 - mh * ma * rho, 1e-9), tau)
        tau = np.where(h10, np.maximum(1 + ma * rho, 1e-9), tau)
        tau = np.where(h01, np.maximum(1 + mh * rho, 1e-9), tau)
        tau = np.where(h11, np.maximum(1 - rho, 1e-9), tau)
        ll = ll + np.where(low, np.log(tau), 0.0)
        ll = np.where(np.isfinite(ll), ll, -30.0)
        return float(-np.mean(ll))
    return obj


def fit_beta(ediff, hg, ag, hlg, alg, x0):
    obj = make_objective(ediff, hg, ag, hlg, alg)
    res = minimize(obj, x0, method="L-BFGS-B",
                   bounds=[(-2.0, 1.5), (0.0, 2.0), (-0.20, 0.20)],
                   options={"maxiter": 1000, "ftol": 1e-10})
    return res.x  # (log_base, beta, rho)


def main(b=B, n_sim=N_SIM, seed=SEED):
    t0 = time.monotonic()
    NOW = datetime.now(timezone.utc).isoformat()
    print("Building dataset + elo_diffs ...")
    ediff, hg, ag, hlg, alg = build_arrays()
    n = len(ediff)
    print(f"  {n:,} competitive matches")

    x0 = [math.log(1.3), 0.45, -0.04]
    point = fit_beta(ediff, hg, ag, hlg, alg, x0)
    print(f"  point fit: log_base={point[0]:.4f} beta={point[1]:.4f} rho={point[2]:.4f}")

    # Production beta is temperature-corrected: beta_prod = original_MLE_beta * temperature_mul.
    # The raw bootstrap fits the MLE scale (~original_beta_elo); transfer its uncertainty onto
    # the production scale by the same temperature_mul so intervals sit around the real forecast.
    base_params = load_calibrated_params()
    temp_mul = float(base_params.get("temperature_mul", base_params["beta_elo"] / point[1]))
    print(f"  temperature_mul={temp_mul:.4f} (production beta {base_params['beta_elo']} = raw {point[1]:.4f} x {temp_mul})")

    print(f"Bootstrapping beta ({b} resamples) ...")
    rng = np.random.default_rng(seed)
    betas_raw = np.empty(b)
    for i in range(b):
        idx = rng.integers(0, n, n)
        xi = fit_beta(ediff[idx], hg[idx], ag[idx], hlg[idx], alg[idx], point)
        betas_raw[i] = xi[1]
    betas = betas_raw * temp_mul  # production scale
    beta_p5, beta_p50, beta_p95 = np.percentile(betas, [5, 50, 95])
    beta_se = float(betas.std(ddof=1))
    print(f"  production-scale beta P5={beta_p5:.4f} P50={beta_p50:.4f} P95={beta_p95:.4f} SE={beta_se:.4f}")

    # Propagate to champion probabilities at the 3 bands (production model = ML@config)
    base_params = load_calibrated_params()
    cfg = load_config(); teams = load_teams(apply_temporal_form=True); groups = load_groups()

    def champ_probs(beta_val):
        p = deepcopy(base_params); p["beta_elo"] = float(beta_val)
        model = CalibratedEloMatchModel(config=cfg, params=p, use_ml=None)  # production config
        sim = TournamentSimulator(teams=teams, groups=groups, model=model)
        s = sim.simulate_many(iterations=n_sim, seed=seed).summary
        return {r.team: r.champion_prob for r in s.itertuples()}

    print(f"Running {n_sim:,} sims at each beta band ...")
    plo = champ_probs(beta_p5); pbase = champ_probs(beta_p50); phi = champ_probs(beta_p95)

    teams_all = set(plo) | set(pbase) | set(phi)
    rows = []
    for t in teams_all:
        a_, b_, c_ = plo.get(t, 0.0), pbase.get(t, 0.0), phi.get(t, 0.0)
        # Band spans all three beta scenarios incl. base, so low <= base <= high by
        # construction (for narrow bands MC noise can otherwise put base outside [lo,hi]).
        lo, hi = min(a_, b_, c_), max(a_, b_, c_)
        rows.append({"team": t, "p_low": round(lo, 4), "p_base": round(b_, 4),
                     "p_high": round(hi, 4), "interval_width_pp": round((hi - lo) * 100, 3)})
    df = pd.DataFrame(rows).sort_values("p_base", ascending=False).reset_index(drop=True)
    df.to_csv(ROOT / "outputs" / "audit" / "champion_probability_intervals.csv", index=False)

    intervals = {r["team"]: {"low": r["p_low"], "base": r["p_base"], "high": r["p_high"]}
                 for r in df.head(24).to_dict("records")}
    (ROOT / "data" / "live" / "champion_probability_intervals.json").write_text(json.dumps({
        "generated_at": NOW,
        "method": "beta_elo bootstrap (P5/P50/P95) propagated through production model",
        "beta": {"p5": round(beta_p5, 4), "p50": round(beta_p50, 4), "p95": round(beta_p95, 4), "se": round(beta_se, 4)},
        "intervals": intervals,
    }, indent=2))

    boot = {
        "generated_at": NOW, "n_matches": n, "n_bootstrap": b, "n_sim_per_band": n_sim,
        "point_fit": {"log_base": round(point[0], 6), "beta_elo": round(point[1], 6), "rho": round(point[2], 6)},
        "production_beta": base_params["beta_elo"],
        "beta_bootstrap": {"p5": round(beta_p5, 5), "p50": round(beta_p50, 5),
                            "p95": round(beta_p95, 5), "se": round(beta_se, 5),
                            "ci90_width": round(beta_p95 - beta_p5, 5)},
        "top_intervals": df.head(12).to_dict("records"),
        "honest_caveats": [
            "SAMPLING uncertainty on beta is SMALL (10.5k matches pin it well) — narrow intervals. This is NOT the same as the +/-25% sensitivity STRESS TEST (which moved ESP ~8pp); that stress test asks 'what if beta were badly wrong', not 'what does the data support'.",
            "iid match bootstrap ignores cross-match dependence -> LOWER bound on parameter uncertainty.",
            "These bands capture beta SAMPLING error only. They EXCLUDE the dominant uncertainties: temperature_mul calibration choice (0.55, not bootstrapped), structural/model error, and small-tournament variance. Treat as a floor on true forecast uncertainty.",
            "Monte Carlo noise (~0.1pp) is separate and additional. Intervals are on the unconditioned pre-tournament forecast.",
        ],
    }
    (ROOT / "outputs" / "audit" / "beta_uncertainty_bootstrap.json").write_text(json.dumps(boot, indent=2))
    lines = ["# beta_elo Uncertainty Bootstrap -> Champion Intervals", "",
             f"Generated {NOW[:19]} · {n:,} matches · B={b} bootstrap · N={n_sim:,}/band", "",
             f"## Bootstrap beta_elo (iid match resample)",
             f"- point fit: **{point[1]:.4f}** (production uses {base_params['beta_elo']})",
             f"- P5 / P50 / P95: **{beta_p5:.4f} / {beta_p50:.4f} / {beta_p95:.4f}**  ·  SE {beta_se:.4f}  ·  90% CI width {beta_p95-beta_p5:.4f}", "",
             "## Champion probability intervals (top 12)", "",
             "| Team | low (P5) | base (P50) | high (P95) | width pp |", "|---|---|---|---|---|"]
    for r in df.head(12).itertuples():
        lines.append(f"| {r.team} | {r.p_low*100:.2f}% | {r.p_base*100:.2f}% | {r.p_high*100:.2f}% | {r.interval_width_pp} |")
    lines += ["", "## Honest caveats", ""] + [f"- {c}" for c in boot["honest_caveats"]]
    (ROOT / "outputs" / "audit" / "beta_uncertainty_bootstrap.md").write_text("\n".join(lines))

    print(f"\nDone in {time.monotonic()-t0:.0f}s")
    print("Top 6 champion intervals:")
    for r in df.head(6).itertuples():
        print(f"  {r.team:4s} {r.p_low*100:5.2f}% .. {r.p_base*100:5.2f}% .. {r.p_high*100:5.2f}%  (±{r.interval_width_pp:.1f}pp)")
    return boot


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--b", type=int, default=B)
    ap.add_argument("--n", type=int, default=N_SIM)
    args = ap.parse_args()
    main(b=args.b, n_sim=args.n)
