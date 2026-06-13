"""Train + gate a multinomial logistic 1X2 model against an Elo-only baseline.

Hard gate (per mission rules): the ML model is ACCEPTED only if it beats the Elo-only
baseline on held-out Brier AND held-out NLL, on a strictly temporal (leak-free) split.
Otherwise it is REJECTED and not integrated.

The Elo-only baseline uses the SAME pre-match elo_diff feature, mapped through the
standard Elo win formula with a fixed draw bias. So ML wins only if a learned mapping
beats the hand-set formula on the same information — a fair, honest test.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

from ..calibration.metrics import (
    brier_score_1x2,
    negative_log_likelihood,
    calibration_error,
    accuracy_1x2,
)
from .features import FEATURE_COLS


def train_logistic_until(cutoff_date: str, min_year: int = 1990) -> LogisticRegression:
    """Train a leak-free 1X2 logistic model on all matches strictly before cutoff_date.

    Used by the walk-forward tournament validation so each tournament is scored with an
    ML model that never saw that tournament (or anything after it).
    """
    from ..calibration.international_dataset import build_clean_dataset
    from .features import build_leakfree_features, FEATURE_COLS

    df, _ = build_clean_dataset(min_year=min_year, max_year=2025)
    feat = build_leakfree_features(df)
    train = feat[feat["date"] < cutoff_date]
    X = train[FEATURE_COLS].to_numpy(dtype=float)
    y = train["outcome"].to_numpy(dtype=int)
    clf = LogisticRegression(max_iter=2000, C=1.0)
    clf.fit(X, y)
    return clf


def elo_only_probs(elo_diff: float, draw_bias: float = 0.26) -> tuple[float, float, float]:
    """1X2 from pre-match elo_diff via standard Elo formula + fixed draw mass."""
    p_home_win = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
    p_away_win = 1.0 - p_home_win
    p_draw = draw_bias
    return (p_home_win * (1 - draw_bias), p_draw, p_away_win * (1 - draw_bias))


def _norm(probs):
    out = []
    for p in probs:
        s = sum(p)
        out.append(tuple(x / s for x in p))
    return out


def _metrics(probs, outcomes):
    probs = _norm(probs)
    return {
        "nll": round(negative_log_likelihood(probs, outcomes), 5),
        "brier": round(brier_score_1x2(probs, outcomes), 5),
        "ece": round(calibration_error(probs, outcomes), 5),
        "accuracy": round(accuracy_1x2(probs, outcomes), 4),
        "n": len(outcomes),
    }


@dataclass
class GateResult:
    accepted: bool
    reason: str
    ml: dict
    elo_only: dict
    random: dict
    ml_calibrated: dict | None


def train_and_gate(train_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[GateResult, LogisticRegression, IsotonicRegression | None]:
    Xtr = train_df[FEATURE_COLS].to_numpy(dtype=float)
    ytr = train_df["outcome"].to_numpy(dtype=int)
    Xte = test_df[FEATURE_COLS].to_numpy(dtype=float)
    yte = test_df["outcome"].to_numpy(dtype=int)

    clf = LogisticRegression(max_iter=2000, C=1.0)  # multinomial by default in sklearn>=1.7
    clf.fit(Xtr, ytr)
    # sklearn class order
    classes = list(clf.classes_)  # e.g. [0,1,2]
    proba_te = clf.predict_proba(Xte)

    def reorder(proba_row):
        # map to (home=0, draw=1, away=2)
        d = {c: proba_row[i] for i, c in enumerate(classes)}
        return (d.get(0, 0.0), d.get(1, 0.0), d.get(2, 0.0))

    ml_probs = [reorder(r) for r in proba_te]
    elo_probs = [elo_only_probs(x) for x in test_df["elo_diff"].to_numpy(dtype=float)]
    rand_probs = [(1/3, 1/3, 1/3)] * len(yte)

    m_ml = _metrics(ml_probs, yte)
    m_elo = _metrics(elo_probs, yte)
    m_rand = _metrics(rand_probs, yte)

    # Isotonic calibration on the home-win probability (per-class would need 3 fits;
    # we calibrate the max-info dimension and renormalize) — trained on TRAIN folds only.
    proba_tr = clf.predict_proba(Xtr)
    ml_tr = [reorder(r) for r in proba_tr]
    iso = None
    m_cal = None
    try:
        # Calibrate each class with isotonic fit on train, apply to test, renormalize.
        iso_models = []
        for k in range(3):
            ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            p_tr_k = np.array([p[k] for p in ml_tr])
            y_tr_k = (ytr == k).astype(float)
            ir.fit(p_tr_k, y_tr_k)
            iso_models.append(ir)
        cal_probs = []
        for p in ml_probs:
            cp = [iso_models[k].predict([p[k]])[0] for k in range(3)]
            s = sum(cp) or 1.0
            cal_probs.append(tuple(c / s for c in cp))
        m_cal = _metrics(cal_probs, yte)
        iso = iso_models
    except Exception as e:  # pragma: no cover
        m_cal = None

    # Hard gate: ML must beat Elo-only on BOTH Brier and NLL
    beats_brier = m_ml["brier"] < m_elo["brier"]
    beats_nll = m_ml["nll"] < m_elo["nll"]
    accepted = beats_brier and beats_nll
    if accepted:
        reason = (f"ML beats Elo-only on Brier ({m_ml['brier']} < {m_elo['brier']}) "
                  f"and NLL ({m_ml['nll']} < {m_elo['nll']}) on held-out {m_ml['n']} matches.")
    else:
        reason = (f"ML did NOT beat Elo-only on both metrics "
                  f"(Brier {m_ml['brier']} vs {m_elo['brier']}, NLL {m_ml['nll']} vs {m_elo['nll']}). "
                  f"REJECTED per hard gate.")

    return (GateResult(accepted, reason, m_ml, m_elo, m_rand, m_cal), clf, iso)
