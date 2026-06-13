"""Leak-free feature construction for the ML match model.

Features are built by replaying matches in chronological order and recording the
PRE-match state before each result is applied to the rolling Elo. This guarantees no
target leakage: every feature for match t uses only information available before t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..calibration.rolling_elo import RollingEloEngine

_HOME_ADV = 65.0  # same scale as rolling_elo home advantage


def build_leakfree_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with added leak-free columns: elo_diff, neutral_int, outcome.

    df must have: date, home_team, away_team, home_goals, away_goals, tournament, neutral.
    Rows are processed in date order; elo_diff is the pre-match Elo difference
    (home - away + home advantage when not neutral).
    """
    d = df.sort_values("date").reset_index(drop=True).copy()
    engine = RollingEloEngine()
    elo_diffs = np.empty(len(d), dtype=float)
    outcomes = np.empty(len(d), dtype=int)

    for i, row in enumerate(d.itertuples(index=False)):
        home, away = row.home_team, row.away_team
        neutral = bool(row.neutral)
        elo_h = engine.get_elo(home)   # current rating == pre-match (not yet updated)
        elo_a = engine.get_elo(away)
        home_adv = 0.0 if neutral else _HOME_ADV
        elo_diffs[i] = (elo_h - elo_a) + home_adv
        hg, ag = int(row.home_goals), int(row.away_goals)
        outcomes[i] = 0 if hg > ag else (1 if hg == ag else 2)
        # NOW apply the result (after recording the feature)
        engine.update(home, away, hg, ag, str(row.tournament), neutral, str(row.date))

    d["elo_diff"] = elo_diffs
    d["neutral_int"] = d["neutral"].astype(int)
    d["outcome"] = outcomes
    return d


FEATURE_COLS = ["elo_diff", "neutral_int"]
