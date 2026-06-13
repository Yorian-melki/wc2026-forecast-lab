"""
Kelly criterion stake calculator for sports betting.

Full Kelly:   f* = (b·p - q) / b = (p·(b+1) - 1) / b
Half Kelly:   0.5 · f*
Quarter Kelly: 0.25 · f*  (recommended for high-variance sports events)

Where:
  b = decimal_odds - 1.0   (net profit per unit staked)
  p = model probability of the event
  q = 1 - p

References:
  Kelly (1956) "A New Interpretation of Information Rate"
  MacLean, Thorp, Ziemba (2011) "The Kelly Capital Growth Investment Criterion"
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class KellyStake:
    team_or_outcome: str
    decimal_odds: float
    model_prob: float          # our Monte Carlo estimate
    market_fair_prob: float    # after margin removal
    edge: float                # model_prob - market_fair_prob
    full_kelly: float          # full Kelly fraction (can be negative = no bet)
    half_kelly: float
    quarter_kelly: float       # recommended for sports
    expected_value: float      # EV per unit = p*(b+1) - 1
    is_value_bet: bool         # edge > MIN_EDGE threshold

    @property
    def best_decimal_odds(self) -> float:
        return self.decimal_odds

    def __str__(self) -> str:
        edge_sign = "+" if self.edge >= 0 else ""
        bet = "VALUE" if self.is_value_bet else "SKIP"
        return (
            f"{self.team_or_outcome:<8} odds={self.decimal_odds:>7.2f}  "
            f"model={self.model_prob*100:>5.1f}%  "
            f"mkt={self.market_fair_prob*100:>5.1f}%  "
            f"edge={edge_sign}{self.edge*100:>4.1f}%  "
            f"qkelly={self.quarter_kelly*100:>5.2f}%  "
            f"EV={self.expected_value*100:>+.2f}%  [{bet}]"
        )


# Minimum edge to qualify as a value bet (model > market by this much)
MIN_EDGE_PCT = 2.0        # 2 percentage points
MIN_MODEL_PROB = 0.005    # don't bet on <0.5% probability outcomes


def kelly_fraction(model_prob: float, decimal_odds: float) -> float:
    """
    Full Kelly fraction. Returns 0 if there's no positive edge.
    f* = (p·b - q) / b  where b = decimal_odds - 1.
    """
    b = decimal_odds - 1.0
    if b <= 0 or model_prob <= 0 or model_prob >= 1:
        return 0.0
    p, q = model_prob, 1.0 - model_prob
    f = (p * b - q) / b
    return max(0.0, f)


def expected_value(model_prob: float, decimal_odds: float) -> float:
    """EV per unit staked: p*(decimal_odds) - 1."""
    return model_prob * decimal_odds - 1.0


def compute_kelly_stake(
    team_or_outcome: str,
    decimal_odds: float,
    model_prob: float,
    market_fair_prob: float,
    min_edge_pct: float = MIN_EDGE_PCT,
    min_model_prob: float = MIN_MODEL_PROB,
) -> KellyStake:
    """
    Full Kelly analysis for a single bet.

    Args:
        team_or_outcome: label (e.g. 'ESP' or 'MEX_WIN')
        decimal_odds:     best available decimal odds from any bookmaker
        model_prob:       Monte Carlo model probability
        market_fair_prob: market-implied fair probability after margin removal
        min_edge_pct:     minimum edge (in %, e.g. 2.0) to flag as value bet
        min_model_prob:   don't compute Kelly for negligible probabilities

    Returns:
        KellyStake with full/half/quarter Kelly fractions.
    """
    edge = model_prob - market_fair_prob
    full_k = kelly_fraction(model_prob, decimal_odds)
    ev = expected_value(model_prob, decimal_odds)

    # Flag as value bet if:
    # 1. Positive Kelly (EV > 0 at offered odds)
    # 2. Model sees more probability than market (edge > 0)
    # 3. Either absolute edge > threshold  OR  relative edge > 15%
    #    (the relative condition catches correctly-sized longshot edges)
    rel_edge = edge / (market_fair_prob + 1e-10)
    is_value = (
        full_k > 0
        and model_prob >= min_model_prob
        and edge > 0
        and (edge >= min_edge_pct / 100.0 or rel_edge >= 0.15)
    )

    return KellyStake(
        team_or_outcome=team_or_outcome,
        decimal_odds=decimal_odds,
        model_prob=model_prob,
        market_fair_prob=market_fair_prob,
        edge=edge,
        full_kelly=round(full_k, 6),
        half_kelly=round(full_k * 0.5, 6),
        quarter_kelly=round(full_k * 0.25, 6),
        expected_value=round(ev, 6),
        is_value_bet=is_value,
    )


def kelly_table(
    model_probs: dict[str, float],
    best_odds: dict[str, float],
    market_fair_probs: dict[str, float],
    min_edge_pct: float = MIN_EDGE_PCT,
    sort_by: str = "edge",
) -> list[KellyStake]:
    """
    Build Kelly stake table for multiple outcomes simultaneously.

    Args:
        model_probs:       {team_code: model_probability}
        best_odds:         {team_code: best decimal odds from any book}
        market_fair_probs: {team_code: fair prob after margin removal}
        min_edge_pct:      minimum edge threshold in percentage points
        sort_by:           'edge', 'ev', 'kelly', or 'model_prob'

    Returns:
        Sorted list of KellyStake records.
    """
    stakes = []
    for code, model_p in model_probs.items():
        odds = best_odds.get(code, 0.0)
        market_fair = market_fair_probs.get(code, model_p)
        if odds <= 1.0 or model_p <= 0:
            continue
        stake = compute_kelly_stake(
            team_or_outcome=code,
            decimal_odds=odds,
            model_prob=model_p,
            market_fair_prob=market_fair,
            min_edge_pct=min_edge_pct,
        )
        stakes.append(stake)

    sort_keys = {
        "edge": lambda s: s.edge,
        "ev": lambda s: s.expected_value,
        "kelly": lambda s: s.full_kelly,
        "model_prob": lambda s: s.model_prob,
    }
    key_fn = sort_keys.get(sort_by, sort_keys["edge"])
    stakes.sort(key=key_fn, reverse=True)
    return stakes


def diversified_kelly(
    stakes: list[KellyStake],
    max_total_exposure: float = 0.20,
    fraction: float = 0.25,
) -> dict[str, float]:
    """
    Scale down Kelly fractions so total bankroll exposure stays within limit.
    When individual quarter_kelly fractions add up to > max_total_exposure,
    scale all proportionally.

    Args:
        stakes:               from kelly_table(), all bets to consider
        max_total_exposure:   max fraction of bankroll across all bets (default 20%)
        fraction:             which Kelly fraction to use (default quarter = 0.25)

    Returns:
        {team_or_outcome: adjusted_fraction}
    """
    value_bets = [s for s in stakes if s.is_value_bet]
    if not value_bets:
        return {}

    attr = "quarter_kelly" if fraction == 0.25 else "half_kelly" if fraction == 0.5 else "full_kelly"
    raw = {s.team_or_outcome: getattr(s, attr) for s in value_bets}
    total = sum(raw.values())

    if total <= max_total_exposure:
        return raw

    scale = max_total_exposure / total
    return {k: round(v * scale, 6) for k, v in raw.items()}
