"""OFFLINE-ONLY: leakage-free pre-match feature derivation for Phase 3A evidence lab.

Given a chronologically-ordered match log, computes for each match ONLY features knowable BEFORE
kickoff (rolling form, goal rates, rest days) plus Elo from a passed-in engine. Each match's features
use strictly prior matches; the current match updates the rolling state AFTER it is recorded (no leak).

NOT imported by app.py or the production model. Pure functions; deterministic. Cannot affect live.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date as _date

import numpy as np
import pandas as pd

FEATURES = ["elo_diff", "elo_sum", "gf_diff", "ga_diff", "form_diff", "rest_diff", "neutral"]


def _d(s: str) -> _date:
    y, m, d = (int(x) for x in str(s)[:10].split("-"))
    return _date(y, m, d)


def build_rolling_features(df: pd.DataFrame, elo_get, window: int = 6) -> pd.DataFrame:
    """df sorted by date asc with home_team, away_team, date, neutral, home_goals, away_goals.

    `elo_get(team, before_date)` returns the pre-match Elo. Returns a feature DataFrame aligned to df,
    plus the W/D/L outcome (0 home / 1 draw / 2 away) and total goals.
    """
    gf = defaultdict(lambda: deque(maxlen=window))
    ga = defaultdict(lambda: deque(maxlen=window))
    pts = defaultdict(lambda: deque(maxlen=window))
    last: dict[str, _date] = {}

    rows = []
    for h, a, ds, n, hg, ag in zip(df["home_team"], df["away_team"], df["date"],
                                   df["neutral"], df["home_goals"], df["away_goals"]):
        d = _d(ds)
        eh, ea = elo_get(h, before_date=ds), elo_get(a, before_date=ds)
        adv = 0.0 if n else 100.0

        def mean(dq, default):
            return float(np.mean(dq)) if len(dq) else default

        h_gf, h_ga, h_pt = mean(gf[h], 1.2), mean(ga[h], 1.2), mean(pts[h], 1.3)
        a_gf, a_ga, a_pt = mean(gf[a], 1.2), mean(ga[a], 1.2), mean(pts[a], 1.3)
        h_rest = min((d - last[h]).days, 90) if h in last else 30
        a_rest = min((d - last[a]).days, 90) if a in last else 30

        rows.append({
            "elo_diff": (eh + adv - ea) / 400.0,
            "elo_sum": (eh + ea - 3000.0) / 400.0,
            "gf_diff": h_gf - a_gf,
            "ga_diff": h_ga - a_ga,
            "form_diff": h_pt - a_pt,
            "rest_diff": (h_rest - a_rest) / 30.0,
            "neutral": 1.0 if n else 0.0,
            "outcome": 0 if hg > ag else (1 if hg == ag else 2),
            "total_goals": int(hg) + int(ag),
        })

        # update rolling state AFTER recording (strictly pre-match features above)
        gf[h].append(hg); ga[h].append(ag); pts[h].append(3 if hg > ag else (1 if hg == ag else 0))
        gf[a].append(ag); ga[a].append(hg); pts[a].append(3 if ag > hg else (1 if hg == ag else 0))
        last[h] = last[a] = d

    return pd.DataFrame(rows)
