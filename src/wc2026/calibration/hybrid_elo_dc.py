"""
Hybrid Elo–Dixon-Coles model.

Model:
  log_mu_home = log_base + beta_elo * elo_diff_scaled + atk_res[home] - def_res[away]
  log_mu_away = log_base - beta_elo * elo_diff_scaled + atk_res[away] - def_res[home]

Where:
  elo_diff_scaled = (elo_home_pre_match - elo_away_pre_match) / 400
  atk_res[t]     = residual attack beyond what Elo already explains (shrunk by L2)
  def_res[t]     = residual defense (same)

Elo is the backbone: beta_elo is expected to be ~0.25–0.50.
Residuals handle team-specific over/under-performance vs. Elo.

Dixon-Coles τ correction applied to low-scoring cells (0-0, 1-0, 0-1, 1-1).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .rolling_elo import RollingEloEngine


@dataclass
class HybridParams:
    log_base: float               # baseline log expected goals
    beta_elo: float               # coefficient on scaled Elo diff
    rho: float                    # Dixon-Coles correction
    attack_res: dict[str, float]  # residual attack per team (mean-zero)
    defense_res: dict[str, float] # residual defense per team
    # Metadata
    n_teams: int = 0
    n_params: int = 0
    n_train_matches: int = 0
    converged: bool = False
    final_nll: float = float("inf")
    n_iterations: int = 0
    message: str = ""
    regularization_lambda: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.n_teams = len(self.attack_res)
        self.n_params = 3 + 2 * self.n_teams  # log_base, beta_elo, rho, attacks, defenses

    @property
    def base_xg(self) -> float:
        return math.exp(self.log_base)

    def expected_goals(
        self, home_team: str, away_team: str,
        elo_home: float, elo_away: float,
    ) -> tuple[float, float]:
        elo_diff_scaled = (elo_home - elo_away) / 400.0
        a_h = self.attack_res.get(home_team, 0.0)
        d_h = self.defense_res.get(home_team, 0.0)
        a_a = self.attack_res.get(away_team, 0.0)
        d_a = self.defense_res.get(away_team, 0.0)
        log_mu_h = self.log_base + self.beta_elo * elo_diff_scaled + a_h - d_a
        log_mu_a = self.log_base - self.beta_elo * elo_diff_scaled + a_a - d_h
        mu_h = min(max(math.exp(log_mu_h), 0.05), 8.0)
        mu_a = min(max(math.exp(log_mu_a), 0.05), 8.0)
        return mu_h, mu_a

    def prob_1x2(
        self, home_team: str, away_team: str,
        elo_home: float, elo_away: float,
        max_goals: int = 8,
    ) -> tuple[float, float, float]:
        mu_h, mu_a = self.expected_goals(home_team, away_team, elo_home, elo_away)
        rho = self.rho

        def tau(i, j):
            if i == 0 and j == 0: return max(1.0 - mu_h * mu_a * rho, 1e-9)
            if i == 1 and j == 0: return max(1.0 + mu_a * rho, 1e-9)
            if i == 0 and j == 1: return max(1.0 + mu_h * rho, 1e-9)
            if i == 1 and j == 1: return max(1.0 - rho, 1e-9)
            return 1.0

        def pmf(k, mu):
            return math.exp(-mu + k * math.log(max(mu, 1e-12)) - math.lgamma(k + 1))

        ph = pd_ = pa = 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                p = pmf(i, mu_h) * pmf(j, mu_a) * tau(i, j)
                if i > j: ph += p
                elif i == j: pd_ += p
                else: pa += p
        total = ph + pd_ + pa
        if total < 1e-12:
            return (1/3, 1/3, 1/3)
        return ph / total, pd_ / total, pa / total

    def to_dict(self) -> dict:
        d = {
            "log_base": round(self.log_base, 6),
            "base_xg": round(self.base_xg, 5),
            "beta_elo": round(self.beta_elo, 6),
            "rho": round(self.rho, 6),
            "n_teams": self.n_teams,
            "n_params": self.n_params,
            "n_train_matches": self.n_train_matches,
            "converged": self.converged,
            "final_nll": round(self.final_nll, 6),
            "n_iterations": self.n_iterations,
            "message": self.message,
            "regularization_lambda": self.regularization_lambda,
            "warnings": self.warnings,
            "team_attack_res": {k: round(v, 6) for k, v in sorted(self.attack_res.items())},
            "team_defense_res": {k: round(v, 6) for k, v in sorted(self.defense_res.items())},
        }
        return d

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))


def _dc_ll_single(hg: int, ag: int, mu_h: float, mu_a: float, rho: float) -> float:
    ll = (
        -mu_h + hg * math.log(max(mu_h, 1e-12)) - math.lgamma(hg + 1)
        - mu_a + ag * math.log(max(mu_a, 1e-12)) - math.lgamma(ag + 1)
    )
    g = (hg, ag)
    if g == (0, 0): tau = max(1.0 - mu_h * mu_a * rho, 1e-9)
    elif g == (1, 0): tau = max(1.0 + mu_a * rho, 1e-9)
    elif g == (0, 1): tau = max(1.0 + mu_h * rho, 1e-9)
    elif g == (1, 1): tau = max(1.0 - rho, 1e-9)
    else: tau = 1.0
    return ll + math.log(tau)


def fit_hybrid(
    train_df: pd.DataFrame,
    elo_engine: RollingEloEngine,
    all_teams: Optional[list[str]] = None,
    regularization_lambda: float = 0.05,
    rho_bounds: tuple[float, float] = (-0.20, 0.20),
    beta_elo_bounds: tuple[float, float] = (0.0, 2.0),
    n_restarts: int = 3,
    max_iter: int = 3000,
    verbose: bool = True,
) -> HybridParams:
    """
    Fit hybrid Elo-DC model on training data.

    train_df must have: date, home_team, away_team, home_goals, away_goals, weight.
    elo_engine must be fitted ONLY on data strictly before the first test date
    (no leakage).
    """
    if all_teams is None:
        all_teams = sorted(set(train_df["home_team"]) | set(train_df["away_team"]))
    n = len(all_teams)
    team_idx = {t: i for i, t in enumerate(all_teams)}

    # Extract arrays once (avoid iterrows in hot path)
    home_teams = train_df["home_team"].tolist()
    away_teams = train_df["away_team"].tolist()
    dates_list = train_df["date"].tolist()
    neutrals = train_df["neutral"].tolist()
    h_goals_list = train_df["home_goals"].tolist()
    a_goals_list = train_df["away_goals"].tolist()
    weights_list = train_df["weight"].tolist()

    # Pre-compute pre-match Elo diffs
    elo_diffs = np.array([
        (elo_engine.get_elo(h, before_date=d) + (0.0 if n else 100.0)
         - elo_engine.get_elo(a, before_date=d)) / 400.0
        for h, a, d, n in zip(home_teams, away_teams, dates_list, neutrals)
    ])

    h_idx = np.array([team_idx.get(t, 0) for t in home_teams])
    a_idx = np.array([team_idx.get(t, 0) for t in away_teams])
    h_goals = np.array([int(g) for g in h_goals_list])
    a_goals = np.array([int(g) for g in a_goals_list])
    weights = np.array([float(w) for w in weights_list])
    # Pre-compute lgamma(g+1) for all matches (constant per match)
    h_lgamma = np.array([math.lgamma(int(g) + 1) for g in h_goals])
    a_lgamma = np.array([math.lgamma(int(g) + 1) for g in a_goals])

    # Layout: [log_base, beta_elo, rho, atk_0..atk_{n-1}, def_0..def_{n-1}]
    def unpack(x):
        return x[0], x[1], x[2], x[3:3+n], x[3+n:]

    def objective(x):
        log_base, beta_elo, rho, atk, dfs = unpack(x)
        # Vectorised log-mu computation
        log_mu_h = log_base + beta_elo * elo_diffs + atk[h_idx] - dfs[a_idx]
        log_mu_a = log_base - beta_elo * elo_diffs + atk[a_idx] - dfs[h_idx]
        mu_h = np.clip(np.exp(log_mu_h), 0.05, 8.0)
        mu_a = np.clip(np.exp(log_mu_a), 0.05, 8.0)

        # Vectorised Poisson log-likelihood (no DC correction — then correct below)
        # log P(G_h=g | mu_h) = -mu_h + g*log(mu_h) - lgamma(g+1)
        ll_h = -mu_h + h_goals * np.log(mu_h) - h_lgamma
        ll_a = -mu_a + a_goals * np.log(mu_a) - a_lgamma
        ll = ll_h + ll_a

        # Dixon-Coles τ correction for low-scoring cells (scalar loop over ≤4 cases)
        # Applied only to matches with goals in {0,1} for both teams
        low = (h_goals <= 1) & (a_goals <= 1)
        if low.any():
            mu_hL = mu_h[low]; mu_aL = mu_a[low]
            hgL = h_goals[low]; agL = a_goals[low]
            tau = np.ones(low.sum())
            m00 = (hgL == 0) & (agL == 0)
            m10 = (hgL == 1) & (agL == 0)
            m01 = (hgL == 0) & (agL == 1)
            m11 = (hgL == 1) & (agL == 1)
            tau[m00] = np.maximum(1.0 - mu_hL[m00] * mu_aL[m00] * rho, 1e-9)
            tau[m10] = np.maximum(1.0 + mu_aL[m10] * rho, 1e-9)
            tau[m01] = np.maximum(1.0 + mu_hL[m01] * rho, 1e-9)
            tau[m11] = np.maximum(1.0 - rho, 1e-9)
            ll[low] += np.log(tau)

        # Clamp -inf values
        ll = np.where(np.isfinite(ll), ll, -30.0)
        nll = -np.dot(weights, ll)
        reg = regularization_lambda * (np.sum(atk**2) + np.sum(dfs**2))
        ident = 100.0 * np.sum(atk)**2
        return float(nll + reg + ident)

    bounds = (
        [(-2.0, 1.5)]                # log_base
        + [list(beta_elo_bounds)]    # beta_elo
        + [list(rho_bounds)]         # rho
        + [(-2.5, 2.5)] * n          # attack residuals
        + [(-2.5, 2.5)] * n          # defense residuals
    )

    mean_goals = (train_df["home_goals"].mean() + train_df["away_goals"].mean()) / 2
    rng = np.random.default_rng(20260609)
    best_result = None
    best_nll = float("inf")

    for restart in range(n_restarts):
        if restart == 0:
            x0 = np.zeros(3 + 2 * n)
            x0[0] = math.log(max(mean_goals, 0.5))
            x0[1] = 0.30   # beta_elo warm start
            x0[2] = -0.05  # rho
        else:
            x0 = rng.normal(0, 0.2, 3 + 2 * n)
            x0[0] = math.log(max(mean_goals, 0.5)) + rng.normal(0, 0.15)
            x0[1] = max(0.05, rng.uniform(*beta_elo_bounds) * 0.5)
            x0[2] = rng.uniform(*rho_bounds)
        try:
            res = minimize(
                objective, x0, method="L-BFGS-B", bounds=bounds,
                options={"maxiter": max_iter, "ftol": 1e-10, "gtol": 1e-7},
            )
            val = float(res.fun)
            if math.isfinite(val) and val < best_nll:
                best_nll = val
                best_result = res
                if verbose:
                    print(f"  restart {restart+1}/{n_restarts}: NLL={val:.4f} {'✓' if res.success else '~'}")
        except Exception as e:
            if verbose:
                print(f"  restart {restart+1} failed: {e}")

    warns = []
    if best_result is None:
        warns.append("CRITICAL: all restarts failed")
        return HybridParams(
            log_base=math.log(max(mean_goals, 0.5)),
            beta_elo=0.3, rho=-0.05,
            attack_res={t: 0.0 for t in all_teams},
            defense_res={t: 0.0 for t in all_teams},
            converged=False, final_nll=float("inf"),
            message="all restarts failed", warnings=warns,
        )

    log_base, beta_elo, rho, atk_arr, dfs_arr = unpack(best_result.x)
    # Enforce identifiability
    mean_atk = float(np.mean(atk_arr))
    atk_arr -= mean_atk
    log_base += mean_atk

    if not best_result.success:
        warns.append(f"WARNING: optimizer did not converge — {best_result.message}")
    if abs(rho - float(np.clip(rho, *rho_bounds))) > 1e-5:
        warns.append(f"WARNING: rho hit boundary ({rho:.4f})")
    rho = float(np.clip(rho, *rho_bounds))

    # Per-match NLL without regularization (vectorised)
    lmh = log_base + beta_elo * elo_diffs + atk_arr[h_idx] - dfs_arr[a_idx]
    lma = log_base - beta_elo * elo_diffs + atk_arr[a_idx] - dfs_arr[h_idx]
    mh = np.clip(np.exp(lmh), 0.05, 8.0)
    ma = np.clip(np.exp(lma), 0.05, 8.0)
    ll_v = -mh + h_goals * np.log(mh) - h_lgamma - ma + a_goals * np.log(ma) - a_lgamma
    low = (h_goals <= 1) & (a_goals <= 1)
    if low.any():
        mhL, maL, hgL, agL = mh[low], ma[low], h_goals[low], a_goals[low]
        tau = np.ones(low.sum())
        tau[(hgL==0)&(agL==0)] = np.maximum(1.0 - mhL[(hgL==0)&(agL==0)]*maL[(hgL==0)&(agL==0)]*rho, 1e-9)
        tau[(hgL==1)&(agL==0)] = np.maximum(1.0 + maL[(hgL==1)&(agL==0)]*rho, 1e-9)
        tau[(hgL==0)&(agL==1)] = np.maximum(1.0 + mhL[(hgL==0)&(agL==1)]*rho, 1e-9)
        tau[(hgL==1)&(agL==1)] = np.maximum(1.0 - rho, 1e-9)
        ll_v[low] += np.log(tau)
    ll_v = np.where(np.isfinite(ll_v), ll_v, -30.0)
    per_match_nll = float(-np.mean(ll_v))

    return HybridParams(
        log_base=float(log_base),
        beta_elo=float(beta_elo),
        rho=rho,
        attack_res={t: float(atk_arr[i]) for i, t in enumerate(all_teams)},
        defense_res={t: float(dfs_arr[i]) for i, t in enumerate(all_teams)},
        n_train_matches=len(train_df),
        converged=bool(best_result.success),
        final_nll=round(per_match_nll, 6),
        n_iterations=int(best_result.nit),
        message=str(best_result.message),
        regularization_lambda=regularization_lambda,
        warnings=warns,
    )


def evaluate_hybrid_on_dataset(
    df: pd.DataFrame,
    params: HybridParams,
    elo_engine: RollingEloEngine,
) -> dict:
    """Evaluate hybrid model on a DataFrame using pre-match Elo lookup."""
    from .metrics import (
        negative_log_likelihood, brier_score_1x2, accuracy_1x2,
        calibration_error, outcome_from_goals,
    )
    probs, outcomes = [], []
    for _, row in df.iterrows():
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        p = params.prob_1x2(row["home_team"], row["away_team"], elo_h + adj, elo_a)
        probs.append(p)
        outcomes.append(outcome_from_goals(int(row["home_goals"]), int(row["away_goals"])))
    return {
        "nll": round(negative_log_likelihood(probs, outcomes), 5),
        "brier": round(brier_score_1x2(probs, outcomes), 5),
        "accuracy": round(accuracy_1x2(probs, outcomes), 4),
        "ece": round(calibration_error(probs, outcomes), 5),
        "n_matches": len(outcomes),
    }


def build_elo_only_prob_fn(elo_engine: RollingEloEngine, draw_bias: float = 0.25):
    """Elo-only baseline using pre-match Elo diff."""
    from .metrics import elo_baseline_probs
    def fn(row):
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        return elo_baseline_probs(row["home_team"], row["away_team"],
                                   {row["home_team"]: elo_h + adj, row["away_team"]: elo_a},
                                   draw_bias=draw_bias)
    return fn
