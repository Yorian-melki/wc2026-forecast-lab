"""
Historical WC match dataset builder for MLE calibration.

Source: StatsBomb open data (competition_id=43)
  WC2018 season_id=3   → training set (64 matches, 32 teams)
  WC2022 season_id=106 → holdout set  (64 matches, 32 teams)

WARNING: 128 total matches for 40 unique teams → ~3.2 matches/team average.
This is a SPARSE dataset. MLE will require L2 regularization to avoid overfit.
Results should be treated as experimental, not production-ready.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

warnings.filterwarnings("ignore")

COMPETITION_ID = 43
SEASON_TRAIN = 3     # WC2018
SEASON_HOLDOUT = 106  # WC2022

# StatsBomb team name → FIFA-3 code (union of WC2018 + WC2022 teams)
_SB_TO_FIFA3: dict[str, str] = {
    "Argentina": "ARG", "Australia": "AUS", "Belgium": "BEL",
    "Brazil": "BRA", "Cameroon": "CMR", "Canada": "CAN",
    "Colombia": "COL", "Costa Rica": "CRC", "Croatia": "CRO",
    "Denmark": "DEN", "Ecuador": "ECU", "Egypt": "EGY",
    "England": "ENG", "France": "FRA", "Germany": "GER",
    "Ghana": "GHA", "Iceland": "ISL", "Iran": "IRN",
    "Japan": "JPN", "Mexico": "MEX", "Morocco": "MAR",
    "Netherlands": "NED", "Nigeria": "NGA", "Panama": "PAN",
    "Peru": "PER", "Poland": "POL", "Portugal": "POR",
    "Qatar": "QAT", "Russia": "RUS", "Saudi Arabia": "KSA",
    "Senegal": "SEN", "Serbia": "SRB", "South Korea": "KOR",
    "Spain": "ESP", "Sweden": "SWE", "Switzerland": "SUI",
    "Tunisia": "TUN", "United States": "USA", "Uruguay": "URU",
    "Wales": "WAL",
}


@dataclass
class MatchRecord:
    date: str
    competition: str
    home_code: str
    away_code: str
    home_goals: int
    away_goals: int
    weight: float  # time-decay weight, default 1.0


@dataclass
class CalibrationDataset:
    train: pd.DataFrame      # columns: home_code, away_code, home_goals, away_goals, weight, competition, date
    holdout: pd.DataFrame
    all_teams: list[str]     # sorted FIFA3 codes across train+holdout
    mapping_failures: pd.DataFrame  # rows that could not be mapped
    train_summary: dict
    holdout_summary: dict


def _load_season(season_id: int, label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (matched_df, failures_df)."""
    from statsbombpy import sb  # lazy import — only in calibration context
    raw = sb.matches(competition_id=COMPETITION_ID, season_id=season_id)
    rows, failures = [], []

    for _, row in raw.iterrows():
        hn = row["home_team"]
        an = row["away_team"]
        hc = _SB_TO_FIFA3.get(hn)
        ac = _SB_TO_FIFA3.get(an)

        if hc is None or ac is None:
            failures.append({
                "competition": label,
                "home_team": hn,
                "away_team": an,
                "home_code_found": hc,
                "away_code_found": ac,
                "reason": f"no FIFA3 for {'home' if hc is None else 'away'}",
            })
            continue

        hs = row["home_score"]
        as_ = row["away_score"]
        if pd.isna(hs) or pd.isna(as_):
            failures.append({
                "competition": label, "home_team": hn, "away_team": an,
                "home_code_found": hc, "away_code_found": ac,
                "reason": "missing score",
            })
            continue

        rows.append({
            "date": str(row["match_date"]),
            "competition": label,
            "home_code": hc,
            "away_code": ac,
            "home_goals": int(hs),
            "away_goals": int(as_),
            "weight": 1.0,
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date","competition","home_code","away_code","home_goals","away_goals","weight"]
    )
    fail_df = pd.DataFrame(failures) if failures else pd.DataFrame()
    return df, fail_df


def _apply_time_decay(df: pd.DataFrame, decay_rate: float = 0.002) -> pd.DataFrame:
    """
    Exponential time decay: weight = exp(-decay_rate * days_before_ref).
    Reference date = last match in the full dataset.
    decay_rate=0.002 → half-life ≈ 347 days ≈ ~1 year.
    Applied within training set only; holdout always weight=1.0.
    """
    df = df.copy()
    ref_date = pd.to_datetime(df["date"]).max()
    days = (ref_date - pd.to_datetime(df["date"])).dt.days
    df["weight"] = ((-decay_rate * days).apply(lambda x: __import__("math").exp(x)))
    return df


def load_calibration_dataset(
    time_decay: bool = False,
    decay_rate: float = 0.002,
    failures_path: Optional[Path] = None,
) -> CalibrationDataset:
    """
    Load WC2018 (train) + WC2022 (holdout) from StatsBomb.

    WARNING: only 128 matches total across 40 teams.
    Dixon-Coles MLE with 81 free parameters on 128 matches needs strong L2 regularization.
    """
    train_df, train_fail = _load_season(SEASON_TRAIN, "WC2018")
    holdout_df, holdout_fail = _load_season(SEASON_HOLDOUT, "WC2022")
    fail_df = pd.concat([train_fail, holdout_fail], ignore_index=True)

    if time_decay and len(train_df) > 0:
        train_df = _apply_time_decay(train_df, decay_rate)

    all_teams = sorted(
        set(train_df["home_code"]) | set(train_df["away_code"])
        | set(holdout_df["home_code"]) | set(holdout_df["away_code"])
    )

    train_summary = {
        "n_matches": len(train_df),
        "n_teams": len(set(train_df["home_code"]) | set(train_df["away_code"])),
        "competitions": train_df["competition"].unique().tolist() if len(train_df) > 0 else [],
        "mapping_failures": len(train_fail),
        "mapping_success_pct": round(100 * len(train_df) / max(1, len(train_df) + len(train_fail)), 1),
        "mean_home_goals": round(train_df["home_goals"].mean(), 3) if len(train_df) > 0 else None,
        "mean_away_goals": round(train_df["away_goals"].mean(), 3) if len(train_df) > 0 else None,
    }
    holdout_summary = {
        "n_matches": len(holdout_df),
        "n_teams": len(set(holdout_df["home_code"]) | set(holdout_df["away_code"])),
        "competitions": holdout_df["competition"].unique().tolist() if len(holdout_df) > 0 else [],
        "mapping_failures": len(holdout_fail),
        "mapping_success_pct": round(100 * len(holdout_df) / max(1, len(holdout_df) + len(holdout_fail)), 1),
        "mean_home_goals": round(holdout_df["home_goals"].mean(), 3) if len(holdout_df) > 0 else None,
        "mean_away_goals": round(holdout_df["away_goals"].mean(), 3) if len(holdout_df) > 0 else None,
    }

    if failures_path is not None and len(fail_df) > 0:
        failures_path.parent.mkdir(parents=True, exist_ok=True)
        fail_df.to_csv(failures_path, index=False)

    return CalibrationDataset(
        train=train_df,
        holdout=holdout_df,
        all_teams=all_teams,
        mapping_failures=fail_df,
        train_summary=train_summary,
        holdout_summary=holdout_summary,
    )
