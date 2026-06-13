"""
Bookmaker margin removal: convert raw decimal odds to fair (true) probabilities.

Three methods implemented and compared:
  1. basic       — simple normalisation: p_i = (1/o_i) / K
  2. power       — power method: p_i = (1/o_i)^k, solve Σp_i = 1
  3. shin        — Shin (1992) insider-trading model, iterative EM

References:
  Shin (1992) "Prices of State Contingent Claims with Insider Traders"
  Kaunitz et al. (2017) "Beating the bookies with their own numbers"
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

Method = Literal["basic", "power", "shin"]


@dataclass
class FairProbabilities:
    """Margin-adjusted probabilities for a single market."""
    method: Method
    raw_odds: list[float]          # decimal odds as offered by bookmaker
    raw_implied: list[float]       # 1/o_i (includes margin)
    overround: float               # Σ raw_implied (>1 means margin present)
    fair_probs: list[float]        # after margin removal, sum ≈ 1.0
    margin_pct: float              # overround - 1, as percentage

    @property
    def n_outcomes(self) -> int:
        return len(self.raw_odds)

    def fair_prob(self, index: int) -> float:
        return self.fair_probs[index]


def _basic(odds: list[float]) -> FairProbabilities:
    """
    Basic normalisation: divide each implied probability by the overround.
    Assumes bookmaker takes equal margin from each outcome.
    """
    implied = [1.0 / o for o in odds]
    K = sum(implied)
    fair = [p / K for p in implied]
    return FairProbabilities(
        method="basic",
        raw_odds=list(odds),
        raw_implied=implied,
        overround=K,
        fair_probs=fair,
        margin_pct=round((K - 1.0) * 100, 3),
    )


def _power(odds: list[float], tol: float = 1e-10, max_iter: int = 200) -> FairProbabilities:
    """
    Power method (multiplicative): find k such that Σ(1/o_i)^k = 1.
    Better than basic for markets where the bookmaker applies proportionally
    higher margin to underdogs.
    """
    implied = np.array([1.0 / o for o in odds])
    K = float(implied.sum())

    if abs(K - 1.0) < tol:
        return FairProbabilities(
            method="power",
            raw_odds=list(odds),
            raw_implied=implied.tolist(),
            overround=K,
            fair_probs=implied.tolist(),
            margin_pct=0.0,
        )

    # Binary search for k in (0, 3)
    lo, hi = 0.0, 3.0
    for _ in range(max_iter):
        k = (lo + hi) / 2.0
        s = float(np.sum(implied ** k))
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = k
        else:
            hi = k

    fair = (implied ** k).tolist()
    return FairProbabilities(
        method="power",
        raw_odds=list(odds),
        raw_implied=implied.tolist(),
        overround=K,
        fair_probs=fair,
        margin_pct=round((K - 1.0) * 100, 3),
    )


def _shin(odds: list[float], tol: float = 1e-9, max_iter: int = 500) -> FairProbabilities:
    """
    Shin (1992) method: assumes a fraction z of bettors are insiders with
    perfect information. Derives fair probabilities via EM algorithm.

    Model:  implied_i = z + (1-z) * p_i   for each outcome i
    Constraint: Σ p_i = 1

    Closed-form solution (Strumbelj 2014):
      p_i = (sqrt(z² + 4(1-z)r_i/K) - z) / (2(1-z))
    where r_i = 1/o_i and K = Σ r_i, z is solved numerically.
    """
    r = np.array([1.0 / o for o in odds])
    K = float(r.sum())
    n = len(r)

    if abs(K - 1.0) < tol:
        return FairProbabilities(
            method="shin",
            raw_odds=list(odds),
            raw_implied=r.tolist(),
            overround=K,
            fair_probs=(r / K).tolist(),
            margin_pct=0.0,
        )

    def _probs_given_z(z: float) -> np.ndarray:
        disc = z * z + 4 * (1.0 - z) * r / K
        disc = np.maximum(disc, 0.0)
        p = (np.sqrt(disc) - z) / (2.0 * (1.0 - z) + 1e-15)
        return p

    # Binary search on z ∈ [0, 1) such that Σ p_i = 1
    lo, hi = 0.0, 0.999
    for _ in range(max_iter):
        z = (lo + hi) / 2.0
        p = _probs_given_z(z)
        s = float(p.sum())
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            hi = z
        else:
            lo = z

    p_final = _probs_given_z(z)
    p_final = np.maximum(p_final, 0.0)
    p_final /= p_final.sum()  # renormalize for floating-point safety

    return FairProbabilities(
        method="shin",
        raw_odds=list(odds),
        raw_implied=r.tolist(),
        overround=K,
        fair_probs=p_final.tolist(),
        margin_pct=round((K - 1.0) * 100, 3),
    )


def remove_margin(
    odds: list[float],
    method: Method = "shin",
) -> FairProbabilities:
    """
    Remove bookmaker margin from a list of decimal odds.

    Args:
        odds:   Decimal odds for each outcome in a market (e.g. [1.50, 4.20, 6.50]).
        method: Margin removal method — 'basic', 'power', or 'shin'.

    Returns:
        FairProbabilities with fair_probs summing to 1.0.

    Raises:
        ValueError: if any odd ≤ 1.0 or < 2 outcomes.
    """
    if len(odds) < 2:
        raise ValueError(f"Need at least 2 outcomes, got {len(odds)}")
    if any(o <= 1.0 for o in odds):
        raise ValueError(f"All decimal odds must be > 1.0, got {odds}")

    if method == "basic":
        return _basic(odds)
    if method == "power":
        return _power(odds)
    if method == "shin":
        return _shin(odds)
    raise ValueError(f"Unknown method {method!r}, choose basic/power/shin")


def compare_methods(odds: list[float]) -> dict[str, FairProbabilities]:
    """Run all three margin removal methods and return comparison dict."""
    return {m: remove_margin(odds, method=m) for m in ("basic", "power", "shin")}


def implied_overround(odds: list[float]) -> float:
    """Raw overround K = Σ(1/o_i). K=1.0 is fair; K=1.10 is 10% margin."""
    return sum(1.0 / o for o in odds)


def best_available_fair_prob(
    bookmaker_odds: dict[str, float],
    method: Method = "shin",
) -> float:
    """
    Given {bookmaker: decimal_odds} for ONE outcome, return the fair probability
    implied by the BEST (highest) available odds using single-book margin removal.

    For tournament winner markets, pass odds for one specific team from multiple books.
    """
    if not bookmaker_odds:
        return 0.0
    best = max(bookmaker_odds.values())
    # For a single number we can't remove margin without the full market.
    # Return: 1/best as an approximation of the fair implied probability.
    return 1.0 / best
