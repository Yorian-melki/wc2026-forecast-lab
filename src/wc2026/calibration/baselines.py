"""
Extended baseline models for hybrid model comparison.
All baselines take a row (from DataFrame) and return (p_home, p_draw, p_away).
"""
from __future__ import annotations

import math
from typing import Callable

import pandas as pd

from .metrics import (
    negative_log_likelihood, brier_score_1x2, accuracy_1x2,
    calibration_error, outcome_from_goals,
)
from .rolling_elo import RollingEloEngine


def _elo_win_prob(elo_diff: float) -> float:
    """Probability of home team winning given Elo diff (home - away + home_adv)."""
    return 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))


def random_fn(row) -> tuple[float, float, float]:
    return (1/3, 1/3, 1/3)


def empirical_freq_fn(df_train: pd.DataFrame) -> Callable:
    """1X2 frequency baseline: p(outcome) = fraction of train outcomes."""
    total = len(df_train)
    p_home = ((df_train["home_goals"] > df_train["away_goals"]).sum()) / total
    p_draw = ((df_train["home_goals"] == df_train["away_goals"]).sum()) / total
    p_away = ((df_train["home_goals"] < df_train["away_goals"]).sum()) / total
    def fn(row): return (p_home, p_draw, p_away)
    return fn


def elo_simple_fn(elo_engine: RollingEloEngine, draw_bias: float = 0.22) -> Callable:
    """
    Elo-only 1X2: map Elo win probability to 1X2 using a draw probability model.
    draw_bias=0.22 → 22% draw probability, rest split proportionally.
    """
    def fn(row):
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        p_win = _elo_win_prob(elo_h + adj - elo_a)
        p_lose = 1.0 - p_win
        p_draw = draw_bias
        p_win *= (1.0 - draw_bias)
        p_lose *= (1.0 - draw_bias)
        return (p_win, p_draw, p_lose)
    return fn


def elo_draw_calibrated_fn(elo_engine: RollingEloEngine, df_train: pd.DataFrame) -> Callable:
    """
    Elo-only with draw probability modeled as a function of |Elo diff|.
    Calibrate the draw probability correction from training data.
    """
    import numpy as np
    from scipy.optimize import minimize_scalar

    # Compute draw rate as a function of elo diff bins
    elo_diffs, outcomes = [], []
    for _, row in df_train.iterrows():
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        elo_diffs.append(abs(elo_h + adj - elo_a))
        outcomes.append(outcome_from_goals(int(row["home_goals"]), int(row["away_goals"])))

    elo_diffs = np.array(elo_diffs)
    is_draw = np.array([o == 1 for o in outcomes], dtype=float)

    # Fit: draw_rate = a * exp(-b * |elo_diff| / 400)
    def neg_ll(params):
        a, b = max(params[0], 0.01), max(params[1], 0.0)
        total = 0.0
        for i in range(len(elo_diffs)):
            pd_ = max(min(a * math.exp(-b * elo_diffs[i] / 400.0), 0.99), 0.01)
            total -= is_draw[i] * math.log(pd_) + (1 - is_draw[i]) * math.log(1 - pd_)
        return total

    try:
        from scipy.optimize import minimize as sp_min
        res = sp_min(neg_ll, [0.25, 0.5], method="Nelder-Mead",
                     options={"maxiter": 500, "xatol": 1e-6})
        a_opt, b_opt = max(res.x[0], 0.01), max(res.x[1], 0.0)
    except Exception:
        a_opt, b_opt = 0.25, 0.3

    def fn(row):
        elo_h = elo_engine.get_elo(row["home_team"], before_date=row["date"])
        elo_a = elo_engine.get_elo(row["away_team"], before_date=row["date"])
        adj = 0.0 if row["neutral"] else 100.0
        diff = elo_h + adj - elo_a
        abs_diff = abs(diff)
        p_win = _elo_win_prob(diff)
        p_draw = max(min(a_opt * math.exp(-b_opt * abs_diff / 400.0), 0.60), 0.05)
        p_win_adj = p_win * (1.0 - p_draw)
        p_lose_adj = (1.0 - p_win) * (1.0 - p_draw)
        total = p_win_adj + p_draw + p_lose_adj
        return (p_win_adj / total, p_draw / total, p_lose_adj / total)
    return fn


def evaluate_row_model(
    df: pd.DataFrame,
    prob_fn: Callable,  # fn(row) -> (ph, pd, pa)
) -> dict:
    probs, outcomes = [], []
    for _, row in df.iterrows():
        try:
            p = prob_fn(row)
            s = sum(p)
            p = tuple(x / max(s, 1e-12) for x in p)
        except Exception:
            p = (1/3, 1/3, 1/3)
        probs.append(p)
        outcomes.append(outcome_from_goals(int(row["home_goals"]), int(row["away_goals"])))
    return {
        "nll": round(negative_log_likelihood(probs, outcomes), 5),
        "brier": round(brier_score_1x2(probs, outcomes), 5),
        "accuracy": round(accuracy_1x2(probs, outcomes), 4),
        "ece": round(calibration_error(probs, outcomes), 5),
        "n_matches": len(outcomes),
    }
