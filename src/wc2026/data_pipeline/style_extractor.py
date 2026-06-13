"""
Style metrics extraction from StatsBomb events.

Metrics per team:
  ppda            — Passes Per Defensive Action (lower = more pressing intensity)
  shot_quality    — mean xG per shot (higher = better chance creation quality)
  comeback_rate   — fraction of games where team trailed at some point then drew/won
  choke_rate      — fraction of games where team led at some point then drew/lost
  press_intensity — pressures per 90 min (normalized)
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

COMPETITION_ID = 43
WC2022_SEASON = 106
WC2018_SEASON = 3


@dataclass
class StyleMetrics:
    team_code: str
    n_matches: int
    ppda: float                # ~6-12 for high press; higher = less press
    shot_quality: float        # mean xG per shot; typical 0.08-0.15
    press_intensity: float     # pressures per 90 min, normalized [0,1]
    comeback_rate: float       # ∈ [0, 1]
    choke_rate: float          # ∈ [0, 1]
    shots_per_game: float
    shots_conceded_per_game: float


def _is_in_defensive_third(location) -> bool:
    """StatsBomb pitch is 120x80. Defensive third = x ∈ [0, 40]."""
    try:
        return float(location[0]) <= 40.0
    except (TypeError, IndexError):
        return False


def _is_in_attacking_third(location) -> bool:
    """Attacking third = x ∈ [80, 120]."""
    try:
        return float(location[0]) >= 80.0
    except (TypeError, IndexError):
        return False


def compute_ppda(
    team_pressures: pd.DataFrame,
    opp_passes: pd.DataFrame,
) -> float:
    """
    PPDA = opponent passes in opponent's own half / team defensive actions in opponent's half.
    Defensive actions here = pressures applied by the team in the opponent's half.
    Lower PPDA → more aggressive pressing.
    """
    # Pressures in opponent's half (x >= 60)
    press_in_opp_half = 0
    if len(team_pressures) > 0 and "location" in team_pressures.columns:
        press_in_opp_half = team_pressures["location"].apply(
            lambda loc: isinstance(loc, (list, tuple)) and float(loc[0]) >= 60.0
        ).sum()

    # Opponent passes in their own half (x <= 60) = "allowed passes" in build-up zone
    opp_passes_in_own_half = 0
    if len(opp_passes) > 0 and "location" in opp_passes.columns:
        opp_passes_in_own_half = opp_passes["location"].apply(
            lambda loc: isinstance(loc, (list, tuple)) and float(loc[0]) <= 60.0
        ).sum()

    if press_in_opp_half == 0:
        return 15.0  # default: low pressing
    return round(opp_passes_in_own_half / press_in_opp_half, 2)


def compute_shot_quality(shots: pd.DataFrame) -> float:
    """Mean xG per shot. StatsBomb field: shot_statsbomb_xg."""
    if len(shots) == 0:
        return 0.10  # league average default
    col = "shot_statsbomb_xg"
    if col not in shots.columns:
        return 0.10
    xg_vals = pd.to_numeric(shots[col], errors="coerce").dropna()
    if len(xg_vals) == 0:
        return 0.10
    return round(float(xg_vals.mean()), 4)


def compute_comeback_choke(match_events: list[pd.DataFrame], team_name: str) -> tuple[float, float]:
    """
    Per-match: track goals scored to detect leading/trailing states.
    Returns (comeback_rate, choke_rate).

    comeback_rate = games_led_by_opp_at_some_point AND team_result >= draw / n_such_games
    choke_rate    = games_led_by_team_at_some_point AND team_result <= draw / n_such_games
    """
    n_comeback_opportunities = 0
    n_comebacks = 0
    n_choke_opportunities = 0
    n_chokes = 0

    for events in match_events:
        goals = events[events["type"] == "Shot"].copy()
        # Only count shots where shot_outcome == 'Goal'
        if "shot_outcome" in goals.columns:
            goals = goals[goals["shot_outcome"].apply(
                lambda x: x == "Goal" if isinstance(x, str) else
                (x.get("name") == "Goal" if isinstance(x, dict) else False)
            )]
        else:
            continue

        # Get team goals and opponent goals in chronological order
        team_goals_min = goals[goals["team"] == team_name]["minute"].tolist()
        opp_goals_min = goals[goals["team"] != team_name]["minute"].tolist()

        all_events = sorted(
            [(m, "team") for m in team_goals_min] +
            [(m, "opp") for m in opp_goals_min]
        )

        score_t, score_o = 0, 0
        was_trailing, was_leading = False, False
        for _minute, scorer in all_events:
            if scorer == "team":
                score_t += 1
            else:
                score_o += 1
            if score_t < score_o:
                was_trailing = True
            if score_t > score_o:
                was_leading = True

        final_result = (
            "win" if score_t > score_o else
            "draw" if score_t == score_o else "loss"
        )

        if was_trailing:
            n_comeback_opportunities += 1
            if final_result in ("win", "draw"):
                n_comebacks += 1

        if was_leading:
            n_choke_opportunities += 1
            if final_result in ("loss", "draw"):
                n_chokes += 1

    comeback_rate = (n_comebacks / n_comeback_opportunities) if n_comeback_opportunities > 0 else 0.3
    choke_rate = (n_chokes / n_choke_opportunities) if n_choke_opportunities > 0 else 0.2
    return round(comeback_rate, 3), round(choke_rate, 3)


def extract_style_metrics(
    team_events,  # TeamMatchEvents
    team_name: str,
    match_events_list: Optional[list[pd.DataFrame]] = None,
) -> StyleMetrics:
    """Compute all style metrics for a single team."""
    tme = team_events

    ppda = compute_ppda(tme.pressures, tme.passes_against)
    shot_quality = compute_shot_quality(tme.shots)

    n_matches = max(1, tme.n_matches)
    shots_per_game = len(tme.shots) / n_matches

    # shots_conceded: use opponent Shot events (correct); passes_against was a bug
    if hasattr(tme, 'shots_against') and len(tme.shots_against) > 0:
        shots_conceded_per_game = len(tme.shots_against) / n_matches
    else:
        # fallback: estimate from shots_per_game (rough league-average reciprocal)
        shots_conceded_per_game = shots_per_game * 0.85

    # Pressures per 90 min
    total_min = n_matches * 90
    pressures_per_90 = (len(tme.pressures) / total_min * 90) if total_min > 0 else 0
    press_intensity = min(1.0, pressures_per_90 / 350.0)

    # Comeback/choke: prefer inline counters, fall back to match_events_list, then defaults
    if hasattr(tme, 'comeback_opps') and tme.comeback_opps > 0:
        comeback_rate = round(tme.comebacks / tme.comeback_opps, 3)
    elif hasattr(tme, 'choke_opps') and tme.choke_opps == 0 and hasattr(tme, 'comeback_opps'):
        # processed but team never trailed — set comeback_rate to neutral
        comeback_rate = 0.5
    elif match_events_list is not None:
        comeback_rate, _ = compute_comeback_choke(match_events_list, team_name)
    else:
        comeback_rate = 0.3  # fallback — mark in coverage report

    if hasattr(tme, 'choke_opps') and tme.choke_opps > 0:
        choke_rate = round(tme.chokes / tme.choke_opps, 3)
    elif match_events_list is not None:
        _, choke_rate = compute_comeback_choke(match_events_list, team_name)
    else:
        choke_rate = 0.2  # fallback

    return StyleMetrics(
        team_code=tme.team_code,
        n_matches=n_matches,
        ppda=ppda,
        shot_quality=shot_quality,
        press_intensity=round(press_intensity, 4),
        comeback_rate=comeback_rate,
        choke_rate=choke_rate,
        shots_per_game=round(shots_per_game, 2),
        shots_conceded_per_game=round(shots_conceded_per_game, 2),
    )


def extract_all_style_metrics(
    team_data: dict,  # {fifa3: TeamMatchEvents}
    match_events_by_match: Optional[dict[int, pd.DataFrame]] = None,
) -> dict[str, StyleMetrics]:
    """Extract StyleMetrics for every team in team_data."""
    from .statsbomb_loader import SB_NAME_TO_CODE
    code_to_name = {v: k for k, v in SB_NAME_TO_CODE.items()}

    results: dict[str, StyleMetrics] = {}
    for fifa3, tme in team_data.items():
        team_name = code_to_name.get(fifa3, fifa3)
        results[fifa3] = extract_style_metrics(tme, team_name)

    return results
