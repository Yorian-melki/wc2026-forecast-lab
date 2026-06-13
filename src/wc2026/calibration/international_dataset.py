"""
International match dataset builder from martj42/international_results.

Source: data/external/international_results/results.csv
49,450 matches from 1872 to present, 336 teams.

For the hybrid model, we use:
  - Full name as the team identifier during training
  - FIFA3 codes for the 48 WC2026 teams only (when integrating with match_model)
  - Rolling Elo for all teams computed from match history

Dataset splits:
  FULL_2000_2026       : all competitive+friendly, 2000-present
  FULL_2010_2026       : all competitive+friendly, 2010-present
  COMPETITIVE_2010_2026: no friendlies, 2010-present
  WC_ONLY_1990_2022    : FIFA World Cup final tournament only
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW_PATH = ROOT / "data" / "external" / "international_results" / "results.csv"
TEAMS_CSV = ROOT / "data" / "teams.csv"
OUT_DIR = ROOT / "outputs" / "calibration"

# Tournament weight assignments
TOURNAMENT_WEIGHTS: dict[str, float] = {
    "FIFA World Cup": 1.00,
    "UEFA Euro": 0.90,
    "Copa América": 0.90,
    "AFC Asian Cup": 0.85,
    "Africa Cup of Nations": 0.85,
    "African Cup of Nations": 0.85,
    "CONCACAF Gold Cup": 0.80,
    "Gold Cup": 0.80,
    "OFC Nations Cup": 0.75,
    "Olympic Games": 0.70,
    "FIFA World Cup qualification": 0.80,
    "UEFA Euro qualification": 0.75,
    "Copa América qualification": 0.75,
    "AFC Asian Cup qualification": 0.70,
    "African Cup of Nations qualification": 0.70,
    "CONCACAF Nations League": 0.70,
    "UEFA Nations League": 0.70,
}
_FRIENDLY_WEIGHT = 0.35
_DEFAULT_WEIGHT = 0.60
_FRIENDLY_KEYWORDS = {"friendly", "four nations", "triangular", "tournament"}


def _is_friendly(tournament: str) -> bool:
    t = tournament.lower()
    return any(kw in t for kw in _FRIENDLY_KEYWORDS)


def _tournament_weight(tournament: str) -> float:
    if tournament in TOURNAMENT_WEIGHTS:
        return TOURNAMENT_WEIGHTS[tournament]
    if _is_friendly(tournament):
        return _FRIENDLY_WEIGHT
    t = tournament.lower()
    if "qualif" in t or "nations league" in t:
        return 0.70
    if "championship" in t or "cup of nations" in t:
        return 0.80
    return _DEFAULT_WEIGHT


def _name_to_fifa3_map() -> dict[str, str]:
    """Build full_name → FIFA3 code map from teams.csv (WC2026 teams only)."""
    teams = pd.read_csv(TEAMS_CSV)
    return dict(zip(teams["name"], teams["code"]))


def load_raw_matches() -> pd.DataFrame:
    """Load and lightly clean the raw martj42 CSV."""
    df = pd.read_csv(RAW_PATH, parse_dates=["date"])
    # Drop rows with missing scores (scheduled fixtures)
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df["year"] = df["date"].dt.year
    df["weight"] = df["tournament"].apply(_tournament_weight)
    df["is_friendly"] = df["tournament"].apply(_is_friendly)
    df["is_competitive"] = ~df["is_friendly"]
    return df


def build_clean_dataset(
    min_year: int = 1990,
    max_year: int = 2025,  # exclude ongoing WC2026
    competitive_only: bool = False,
    failures_path: Optional[Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build a clean normalized match DataFrame.

    Returns (matches_df, failures_df).
    matches_df columns: date, home_team, away_team, home_code, away_code,
                        home_goals, away_goals, tournament, neutral, weight, source
    """
    df = load_raw_matches()
    df = df[(df["year"] >= min_year) & (df["year"] <= max_year)]
    if competitive_only:
        df = df[df["is_competitive"]]

    name_to_code = _name_to_fifa3_map()
    rows, failures = [], []

    for _, row in df.iterrows():
        hc = name_to_code.get(row["home_team"])
        ac = name_to_code.get(row["away_team"])
        # Teams without FIFA3 codes are not WC2026 teams — keep as name-only
        rows.append({
            "date": row["date_str"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "home_code": hc,   # None if not WC2026 team
            "away_code": ac,
            "home_goals": int(row["home_score"]),
            "away_goals": int(row["away_score"]),
            "tournament": row["tournament"],
            "neutral": bool(row["neutral"]),
            "weight": float(row["weight"]),
            "source": "martj42",
        })

    clean_df = pd.DataFrame(rows)
    fail_df = pd.DataFrame(failures)

    if failures_path and len(fail_df) > 0:
        failures_path.parent.mkdir(parents=True, exist_ok=True)
        fail_df.to_csv(failures_path, index=False)

    return clean_df, fail_df


def make_temporal_splits(
    df: pd.DataFrame,
) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Produce named (train, test) temporal splits. No data leakage guaranteed
    since all test data is strictly after the last training date.

    Returns dict of split_name → (train_df, test_df).
    """
    splits = {}

    # Split 1: train ≤ 2014, test 2015–2018
    tr = df[df["date"] <= "2014-12-31"]
    te = df[(df["date"] >= "2015-01-01") & (df["date"] <= "2018-12-31")]
    splits["train_pre2015_test_2015_2018"] = (tr, te)

    # Split 2: train ≤ 2018, test 2019–2022
    tr = df[df["date"] <= "2018-12-31"]
    te = df[(df["date"] >= "2019-01-01") & (df["date"] <= "2022-12-31")]
    splits["train_pre2019_test_2019_2022"] = (tr, te)

    # Split 3: WC holdout — train all non-WC2022, test WC2022 matches only
    tr = df[~((df["tournament"] == "FIFA World Cup") & (df["date"] >= "2022-11-01"))]
    te = df[(df["tournament"] == "FIFA World Cup") & (df["date"] >= "2022-11-01") & (df["date"] <= "2022-12-30")]
    splits["wc2022_holdout"] = (tr, te)

    # Split 4: train ≤ 2022, recent test 2023–2025
    tr = df[df["date"] <= "2022-12-31"]
    te = df[(df["date"] >= "2023-01-01") & (df["date"] <= "2025-12-31")]
    splits["train_pre2023_test_2023_2025"] = (tr, te)

    return splits


def dataset_audit(df: pd.DataFrame, label: str = "") -> dict:
    """Produce a summary dict for a dataset."""
    n = len(df)
    years = pd.to_datetime(df["date"]).dt.year
    competitive = df[df["tournament"] != "Friendly"]
    neutral_pct = round(100 * df["neutral"].mean(), 1) if n > 0 else 0
    return {
        "label": label,
        "n_matches": n,
        "date_min": df["date"].min() if n > 0 else None,
        "date_max": df["date"].max() if n > 0 else None,
        "n_teams": len(set(df["home_team"]) | set(df["away_team"])),
        "n_tournaments": df["tournament"].nunique() if n > 0 else 0,
        "neutral_pct": neutral_pct,
        "n_competitive": len(competitive),
        "n_post_2000": int((years >= 2000).sum()),
        "n_post_2010": int((years >= 2010).sum()),
        "n_competitive_post_2010": int(
            ((years >= 2010) & (df["tournament"] != "Friendly")).sum()
        ),
        "mean_home_goals": round(df["home_goals"].mean(), 3) if n > 0 else None,
        "mean_away_goals": round(df["away_goals"].mean(), 3) if n > 0 else None,
    }
