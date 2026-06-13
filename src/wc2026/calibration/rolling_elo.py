"""
Rolling Elo computation from martj42 international results.

Uses the standard Elo rating system with tournament-weighted K-factors,
matching the eloratings.net methodology (no home advantage for neutral games).

K-factors (per eloratings.net specification):
  60 — FIFA World Cup finals
  50 — continental final tournaments + Olympics
  40 — FIFA World Cup qualifiers, continental qualifiers
  30 — all other tournaments including friendlies

Home advantage: +100 Elo points unless neutral=True.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


# Tournament → K-factor mapping (eloratings.net methodology)
_TOURNAMENT_K: dict[str, float] = {
    # Top tier
    "FIFA World Cup": 60.0,
    "UEFA Euro": 50.0,
    "Copa América": 50.0,
    "AFC Asian Cup": 50.0,
    "Africa Cup of Nations": 50.0,
    "African Cup of Nations": 50.0,
    "CONCACAF Gold Cup": 50.0,
    "Gold Cup": 50.0,
    "OFC Nations Cup": 50.0,
    "Olympic Games": 50.0,
    # Qualifiers & Nations Leagues
    "FIFA World Cup qualification": 40.0,
    "UEFA Euro qualification": 40.0,
    "Copa América qualification": 40.0,
    "AFC Asian Cup qualification": 40.0,
    "African Cup of Nations qualification": 40.0,
    "CONCACAF Nations League": 40.0,
    "UEFA Nations League": 40.0,
    "CONMEBOL–UEFA Cup of Champions": 50.0,
}
_DEFAULT_K_FRIENDLY = 30.0
_DEFAULT_K_QUALIFIER = 40.0
_DEFAULT_K_CONTINENTAL = 45.0
_HOME_ADVANTAGE = 100.0
_INITIAL_ELO = 1500.0


def _k_factor(tournament: str) -> float:
    if tournament in _TOURNAMENT_K:
        return _TOURNAMENT_K[tournament]
    t = tournament.lower()
    if "world cup" in t:
        return 50.0
    if "qualif" in t or "nations league" in t:
        return 40.0
    if "championship" in t or "cup of nations" in t or "continental" in t:
        return 45.0
    if "friendly" in t or "four nations" in t or "triangular" in t:
        return 30.0
    return 35.0  # default


def _elo_expected(elo_a: float, elo_b: float, home_adv: float = 0.0) -> float:
    """Expected score for team A against team B (1=win, 0.5=draw, 0=loss)."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a - home_adv) / 400.0))


@dataclass
class RollingEloEngine:
    """
    Maintains rolling Elo ratings for all international teams.

    Usage:
        engine = RollingEloEngine()
        engine.fit(matches_df)
        elo_at_date = engine.get_elo("France", "2021-11-01")
    """
    ratings: dict[str, float] = field(default_factory=dict)
    # history[team][date] = elo_after_that_date (for pre-match lookup)
    history: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    n_matches_processed: int = 0

    def _get_rating(self, team: str) -> float:
        return self.ratings.get(team, _INITIAL_ELO)

    def get_elo(self, team: str, before_date: Optional[str] = None) -> float:
        """
        Get Elo for a team, optionally before a specific date (for pre-match lookup).
        Returns rating as of the last match BEFORE before_date.
        """
        if before_date is None:
            return self._get_rating(team)
        hist = self.history.get(team, [])
        # Binary search for last entry before before_date
        elo = _INITIAL_ELO
        for date_str, rating in hist:
            if date_str < before_date:
                elo = rating
            else:
                break
        return elo

    def update(self, home_team: str, away_team: str, home_goals: int, away_goals: int,
               tournament: str, neutral: bool, date: str) -> tuple[float, float]:
        """Process one match and return (elo_change_home, elo_change_away)."""
        elo_h = self._get_rating(home_team)
        elo_a = self._get_rating(away_team)
        k = _k_factor(tournament)
        home_adv = 0.0 if neutral else _HOME_ADVANTAGE
        exp_h = _elo_expected(elo_h, elo_a, home_adv)
        exp_a = 1.0 - exp_h
        if home_goals > away_goals:
            act_h, act_a = 1.0, 0.0
        elif home_goals == away_goals:
            act_h, act_a = 0.5, 0.5
        else:
            act_h, act_a = 0.0, 1.0
        delta_h = k * (act_h - exp_h)
        delta_a = k * (act_a - exp_a)
        self.ratings[home_team] = elo_h + delta_h
        self.ratings[away_team] = elo_a + delta_a
        # Record history
        for team, new_elo in [(home_team, self.ratings[home_team]), (away_team, self.ratings[away_team])]:
            if team not in self.history:
                self.history[team] = []
            self.history[team].append((date, new_elo))
        self.n_matches_processed += 1
        return delta_h, delta_a

    def fit(self, matches: pd.DataFrame) -> None:
        """
        Fit rolling Elo on a matches DataFrame.
        Accepts both raw martj42 (home_score/away_score) and
        normalized datasets (home_goals/away_goals).
        Processes in chronological order.
        """
        df = matches.sort_values("date").reset_index(drop=True)
        # Support both column naming conventions
        h_col = "home_goals" if "home_goals" in df.columns else "home_score"
        a_col = "away_goals" if "away_goals" in df.columns else "away_score"
        for _, row in df.iterrows():
            if pd.isna(row[h_col]) or pd.isna(row[a_col]):
                continue
            self.update(
                row["home_team"], row["away_team"],
                int(row[h_col]), int(row[a_col]),
                str(row["tournament"]), bool(row["neutral"]),
                str(row["date"]),
            )

    def get_pre_match_elo_diff(
        self, home_team: str, away_team: str, date: str, neutral: bool
    ) -> float:
        """
        Pre-match Elo difference for a specific match:
        elo_home - elo_away + home_advantage.
        Returns the adjusted Elo diff for use as a feature.
        """
        elo_h = self.get_elo(home_team, before_date=date)
        elo_a = self.get_elo(away_team, before_date=date)
        adj = 0.0 if neutral else _HOME_ADVANTAGE
        return (elo_h + adj) - elo_a

    def snapshot(self, teams: list[str]) -> dict[str, float]:
        """Return current Elo for a list of teams."""
        return {t: self._get_rating(t) for t in teams}
