"""
Binomial confidence intervals for tournament probabilities.
Uses Wilson score interval — more accurate than normal approximation at extreme probs.
"""
from __future__ import annotations

import math
import pandas as pd


def wilson_ci(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a proportion p estimated from n trials."""
    if n == 0:
        return 0.0, 1.0
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def add_confidence_intervals(summary: pd.DataFrame, iterations: int) -> pd.DataFrame:
    """
    Append Wilson 95% CI columns to a tournament summary DataFrame.
    Adds: champion_ci_low, champion_ci_high, final_ci_low, final_ci_high,
          sf_ci_low, sf_ci_high.
    """
    df = summary.copy()
    for col, base in [
        ('champion_prob', 'champion'),
        ('final_prob', 'final'),
        ('sf_prob', 'sf'),
        ('group_survival_prob', 'group'),
    ]:
        lows, highs = [], []
        for p in df[col]:
            lo, hi = wilson_ci(float(p), iterations)
            lows.append(round(lo, 6))
            highs.append(round(hi, 6))
        df[f'{base}_ci_low'] = lows
        df[f'{base}_ci_high'] = highs
    return df
