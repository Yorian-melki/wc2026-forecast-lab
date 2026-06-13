"""
Form engine: combines Elo data + StatsBomb style metrics into updated team scores.

Outputs:
  - Updated teams.csv with new Elo-derived form + 6 style columns
  - data/elo_snapshot.csv   (raw Elo data for all 48 teams)
  - data/style_metrics.csv  (StatsBomb style per team)
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # wc2026_june2026/
DATA_DIR = ROOT / "data"
ELO_SNAPSHOT_PATH = DATA_DIR / "elo_snapshot.csv"
STYLE_METRICS_PATH = DATA_DIR / "style_metrics.csv"
TEAMS_CSV_PATH = DATA_DIR / "teams.csv"

# How much each signal contributes to the final `form` score.
# Elo current is already represented in attack/defense/etc dimensions;
# here `form` represents recent momentum + style resilience.
FORM_WEIGHTS = {
    "elo_base": 0.50,      # normalized absolute Elo → base quality
    "elo_momentum": 0.35,  # d1yr delta → recent trajectory
    "style_bonus": 0.15,   # style (shot quality, press intensity) → execution edge
}


def fetch_and_save_elo(cache_path: Optional[Path] = None) -> pd.DataFrame:
    """Fetch Elo data for all 48 teams and save snapshot CSV."""
    from .elo_engine import fetch_elo_data, elo_to_form, FIFA3_TO_ELO2

    cache = cache_path or (DATA_DIR / "elo_raw_cache.tsv")
    records = fetch_elo_data(cache_path=cache)

    rows = []
    for fifa3, rec in sorted(records.items()):
        rows.append({
            "code": fifa3,
            "elo2": rec.elo2,
            "elo_current": rec.elo_current,
            "elo_5yr_ago": rec.elo_5yr_ago,
            "elo_wc2022": rec.elo_wc2022_approx,
            "d_1m": rec.d_1m,
            "d_3m": rec.d_3m,
            "d_6m": rec.d_6m,
            "d_1yr": rec.d_1yr,
            "d_2yr": rec.d_2yr,
            "d_5yr": rec.d_5yr,
            "win_rate": round(rec.win_rate, 3),
            "total_matches": rec.total_matches,
            "elo_form_score": elo_to_form(rec.elo_current, rec.d_1yr),
        })

    df = pd.DataFrame(rows)
    df.to_csv(ELO_SNAPSHOT_PATH, index=False)
    print(f"[elo] Saved {len(df)} team Elo records → {ELO_SNAPSHOT_PATH}")
    return df


def load_and_save_style(
    seasons: tuple = (106, 3),
    max_matches_per_season: Optional[int] = None,
) -> pd.DataFrame:
    """Load StatsBomb events, extract style metrics, save CSV."""
    from .statsbomb_loader import load_all_team_events
    from .style_extractor import extract_all_style_metrics

    print(f"[style] Loading StatsBomb events for seasons {seasons}...")
    team_data = load_all_team_events(
        seasons=list(seasons),
        max_matches=max_matches_per_season,
    )
    print(f"[style] Loaded event data for {len(team_data)} teams")

    metrics = extract_all_style_metrics(team_data)

    rows = []
    for fifa3, m in sorted(metrics.items()):
        rows.append({
            "code": fifa3,
            "n_matches": m.n_matches,
            "ppda": m.ppda,
            "shot_quality": m.shot_quality,
            "press_intensity": m.press_intensity,
            "comeback_rate": m.comeback_rate,
            "choke_rate": m.choke_rate,
            "shots_per_game": m.shots_per_game,
            "shots_conceded_per_game": m.shots_conceded_per_game,
        })

    df = pd.DataFrame(rows)
    df.to_csv(STYLE_METRICS_PATH, index=False)
    print(f"[style] Saved style metrics for {len(df)} teams → {STYLE_METRICS_PATH}")
    return df


def _compute_final_form(
    elo_current: int,
    d_1yr: int,
    shot_quality: Optional[float],
    press_intensity: Optional[float],
) -> float:
    """
    Blend Elo base strength + momentum + style edge into a single form score.
    Output ∈ [0, 100].
    """
    # 1. Elo base: 1400→0, 2200→100
    elo_base = max(0.0, min(100.0, (elo_current - 1400) / 8.0))

    # 2. Momentum: d1yr ∈ [-300, +300] → [-37.5, +37.5] → clipped to [-30, +30]
    momentum = max(-30.0, min(30.0, d_1yr / 8.0))
    elo_momentum_score = max(0.0, min(100.0, 50.0 + momentum))

    # 3. Style bonus: shot quality ∈ [0.05, 0.20] → [0, 100]; press ∈ [0, 1]
    sq_norm = max(0.0, min(100.0, (((shot_quality or 0.10) - 0.05) / 0.15) * 100))
    pi_norm = min(100.0, (press_intensity or 0.5) * 100)
    style_score = 0.5 * sq_norm + 0.5 * pi_norm

    final = (
        FORM_WEIGHTS["elo_base"] * elo_base +
        FORM_WEIGHTS["elo_momentum"] * elo_momentum_score +
        FORM_WEIGHTS["style_bonus"] * style_score
    )
    return round(max(0.0, min(100.0, final)), 1)


def update_teams_csv(
    elo_df: pd.DataFrame,
    style_df: Optional[pd.DataFrame] = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    """
    Merge Elo + style data into teams.csv.
    Updates `form` column with data-driven values.
    Adds new columns: elo_current, d_1yr, d_2yr, ppda, shot_quality,
                      press_intensity, comeback_rate, choke_rate.
    """
    teams = pd.read_csv(TEAMS_CSV_PATH)

    # Index by code
    elo_idx = elo_df.set_index("code")
    style_idx = style_df.set_index("code") if style_df is not None else None

    new_cols = {
        "elo_current": [],
        "d_1yr": [],
        "d_2yr": [],
        "elo_wc2022": [],
        "ppda": [],
        "shot_quality": [],
        "press_intensity": [],
        "comeback_rate": [],
        "choke_rate": [],
        "form_data_driven": [],
    }

    updated_form = []
    for _, row in teams.iterrows():
        code = row["code"]
        if code not in elo_idx.index:
            # Fallback: keep existing values
            for col in new_cols:
                new_cols[col].append(None)
            updated_form.append(row["form"])
            continue

        erec = elo_idx.loc[code]
        elo_current = int(erec["elo_current"])
        d_1yr = int(erec["d_1yr"])
        d_2yr = int(erec["d_2yr"])
        elo_wc2022 = int(erec["elo_wc2022"])

        srec = style_idx.loc[code] if style_idx is not None and code in style_idx.index else None
        shot_quality = float(srec["shot_quality"]) if srec is not None else None
        press_intensity = float(srec["press_intensity"]) if srec is not None else None
        ppda = float(srec["ppda"]) if srec is not None else None
        comeback_rate = float(srec["comeback_rate"]) if srec is not None else None
        choke_rate = float(srec["choke_rate"]) if srec is not None else None

        form_dd = _compute_final_form(elo_current, d_1yr, shot_quality, press_intensity)

        new_cols["elo_current"].append(elo_current)
        new_cols["d_1yr"].append(d_1yr)
        new_cols["d_2yr"].append(d_2yr)
        new_cols["elo_wc2022"].append(elo_wc2022)
        new_cols["ppda"].append(ppda)
        new_cols["shot_quality"].append(shot_quality)
        new_cols["press_intensity"].append(press_intensity)
        new_cols["comeback_rate"].append(comeback_rate)
        new_cols["choke_rate"].append(choke_rate)
        new_cols["form_data_driven"].append(form_dd)
        updated_form.append(form_dd)

    for col, values in new_cols.items():
        teams[col] = values

    # Replace the `form` column with data-driven values
    teams["form"] = updated_form

    if not dry_run:
        teams.to_csv(TEAMS_CSV_PATH, index=False, float_format="%.4f")
        print(f"[form] Updated teams.csv with data-driven form for {len(teams)} teams")

    return teams


def run_form_pipeline(
    skip_statsbomb: bool = False,
    max_sb_matches: Optional[int] = None,
    dry_run: bool = False,
) -> pd.DataFrame:
    """
    Full pipeline:
      1. Fetch Elo data (all 48 teams)
      2. Load StatsBomb events (WC 2022 + 2018)
      3. Extract style metrics
      4. Merge + update teams.csv

    Args:
        skip_statsbomb: use cached style_metrics.csv if it exists
        max_sb_matches: cap matches per season (for fast testing)
        dry_run: don't write teams.csv
    Returns:
        Updated teams DataFrame.
    """
    print("=" * 60)
    print("FORM ENGINE — Étape A Data Pipeline")
    print("=" * 60)

    elo_df = fetch_and_save_elo()

    if skip_statsbomb and STYLE_METRICS_PATH.exists():
        style_df = pd.read_csv(STYLE_METRICS_PATH)
        print(f"[style] Loaded cached style metrics from {STYLE_METRICS_PATH}")
    else:
        style_df = load_and_save_style(max_matches_per_season=max_sb_matches)

    result = update_teams_csv(elo_df, style_df, dry_run=dry_run)

    print("\n[form] Top 10 teams by data-driven form:")
    print(f"{'Rank':<5} {'Code':<6} {'Form':>6} {'Elo':>6} {'d1yr':>6}")
    print("-" * 35)
    top10 = result.nlargest(10, "form").reset_index(drop=True)
    for i, r in top10.iterrows():
        d1yr = r.get("d_1yr", "n/a")
        print(f"{i+1:<5} {r['code']:<6} {r['form']:>6.1f} {r.get('elo_current', 'n/a'):>6} {d1yr:>6}")

    return result
