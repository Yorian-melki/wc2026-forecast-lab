"""Temporal decay form scoring from match history."""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pandas as pd

RESULT_SCORE: dict[str, float] = {'W': 1.0, 'D': 0.5, 'L': 0.0}
LAMBDA_DECAY = 0.030          # e^(-λ*days) — half-life ≈ 23 days
REFERENCE_DATE = date(2026, 6, 11)  # tournament start


def decay_weight(match_date: date, ref_date: date = REFERENCE_DATE,
                 lam: float = LAMBDA_DECAY) -> float:
    days_ago = max(0, (ref_date - match_date).days)
    return math.exp(-lam * days_ago)


def temporal_form_score(results: list[tuple[str, date]], baseline: float = 75.0) -> float:
    """
    Given a list of (result, match_date) tuples, return a [0,100] form score.
    Weighted average of result scores (W=1, D=0.5, L=0) decayed by days from ref.
    Mapped to [50, 100] range.
    """
    if not results:
        return baseline
    weights = [decay_weight(d) for _, d in results]
    scores = [RESULT_SCORE.get(r, 0.5) for r, _ in results]
    w_total = sum(weights)
    if w_total < 1e-9:
        return baseline
    weighted_avg = sum(s * w for s, w in zip(scores, weights)) / w_total
    return round(min(100.0, max(0.0, 50.0 + weighted_avg * 50.0)), 1)


def compute_all_temporal_forms(history_csv: str | Path) -> dict[str, float]:
    """Load form_history.csv and return {code: form_score} for all teams present."""
    df = pd.read_csv(history_csv)
    df['date'] = pd.to_datetime(df['date']).dt.date
    result: dict[str, float] = {}
    for code, grp in df.groupby('code'):
        pairs = [(row['result'], row['date']) for _, row in grp.iterrows()]
        result[str(code)] = temporal_form_score(pairs)
    return result
