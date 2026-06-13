"""
Value bet detection: compare model Monte Carlo probabilities to bookmaker odds.

Two markets:
  1. Tournament winner (champion outright)
  2. Group match 1X2 (H2H)

Pipeline for each:
  model_prob → compare → market_fair_prob (after Shin margin removal) → edge → Kelly
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SUMMARY_PATH = ROOT / "outputs" / "tournament_run" / "summary.csv"


@dataclass
class ValueReport:
    """Full value bet analysis for tournament + matches."""
    champion_bets: list        # list[KellyStake], sorted by edge
    match_bets: list           # list[MatchValueBet], sorted by edge
    n_value_champion: int
    n_value_matches: int
    total_kelly_exposure: float
    diversified_stakes: dict[str, float]
    method: str                # margin removal method used


@dataclass
class MatchValueBet:
    """Value analysis for a single H2H match outcome."""
    home_code: str
    away_code: str
    outcome: str               # 'home', 'draw', 'away'
    decimal_odds: float
    model_prob: float
    market_fair_prob: float
    edge: float
    quarter_kelly: float
    is_value_bet: bool

    def __str__(self) -> str:
        edge_sign = "+" if self.edge >= 0 else ""
        bet = "VALUE" if self.is_value_bet else "----"
        return (
            f"{self.home_code}v{self.away_code} [{self.outcome:4s}] "
            f"odds={self.decimal_odds:>6.2f}  "
            f"model={self.model_prob*100:>5.1f}%  "
            f"mkt={self.market_fair_prob*100:>5.1f}%  "
            f"edge={edge_sign}{self.edge*100:>4.1f}%  "
            f"qkelly={self.quarter_kelly*100:>5.2f}%  [{bet}]"
        )


def _load_model_summary() -> pd.DataFrame:
    if not SUMMARY_PATH.exists():
        raise FileNotFoundError(
            f"summary.csv not found at {SUMMARY_PATH}. "
            "Run: python3 -m wc2026.cli simulate-tournament"
        )
    return pd.read_csv(SUMMARY_PATH)


def analyze_champion_market(
    outright_odds,          # OutrightOdds from fetcher
    method: str = "power",  # 'power' is correct for N>5 outcome markets; shin is for H2H only
    min_edge_pct: float = 2.0,
) -> list:
    """
    Compare model champion probabilities to outright bookmaker odds.
    Returns list[KellyStake] sorted by edge desc.
    """
    from wc2026.odds.margin_removal import remove_margin, implied_overround
    from wc2026.odds.kelly import kelly_table

    df = _load_model_summary()
    model_probs = dict(zip(df["team"], df["champion_prob"]))

    # Build consensus odds and best odds per team
    consensus: dict[str, float] = {}
    best: dict[str, float] = {}
    for code in df["team"]:
        c = outright_odds.consensus_odds(code)
        b = outright_odds.best_odds(code)
        if c > 1.0:
            consensus[code] = c
        if b > 1.0:
            best[code] = b

    # Remove margin from the full field (all teams with odds)
    # Sort teams by consensus odds (favorites first) for stability
    covered = [c for c in df["team"] if c in consensus]
    if not covered:
        return []

    odds_list = [consensus[c] for c in covered]
    fair = remove_margin(odds_list, method=method)

    market_fair_probs: dict[str, float] = {}
    for i, code in enumerate(covered):
        market_fair_probs[code] = fair.fair_probs[i]

    # Use best odds for Kelly calculation
    return kelly_table(
        model_probs={c: model_probs[c] for c in covered},
        best_odds={c: best.get(c, consensus.get(c, 0)) for c in covered},
        market_fair_probs=market_fair_probs,
        min_edge_pct=min_edge_pct,
        sort_by="edge",
    )


def analyze_match_market(
    match_odds_list: list,    # list[MatchOdds] from fetcher
    method: str = "shin",
    min_edge_pct: float = 2.5,
    simulation_iters: int = 10_000,
) -> list[MatchValueBet]:
    """
    Compare model 1X2 probabilities to bookmaker H2H odds for each group match.
    Returns list[MatchValueBet] sorted by edge desc.
    """
    from wc2026.odds.margin_removal import remove_margin
    from wc2026.odds.kelly import kelly_fraction, expected_value, MIN_MODEL_PROB
    from wc2026.data_loader import load_teams, load_config
    from wc2026.match_model import MatchModel

    import numpy as np

    config = load_config()
    teams = load_teams()
    model = MatchModel(config)
    rng = np.random.default_rng(20260611)

    value_bets: list[MatchValueBet] = []

    for mo in match_odds_list:
        cons = mo.consensus_odds
        if cons["home"] <= 1.0 or cons["draw"] <= 1.0 or cons["away"] <= 1.0:
            continue

        # Market fair probabilities (Shin on 3 outcomes)
        odds_3 = [cons["home"], cons["draw"], cons["away"]]
        fair = remove_margin(odds_3, method=method)
        mkt_h, mkt_d, mkt_a = fair.fair_probs

        # Model probabilities (simulate N matches)
        if mo.home_code not in teams or mo.away_code not in teams:
            continue

        hw = dw = aw = 0
        for _ in range(simulation_iters):
            res = model.simulate_group_match(
                teams[mo.home_code], teams[mo.away_code], rng
            )
            if res.goals_a > res.goals_b:
                hw += 1
            elif res.goals_a == res.goals_b:
                dw += 1
            else:
                aw += 1

        p_h = hw / simulation_iters
        p_d = dw / simulation_iters
        p_a = aw / simulation_iters

        best_h = mo.best_home_odds
        best_d = mo.best_draw_odds
        best_a = mo.best_away_odds

        for label, model_p, mkt_p, dec_odds, best_o in [
            ("home", p_h, mkt_h, cons["home"], best_h),
            ("draw", p_d, mkt_d, cons["draw"], best_d),
            ("away", p_a, mkt_a, cons["away"], best_a),
        ]:
            edge = model_p - mkt_p
            b_odds = best_o if best_o > 1.0 else dec_odds
            fk = kelly_fraction(model_p, b_odds)
            ev = expected_value(model_p, b_odds)
            is_value = (
                edge >= min_edge_pct / 100.0
                and model_p >= MIN_MODEL_PROB
                and fk > 0
            )
            value_bets.append(MatchValueBet(
                home_code=mo.home_code,
                away_code=mo.away_code,
                outcome=label,
                decimal_odds=round(b_odds, 2),
                model_prob=round(model_p, 4),
                market_fair_prob=round(mkt_p, 4),
                edge=round(edge, 4),
                quarter_kelly=round(fk * 0.25, 6),
                is_value_bet=is_value,
            ))

    value_bets.sort(key=lambda x: x.edge, reverse=True)
    return value_bets


def build_value_report(
    method: str = "shin",
    champion_min_edge_pct: float = 2.0,
    match_min_edge_pct: float = 2.5,
    match_sim_iters: int = 5_000,
    max_exposure: float = 0.20,
) -> ValueReport:
    """
    Full value report: fetch odds, remove margin, compute Kelly for all markets.
    Works in demo mode (no API key required).
    """
    from wc2026.odds.fetcher import fetch_outright_odds, fetch_match_odds
    from wc2026.odds.kelly import kelly_table, diversified_kelly

    outright = fetch_outright_odds()
    matches = fetch_match_odds()

    champ_stakes = analyze_champion_market(
        outright, method=method, min_edge_pct=champion_min_edge_pct
    )
    match_bets = analyze_match_market(
        matches, method=method, min_edge_pct=match_min_edge_pct,
        simulation_iters=match_sim_iters,
    )

    n_vc = sum(1 for s in champ_stakes if s.is_value_bet)
    n_vm = sum(1 for b in match_bets if b.is_value_bet)
    total_k = sum(s.quarter_kelly for s in champ_stakes if s.is_value_bet)

    div = diversified_kelly(champ_stakes, max_total_exposure=max_exposure)

    return ValueReport(
        champion_bets=champ_stakes,
        match_bets=match_bets,
        n_value_champion=n_vc,
        n_value_matches=n_vm,
        total_kelly_exposure=round(total_k, 4),
        diversified_stakes=div,
        method=method,
    )
