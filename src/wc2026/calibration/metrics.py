"""
Evaluation metrics for WC match model comparison.

All metrics operate on match-level 1X2 probabilities.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd


def negative_log_likelihood(
    probs: Sequence[tuple[float, float, float]],  # (p_home, p_draw, p_away)
    outcomes: Sequence[int],                       # 0=home, 1=draw, 2=away
) -> float:
    """Mean NLL per match. Lower is better. Perfect = 0, random ≈ log(3) ≈ 1.099."""
    total = 0.0
    for (ph, pd_, pa), o in zip(probs, outcomes):
        p = [ph, pd_, pa][o]
        total -= math.log(max(p, 1e-12))
    return total / max(len(outcomes), 1)


def brier_score_1x2(
    probs: Sequence[tuple[float, float, float]],
    outcomes: Sequence[int],
) -> float:
    """Multiclass Brier score. Range [0, 2]. Random = 2/3 ≈ 0.667."""
    total = 0.0
    for (ph, pd_, pa), o in zip(probs, outcomes):
        one_hot = [0.0, 0.0, 0.0]
        one_hot[o] = 1.0
        for i, p in enumerate([ph, pd_, pa]):
            total += (p - one_hot[i]) ** 2
    return total / max(len(outcomes), 1)


def log_loss_binary(
    p_events: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    """Binary log loss for a single event (e.g. group survival). Random = log(2) ≈ 0.693."""
    total = 0.0
    for p, o in zip(p_events, outcomes):
        p = max(min(p, 1 - 1e-12), 1e-12)
        total -= o * math.log(p) + (1 - o) * math.log(1 - p)
    return total / max(len(outcomes), 1)


def accuracy_1x2(
    probs: Sequence[tuple[float, float, float]],
    outcomes: Sequence[int],
) -> float:
    """Fraction of matches where the mode prediction is correct."""
    correct = sum(
        1 for (ph, pd_, pa), o in zip(probs, outcomes)
        if [ph, pd_, pa].index(max(ph, pd_, pa)) == o
    )
    return correct / max(len(outcomes), 1)


def calibration_error(
    probs: Sequence[tuple[float, float, float]],
    outcomes: Sequence[int],
    n_bins: int = 5,
) -> float:
    """
    Expected calibration error (ECE) across home/draw/away outcomes.
    Bins predicted probabilities and measures |mean_pred - freq_actual| per bin.
    Returns weighted mean absolute calibration error.
    """
    flat_probs, flat_outcomes = [], []
    for (ph, pd_, pa), o in zip(probs, outcomes):
        for i, p in enumerate([ph, pd_, pa]):
            flat_probs.append(p)
            flat_outcomes.append(1 if o == i else 0)

    flat_probs = np.array(flat_probs)
    flat_outcomes = np.array(flat_outcomes, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(flat_probs)

    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (flat_probs >= lo) & (flat_probs < hi)
        if not mask.any():
            continue
        n = mask.sum()
        mean_pred = flat_probs[mask].mean()
        freq_act = flat_outcomes[mask].mean()
        ece += (n / total) * abs(mean_pred - freq_act)

    return float(ece)


def outcome_from_goals(home_goals: int, away_goals: int) -> int:
    """0=home win, 1=draw, 2=away win."""
    if home_goals > away_goals:
        return 0
    elif home_goals == away_goals:
        return 1
    else:
        return 2


def evaluate_model_on_dataset(
    df: pd.DataFrame,
    prob_fn,  # callable(home_code, away_code) -> (p_home, p_draw, p_away)
) -> dict[str, float]:
    """
    Evaluate a probability function on a match dataset.
    Returns dict of NLL, Brier, accuracy, ECE.
    """
    probs, outcomes = [], []
    for _, row in df.iterrows():
        try:
            p = prob_fn(row["home_code"], row["away_code"])
            p = tuple(float(x) for x in p)
            s = sum(p)
            p = tuple(x / s for x in p)  # renormalize
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


# Baseline functions
def random_baseline_probs(home_code: str, away_code: str) -> tuple[float, float, float]:
    """Uniform 1/3 each outcome."""
    return (1/3, 1/3, 1/3)


def elo_baseline_probs(
    home_code: str,
    away_code: str,
    elo_map: dict[str, float],
    draw_bias: float = 0.10,
) -> tuple[float, float, float]:
    """
    Elo-based 1X2 probability using standard Elo win probability formula.
    Draw probability modeled as uniform draw_bias split from win probability.
    draw_bias=0.10 → add 10% mass to draw, redistribute from H/A proportionally.
    """
    elo_h = elo_map.get(home_code, 1500.0)
    elo_a = elo_map.get(away_code, 1500.0)
    delta = (elo_h - elo_a) / 400.0
    p_home_win = 1.0 / (1.0 + 10 ** (-delta))
    p_away_win = 1.0 - p_home_win
    p_draw = draw_bias
    p_home_win = p_home_win * (1.0 - draw_bias)
    p_away_win = p_away_win * (1.0 - draw_bias)
    return (p_home_win, p_draw, p_away_win)


def indep_poisson_probs(
    mu_home: float,
    mu_away: float,
    max_goals: int = 8,
) -> tuple[float, float, float]:
    """
    Independent (non-DC) Poisson 1X2 probabilities.
    mu_home, mu_away: expected goals.
    """
    from math import exp, factorial
    def pmf(k, mu):
        return exp(-mu) * mu**k / factorial(k)

    p_home = p_draw = p_away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = pmf(i, mu_home) * pmf(j, mu_away)
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    return (p_home, p_draw, p_away)
