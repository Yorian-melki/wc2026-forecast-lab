"""
Significance testing for model NLL comparison.

Uses approximate standard error based on test set size and empirical NLL variance.
Empirical variance of per-match log-loss ≈ 0.40 nat^2 (calibrated on football datasets).

Convention: delta_nll = nll_challenger - nll_reference
  negative → challenger is better
  positive → challenger is worse
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

import pandas as pd

# Empirical per-match NLL variance calibrated on international football datasets.
# Corresponds to ≈ ±0.063 NLL standard error per match.
_NLL_VARIANCE_PER_MATCH: float = 0.40  # nats^2

Verdict = Literal["clear_win", "marginal_win", "tie", "loss"]

# Verdict z-score thresholds
_CLEAR_WIN_Z  =  2.0   # ≥ 2σ improvement  → clear_win
_MARGINAL_WIN_Z = 0.5  # 0.5–2σ             → marginal_win
_TIE_Z        = -0.5   # within ±0.5σ       → tie
# below -0.5σ          → loss


@dataclass
class SignificanceResult:
    split: str
    n_test: int
    model_a: str         # reference model
    model_b: str         # challenger model
    nll_a: float
    nll_b: float
    delta_nll: float     # nll_b - nll_a  (negative = challenger better)
    approx_se: float     # approx std error of mean NLL for n_test samples
    z_score: float       # how many σ challenger improves over reference
    verdict: Verdict
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def approx_se_nll(n: int) -> float:
    """Approximate standard error of mean NLL for a test set of size n."""
    return math.sqrt(_NLL_VARIANCE_PER_MATCH / max(n, 1))


def classify_verdict(delta_nll: float, se: float) -> tuple[Verdict, str]:
    """
    Map delta_nll + SE to verdict.
    z = -delta/SE (positive = challenger improves).
    """
    z = -delta_nll / max(se, 1e-12)
    if z >= _CLEAR_WIN_Z:
        return "clear_win", f"z={z:.2f} (≥2σ improvement, meaningful)"
    elif z >= _MARGINAL_WIN_Z:
        return "marginal_win", f"z={z:.2f} (0.5–2σ, plausible signal but not conclusive)"
    elif z >= _TIE_Z:
        return "tie", f"z={z:.2f} (within ±0.5σ noise floor, treat as tie)"
    else:
        return "loss", f"z={z:.2f} (challenger worse, negative signal)"


def compute_significance(
    split: str,
    n_test: int,
    model_a: str,
    model_b: str,
    nll_a: float,
    nll_b: float,
) -> SignificanceResult:
    """Compute one pairwise significance result."""
    delta = nll_b - nll_a
    se = approx_se_nll(n_test)
    verdict, note = classify_verdict(delta, se)
    z = -delta / max(se, 1e-12)
    return SignificanceResult(
        split=split, n_test=n_test,
        model_a=model_a, model_b=model_b,
        nll_a=round(nll_a, 5), nll_b=round(nll_b, 5),
        delta_nll=round(delta, 5),
        approx_se=round(se, 5),
        z_score=round(z, 3),
        verdict=verdict, note=note,
    )


def batch_significance(
    backtest_df: pd.DataFrame,
    reference_col: str = "elo_calib_nll",
    challenger_col: str = "hybrid_nll",
    n_test_col: str = "n_test",
    split_col: str = "split",
    model_a_name: str = "elo_calib",
    model_b_name: str = "hybrid",
) -> pd.DataFrame:
    """
    Compute significance for all splits in a backtest DataFrame.
    Returns a DataFrame with one row per split.
    """
    rows = []
    for _, r in backtest_df.iterrows():
        res = compute_significance(
            split=str(r[split_col]),
            n_test=int(r[n_test_col]),
            model_a=model_a_name,
            model_b=model_b_name,
            nll_a=float(r[reference_col]),
            nll_b=float(r[challenger_col]),
        )
        rows.append(res.to_dict())
    return pd.DataFrame(rows)


def summary_verdict(results_df: pd.DataFrame) -> dict:
    """
    Aggregate significance across splits.
    Returns counts per verdict and overall assessment.
    """
    counts = results_df["verdict"].value_counts().to_dict()
    n_clear   = counts.get("clear_win", 0)
    n_marginal= counts.get("marginal_win", 0)
    n_tie     = counts.get("tie", 0)
    n_loss    = counts.get("loss", 0)
    n_total   = len(results_df)

    avg_delta = float(results_df["delta_nll"].mean())
    avg_z     = float(results_df["z_score"].mean())

    if n_clear >= 2:
        overall = "MEANINGFUL_IMPROVEMENT"
    elif n_clear >= 1 or (n_marginal >= 2 and n_loss == 0):
        overall = "MARGINAL_IMPROVEMENT"
    elif n_loss >= 2:
        overall = "DEGRADATION"
    else:
        overall = "INCONCLUSIVE"

    return {
        "n_clear_win": n_clear,
        "n_marginal_win": n_marginal,
        "n_tie": n_tie,
        "n_loss": n_loss,
        "n_total": n_total,
        "avg_delta_nll": round(avg_delta, 5),
        "avg_z_score": round(avg_z, 3),
        "overall": overall,
    }
