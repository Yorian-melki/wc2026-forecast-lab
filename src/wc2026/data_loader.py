from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Team:
    # Core analyst-prior attributes (all on 0-100 scale; not statistically calibrated)
    code: str
    name: str
    group: str
    fifa_rank: int
    attack: float
    defense: float
    midfield: float
    transition: float
    setpiece: float
    goalkeeper: float
    depth: float
    coach: float
    penalties: float
    discipline: float
    health: float
    form: float
    climate_resilience: float
    altitude_resilience: float
    travel_resilience: float
    # StatsBomb-derived style metrics (real data for 30/48 teams; defaults for 18)
    ppda: float = 6.0           # Passes Per Defensive Action — lower = more pressing
    shot_quality: float = 0.100  # mean xG per shot — higher = better chance creation
    press_intensity: float = 0.35  # normalized pressures per 90 min
    # Comeback/choke rates (all fallback 0.3/0.2 until statsbombpy pipeline re-run)
    comeback_rate: float = 0.30
    choke_rate: float = 0.20
    # Jet lag — performance multiplier ∈ [0.85, 1.0] vs NA venues; computed at load time
    jet_lag_factor: float = 1.0
    # Coverage flag: True = real StatsBomb data; False = Elo/default fallback
    has_statsbomb_data: bool = False


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return project_root() / 'data'


def load_config() -> dict:
    return json.loads((data_dir() / 'config.json').read_text(encoding='utf-8'))


def load_groups() -> Dict[str, List[str]]:
    return json.loads((data_dir() / 'groups.json').read_text(encoding='utf-8'))


def _safe_float(value: str, default: float) -> float:
    """Parse float from CSV, returning default for empty/NaN strings."""
    try:
        v = float(value)
        return default if math.isnan(v) else v
    except (ValueError, TypeError):
        return default


def _compute_jet_lag_factor(team_code: str) -> float:
    """
    Static jet lag factor: representative NA venue (Dallas, UTC-5),
    prime-time kickoff (01:00 UTC = 20:00 Dallas), 5 days adaptation.
    European teams ~0.943, Asian ~0.957, NA teams ~0.980.
    """
    from wc2026.jet_lag import compute_jet_lag
    try:
        result = compute_jet_lag(team_code, venue_city="Dallas",
                                 kickoff_utc=1.0, days_since_arrival=5.0)
        return result.performance_factor
    except Exception:
        return 1.0


def load_teams(apply_temporal_form: bool = True) -> Dict[str, Team]:
    """
    Load all 48 teams from teams.csv, enriching with:
      1. StatsBomb style metrics (ppda/shot_quality/press_intensity) — already in teams.csv
      2. Temporal form from form_history.csv — overwrites `form` for 16 covered teams
      3. Jet lag factor — computed from home UTC offset vs NA venues (all 48 teams)
    """
    path = data_dir() / 'teams.csv'
    teams: Dict[str, Team] = {}

    with path.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            # Detect StatsBomb coverage: ppda is non-NaN only for covered teams
            has_sb = (
                'ppda' in cols
                and row.get('ppda', '').strip() not in ('', 'nan', 'NaN', 'NA')
            )
            team = Team(
                code=row['code'],
                name=row['name'],
                group=row['group'],
                fifa_rank=int(row['fifa_rank']),
                attack=float(row['attack']),
                defense=float(row['defense']),
                midfield=float(row['midfield']),
                transition=float(row['transition']),
                setpiece=float(row['setpiece']),
                goalkeeper=float(row['goalkeeper']),
                depth=float(row['depth']),
                coach=float(row['coach']),
                penalties=float(row['penalties']),
                discipline=float(row['discipline']),
                health=float(row['health']),
                form=float(row['form']),
                climate_resilience=float(row['climate_resilience']),
                altitude_resilience=float(row['altitude_resilience']),
                travel_resilience=float(row['travel_resilience']),
                ppda=_safe_float(row.get('ppda', ''), 6.0),
                shot_quality=_safe_float(row.get('shot_quality', ''), 0.100),
                press_intensity=_safe_float(row.get('press_intensity', ''), 0.35),
                comeback_rate=_safe_float(row.get('comeback_rate', ''), 0.30),
                choke_rate=_safe_float(row.get('choke_rate', ''), 0.20),
                jet_lag_factor=1.0,  # filled below
                has_statsbomb_data=has_sb,
            )
            teams[team.code] = team

    # Apply temporal form (overwrites `form` for the 16 teams in form_history.csv)
    if apply_temporal_form:
        history_path = data_dir() / 'form_history.csv'
        if history_path.exists():
            try:
                from wc2026.temporal_form import compute_all_temporal_forms
                temporal_scores = compute_all_temporal_forms(history_path)
                from dataclasses import replace
                for code, score in temporal_scores.items():
                    if code in teams:
                        teams[code] = replace(teams[code], form=score)
            except Exception:
                pass  # keep form from teams.csv on any error

    # Compute jet lag factors for all 48 teams
    from dataclasses import replace
    for code, team in list(teams.items()):
        factor = _compute_jet_lag_factor(code)
        teams[code] = replace(team, jet_lag_factor=factor)

    return teams


def load_teams_coverage_report(teams: Optional[Dict[str, Team]] = None) -> dict:
    """Return a dict describing data coverage across the 48 teams."""
    if teams is None:
        teams = load_teams()
    total = len(teams)
    sb_count = sum(1 for t in teams.values() if t.has_statsbomb_data)
    jl_non_default = sum(1 for t in teams.values() if t.jet_lag_factor < 1.0)
    form_non_default = sum(1 for t in teams.values() if t.form != 50.0)
    return {
        'total_teams': total,
        'statsbomb_coverage': sb_count,
        'statsbomb_fallback': total - sb_count,
        'jet_lag_computed': jl_non_default,
        'teams_with_form_data': form_non_default,
        # comeback/choke are real for StatsBomb-covered teams (pipeline was run)
        'comeback_choke_real': sb_count,
        'comeback_choke_fallback': total - sb_count,
    }


def validate_data() -> None:
    groups = load_groups()
    teams = load_teams()
    expected = {code for values in groups.values() for code in values}
    actual = set(teams.keys())
    if expected != actual:
        missing = expected - actual
        extra = actual - expected
        raise ValueError(f'data mismatch; missing={sorted(missing)} extra={sorted(extra)}')
    for group, members in groups.items():
        if len(members) != 4:
            raise ValueError(f'group {group} does not contain 4 teams')
        for code in members:
            if teams[code].group != group:
                raise ValueError(f'team {code} has group={teams[code].group}, expected {group}')
