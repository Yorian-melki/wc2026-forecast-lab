"""
Dixon-Coles bivariate Poisson MLE calibration.

Model:
  mu_home = exp(log_base + attack[home] - defense[away])
  mu_away = exp(log_base + attack[away] - defense[home])

Dixon-Coles τ correction for low-scoring cells:
  τ(0,0) = 1 - mu_h * mu_a * rho
  τ(1,0) = 1 + mu_a * rho
  τ(0,1) = 1 + mu_h * rho
  τ(1,1) = 1 - rho

Identifiability: sum(attack) = 0 enforced via penalty (soft constraint).
L2 regularization on attack and defense parameters to handle sparse data.

EXPERIMENTAL — train=WC2018 (64 matches), holdout=WC2022 (64 matches).
~3.2 matches per team. Do NOT use in production without holdout improvement proof.
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize, OptimizeResult

warnings.filterwarnings("ignore")


@dataclass
class DCParams:
    log_base_xg: float          # log of baseline expected goals per team per match
    attack: dict[str, float]    # team_code → attack parameter (mean-zero)
    defense: dict[str, float]   # team_code → defense parameter
    rho: float                  # Dixon-Coles correction [-0.20, 0.20]
    # Derived
    base_xg: float = 0.0        # exp(log_base_xg)
    n_teams: int = 0
    n_params: int = 0
    # Optimization metadata
    converged: bool = False
    final_nll: float = float("inf")
    n_iterations: int = 0
    message: str = ""
    regularization_lambda: float = 0.0
    warnings: list[str] = None

    def __post_init__(self):
        self.base_xg = math.exp(self.log_base_xg)
        self.n_teams = len(self.attack)
        self.n_params = 1 + 2 * self.n_teams + 1  # log_base + attacks + defenses + rho
        if self.warnings is None:
            self.warnings = []

    def expected_goals(self, home_code: str, away_code: str) -> tuple[float, float]:
        a_h = self.attack.get(home_code, 0.0)
        d_h = self.defense.get(home_code, 0.0)
        a_a = self.attack.get(away_code, 0.0)
        d_a = self.defense.get(away_code, 0.0)
        mu_h = math.exp(self.log_base_xg + a_h - d_a)
        mu_a = math.exp(self.log_base_xg + a_a - d_h)
        mu_h = min(max(mu_h, 0.05), 6.0)
        mu_a = min(max(mu_a, 0.05), 6.0)
        return mu_h, mu_a

    def prob_1x2(self, home_code: str, away_code: str, max_goals: int = 8) -> tuple[float, float, float]:
        mu_h, mu_a = self.expected_goals(home_code, away_code)
        rho = self.rho

        def tau(i, j):
            if i == 0 and j == 0:
                return max(1.0 - mu_h * mu_a * rho, 1e-9)
            elif i == 1 and j == 0:
                return max(1.0 + mu_a * rho, 1e-9)
            elif i == 0 and j == 1:
                return max(1.0 + mu_h * rho, 1e-9)
            elif i == 1 and j == 1:
                return max(1.0 - rho, 1e-9)
            return 1.0

        def poisson_pmf(k, mu):
            return math.exp(-mu + k * math.log(max(mu, 1e-12)) - math.lgamma(k + 1))

        p_home = p_draw = p_away = 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                p = poisson_pmf(i, mu_h) * poisson_pmf(j, mu_a) * tau(i, j)
                if i > j:
                    p_home += p
                elif i == j:
                    p_draw += p
                else:
                    p_away += p

        total = p_home + p_draw + p_away
        if total < 1e-12:
            return (1/3, 1/3, 1/3)
        return (p_home / total, p_draw / total, p_away / total)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["base_xg"] = round(self.base_xg, 5)
        d["log_base_xg"] = round(self.log_base_xg, 6)
        d["rho"] = round(self.rho, 6)
        d["attack"] = {k: round(v, 6) for k, v in sorted(self.attack.items())}
        d["defense"] = {k: round(v, 6) for k, v in sorted(self.defense.items())}
        d["final_nll"] = round(self.final_nll, 6)
        return d

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "DCParams":
        d = json.loads(path.read_text())
        obj = cls(
            log_base_xg=d["log_base_xg"],
            attack=d["attack"],
            defense=d["defense"],
            rho=d["rho"],
            converged=d.get("converged", False),
            final_nll=d.get("final_nll", float("inf")),
            n_iterations=d.get("n_iterations", 0),
            message=d.get("message", ""),
            regularization_lambda=d.get("regularization_lambda", 0.0),
            warnings=d.get("warnings", []),
        )
        return obj


def _dc_log_likelihood_single(
    home_goals: int,
    away_goals: int,
    mu_h: float,
    mu_a: float,
    rho: float,
) -> float:
    """Log likelihood for one match under Dixon-Coles model."""
    log_p = (
        -mu_h + home_goals * math.log(max(mu_h, 1e-12)) - math.lgamma(home_goals + 1)
        - mu_a + away_goals * math.log(max(mu_a, 1e-12)) - math.lgamma(away_goals + 1)
    )
    # DC correction τ
    g = (home_goals, away_goals)
    if g == (0, 0):
        tau = 1.0 - mu_h * mu_a * rho
    elif g == (1, 0):
        tau = 1.0 + mu_a * rho
    elif g == (0, 1):
        tau = 1.0 + mu_h * rho
    elif g == (1, 1):
        tau = 1.0 - rho
    else:
        tau = 1.0

    tau = max(tau, 1e-9)
    return log_p + math.log(tau)


def fit_dixon_coles(
    train_df: pd.DataFrame,
    all_teams: list[str],
    regularization_lambda: float = 0.05,
    rho_bounds: tuple[float, float] = (-0.20, 0.20),
    n_restarts: int = 3,
    max_iter: int = 2000,
    verbose: bool = True,
) -> DCParams:
    """
    Fit Dixon-Coles model via negative log-likelihood minimization.

    Parameters
    ----------
    train_df       : DataFrame with home_code, away_code, home_goals, away_goals, weight
    all_teams      : sorted list of FIFA3 codes (defines parameter vector order)
    regularization_lambda : L2 penalty on attack/defense (prevents overfit on sparse data)
    rho_bounds     : bounds for Dixon-Coles rho parameter
    n_restarts     : number of random initializations (keeps best NLL)
    max_iter       : max optimizer iterations per restart

    WARNING: with ~3.2 matches/team, regularization_lambda matters a lot.
    Try lambda in {0.01, 0.05, 0.10} and pick by holdout NLL.
    """
    n = len(all_teams)
    team_idx = {t: i for i, t in enumerate(all_teams)}

    # Extract match data arrays for speed
    h_idx = np.array([team_idx[r["home_code"]] for _, r in train_df.iterrows()])
    a_idx = np.array([team_idx[r["away_code"]] for _, r in train_df.iterrows()])
    h_goals = np.array([int(r["home_goals"]) for _, r in train_df.iterrows()])
    a_goals = np.array([int(r["away_goals"]) for _, r in train_df.iterrows()])
    weights = np.array([float(r["weight"]) for _, r in train_df.iterrows()])

    # Parameter vector layout:
    # [log_base_xg, attack_0..attack_{n-1}, defense_0..defense_{n-1}, rho]
    # Total: 1 + n + n + 1 = 2n+2

    def unpack(x):
        log_base = x[0]
        atk = x[1:n+1]
        dfs = x[n+1:2*n+1]
        rho = x[2*n+1]
        return log_base, atk, dfs, rho

    def objective(x):
        log_base, atk, dfs, rho = unpack(x)
        nll = 0.0
        for k in range(len(h_goals)):
            hi, ai = h_idx[k], a_idx[k]
            mu_h = math.exp(log_base + atk[hi] - dfs[ai])
            mu_a = math.exp(log_base + atk[ai] - dfs[hi])
            mu_h = min(max(mu_h, 0.05), 8.0)
            mu_a = min(max(mu_a, 0.05), 8.0)
            ll = _dc_log_likelihood_single(h_goals[k], a_goals[k], mu_h, mu_a, rho)
            if not math.isfinite(ll):
                ll = -30.0
            nll -= weights[k] * ll
        # L2 regularization (not on log_base or rho)
        reg = regularization_lambda * (np.sum(atk**2) + np.sum(dfs**2))
        # Soft identifiability: penalize deviation of mean(attack) from 0
        ident_penalty = 100.0 * np.sum(atk)**2
        return nll + reg + ident_penalty

    bounds = (
        [(-2.0, 1.0)]        # log_base_xg: exp(-2)=0.14 to exp(1)=2.72
        + [(-3.0, 3.0)] * n  # attack
        + [(-3.0, 3.0)] * n  # defense
        + [list(rho_bounds)]  # rho
    )

    best_result: Optional[OptimizeResult] = None
    best_nll = float("inf")
    rng = np.random.default_rng(20260609)

    for restart in range(n_restarts):
        if restart == 0:
            # Warm start: log_base near global WC average, attack/defense near 0
            mean_goals = (train_df["home_goals"].mean() + train_df["away_goals"].mean()) / 2
            x0 = np.zeros(2 * n + 2)
            x0[0] = math.log(max(mean_goals, 0.5))
            x0[-1] = -0.05  # slightly negative rho (typical for football)
        else:
            x0 = rng.normal(0, 0.3, 2 * n + 2)
            x0[0] = math.log(max(mean_goals, 0.5)) + rng.normal(0, 0.2)
            x0[-1] = rng.uniform(*rho_bounds)

        try:
            result = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": max_iter, "ftol": 1e-10, "gtol": 1e-6},
            )
            val = float(result.fun)
            if math.isfinite(val) and val < best_nll:
                best_nll = val
                best_result = result
                if verbose:
                    print(f"  restart {restart+1}/{n_restarts}: NLL={val:.4f} {'✓' if result.success else '~'}")
        except Exception as e:
            if verbose:
                print(f"  restart {restart+1} failed: {e}")

    warn_list = []
    if best_result is None:
        # Complete failure — return neutral params
        warn_list.append("CRITICAL: all optimizer restarts failed — returning neutral parameters")
        return DCParams(
            log_base_xg=math.log(1.1),
            attack={t: 0.0 for t in all_teams},
            defense={t: 0.0 for t in all_teams},
            rho=-0.05,
            converged=False,
            final_nll=float("inf"),
            message="all restarts failed",
            regularization_lambda=regularization_lambda,
            warnings=warn_list,
        )

    log_base, atk_arr, dfs_arr, rho = unpack(best_result.x)

    # Enforce identifiability: shift attacks so mean=0, compensate in log_base
    mean_atk = float(np.mean(atk_arr))
    atk_arr = atk_arr - mean_atk
    log_base = log_base + mean_atk  # absorb mean attack into baseline

    if regularization_lambda < 0.01:
        warn_list.append(
            f"WARNING: regularization_lambda={regularization_lambda} very small "
            "— overfit risk on 64-match training set"
        )
    if not best_result.success:
        warn_list.append(
            f"WARNING: optimizer did not converge cleanly — {best_result.message}"
        )

    rho_clamped = float(np.clip(rho, *rho_bounds))
    if abs(rho - rho_clamped) > 1e-6:
        warn_list.append(f"WARNING: rho hit boundary ({rho:.4f}) → clamped to {rho_clamped:.4f}")

    # Per-match NLL (normalized, without regularization)
    raw_nll = 0.0
    for k in range(len(h_goals)):
        hi, ai = h_idx[k], a_idx[k]
        mu_h = math.exp(log_base + atk_arr[hi] - dfs_arr[ai])
        mu_a = math.exp(log_base + atk_arr[ai] - dfs_arr[hi])
        mu_h = min(max(mu_h, 0.05), 8.0)
        mu_a = min(max(mu_a, 0.05), 8.0)
        ll = _dc_log_likelihood_single(h_goals[k], a_goals[k], mu_h, mu_a, rho_clamped)
        raw_nll -= float(ll)
    per_match_nll = raw_nll / max(len(h_goals), 1)

    return DCParams(
        log_base_xg=float(log_base),
        attack={t: float(atk_arr[i]) for i, t in enumerate(all_teams)},
        defense={t: float(dfs_arr[i]) for i, t in enumerate(all_teams)},
        rho=rho_clamped,
        converged=bool(best_result.success),
        final_nll=round(per_match_nll, 6),
        n_iterations=int(best_result.nit),
        message=str(best_result.message),
        regularization_lambda=regularization_lambda,
        warnings=warn_list,
    )


def grid_search_lambda(
    train_df: pd.DataFrame,
    holdout_df: pd.DataFrame,
    all_teams: list[str],
    lambdas: list[float] = (0.01, 0.05, 0.10, 0.20),
    n_restarts: int = 2,
    verbose: bool = True,
) -> tuple[float, dict[float, dict]]:
    """
    Simple grid search over regularization_lambda by holdout NLL.
    Returns (best_lambda, {lambda: {train_nll, holdout_nll}}).
    """
    from .metrics import evaluate_model_on_dataset

    results = {}
    best_lambda = lambdas[0]
    best_holdout_nll = float("inf")

    for lam in lambdas:
        if verbose:
            print(f"\n[grid_search] lambda={lam}")
        params = fit_dixon_coles(
            train_df, all_teams,
            regularization_lambda=lam,
            n_restarts=n_restarts,
            verbose=verbose,
        )
        prob_fn = lambda h, a, p=params: p.prob_1x2(h, a)
        train_metrics = evaluate_model_on_dataset(train_df, prob_fn)
        holdout_metrics = evaluate_model_on_dataset(holdout_df, prob_fn)
        results[lam] = {
            "train_nll": train_metrics["nll"],
            "holdout_nll": holdout_metrics["nll"],
            "train_brier": train_metrics["brier"],
            "holdout_brier": holdout_metrics["brier"],
            "converged": params.converged,
            "rho": round(params.rho, 4),
            "base_xg": round(params.base_xg, 4),
        }
        if verbose:
            print(f"  train_nll={train_metrics['nll']:.4f} holdout_nll={holdout_metrics['nll']:.4f}")
        if holdout_metrics["nll"] < best_holdout_nll:
            best_holdout_nll = holdout_metrics["nll"]
            best_lambda = lam

    return best_lambda, results
