"""
StatsBomb open data loader: WC 2022 (season 106) + WC 2018 (season 3).

Loads per-team match DataFrames for style extraction.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

warnings.filterwarnings("ignore")

COMPETITION_ID = 43  # FIFA World Cup
WC2022_SEASON = 106
WC2018_SEASON = 3

# StatsBomb team name → FIFA-3 code
SB_NAME_TO_CODE: dict[str, str] = {
    "Argentina": "ARG", "Australia": "AUS", "Belgium": "BEL",
    "Brazil": "BRA", "Cameroon": "CMR", "Canada": "CAN",
    "Costa Rica": "CRC", "Croatia": "CRO", "Denmark": "DEN",
    "Ecuador": "ECU", "England": "ENG", "France": "FRA",
    "Germany": "GER", "Ghana": "GHA", "Iran": "IRN",
    "Japan": "JPN", "Mexico": "MEX", "Morocco": "MAR",
    "Netherlands": "NED", "Poland": "POL", "Portugal": "POR",
    "Qatar": "QAT", "Saudi Arabia": "KSA", "Senegal": "SEN",
    "Serbia": "SRB", "South Korea": "KOR", "Spain": "ESP",
    "Switzerland": "SUI", "Tunisia": "TUN", "United States": "USA",
    "Uruguay": "URU", "Wales": "WAL",
    # WC 2018
    "Colombia": "COL", "Iceland": "ISL", "Nigeria": "NGA",
    "Panama": "PAN", "Peru": "PER", "Russia": "RUS",
    "Sweden": "SWE", "Egypt": "EGY", "Costa Rica": "CRC",
    "Uzbekistan": "UZB", "Austria": "AUT", "Norway": "NOR",
    "Scotland": "SCO", "Algeria": "ALG", "Jordan": "JOR",
    "South Africa": "RSA", "Czech Republic": "CZE", "Turkey": "TUR",
    "Côte d'Ivoire": "CIV", "Curaçao": "CUW", "Cape Verde": "CPV",
    "DR Congo": "COD", "Haiti": "HAI", "New Zealand": "NZL",
    "Paraguay": "PAR", "Bosnia and Herzegovina": "BIH",
    "United States": "USA", "Iraq": "IRQ",
}


@dataclass
class TeamMatchEvents:
    team_code: str
    season_id: int
    match_ids: list[int] = field(default_factory=list)
    # Accumulated event DataFrames across all matches
    shots: pd.DataFrame = field(default_factory=pd.DataFrame)
    passes_for: pd.DataFrame = field(default_factory=pd.DataFrame)
    passes_against: pd.DataFrame = field(default_factory=pd.DataFrame)
    shots_against: pd.DataFrame = field(default_factory=pd.DataFrame)  # opponent shots on team
    pressures: pd.DataFrame = field(default_factory=pd.DataFrame)
    # Comeback/choke counters — computed inline to avoid storing full match event DFs
    comeback_opps: int = 0    # games where team was trailing at some point
    comebacks: int = 0        # of those, games team drew or won
    choke_opps: int = 0       # games where team was leading at some point
    chokes: int = 0           # of those, games team drew or lost

    @property
    def n_matches(self) -> int:
        return len(self.match_ids)


def _sb_import():
    try:
        from statsbombpy import sb
        return sb
    except ImportError:
        raise RuntimeError("statsbombpy not installed — run: pip install statsbombpy")


def load_matches(season_id: int) -> pd.DataFrame:
    sb = _sb_import()
    return sb.matches(competition_id=COMPETITION_ID, season_id=season_id)


def load_events_for_match(match_id: int) -> pd.DataFrame:
    sb = _sb_import()
    return sb.events(match_id=match_id)


def _team_code(name: str) -> Optional[str]:
    return SB_NAME_TO_CODE.get(name)


def load_all_team_events(
    seasons: list[int] = (WC2022_SEASON, WC2018_SEASON),
    max_matches: Optional[int] = None,
) -> dict[str, TeamMatchEvents]:
    """
    Load all WC events for the given seasons.
    Returns {fifa3_code: TeamMatchEvents}.
    max_matches: cap per season for testing (None = all).
    """
    sb = _sb_import()
    team_data: dict[str, TeamMatchEvents] = {}

    for season_id in seasons:
        matches_df = load_matches(season_id)
        match_list = matches_df["match_id"].tolist()
        if max_matches is not None:
            match_list = match_list[:max_matches]

        for match_id in match_list:
            events = load_events_for_match(match_id)
            row = matches_df[matches_df["match_id"] == match_id].iloc[0]
            home_name = row["home_team"]
            away_name = row["away_team"]
            home_code = _team_code(home_name)
            away_code = _team_code(away_name)

            for team_name, team_code, opp_code in [
                (home_name, home_code, away_code),
                (away_name, away_code, home_code),
            ]:
                if team_code is None:
                    continue
                if team_code not in team_data:
                    team_data[team_code] = TeamMatchEvents(
                        team_code=team_code, season_id=season_id
                    )
                tme = team_data[team_code]
                tme.match_ids.append(match_id)

                # Shots by this team
                team_shots = events[
                    (events["type"] == "Shot") &
                    (events["team"] == team_name)
                ]
                if len(team_shots) > 0:
                    tme.shots = pd.concat([tme.shots, team_shots], ignore_index=True)

                # Passes by this team
                team_passes = events[
                    (events["type"] == "Pass") &
                    (events["team"] == team_name)
                ]
                if len(team_passes) > 0:
                    tme.passes_for = pd.concat(
                        [tme.passes_for, team_passes], ignore_index=True
                    )

                # Opponent passes (needed for PPDA)
                opp_passes = events[
                    (events["type"] == "Pass") &
                    (events["team"] != team_name) &
                    (events["team"].notna())
                ]
                if len(opp_passes) > 0:
                    tme.passes_against = pd.concat(
                        [tme.passes_against, opp_passes], ignore_index=True
                    )

                # Pressures by this team
                team_pressures = events[
                    (events["type"] == "Pressure") &
                    (events["team"] == team_name)
                ]
                if len(team_pressures) > 0:
                    tme.pressures = pd.concat(
                        [tme.pressures, team_pressures], ignore_index=True
                    )

                # Opponent shots (for shots_conceded_per_game — correct metric)
                opp_shots = events[
                    (events["type"] == "Shot") &
                    (events["team"] != team_name) &
                    (events["team"].notna())
                ]
                if len(opp_shots) > 0:
                    tme.shots_against = pd.concat(
                        [tme.shots_against, opp_shots], ignore_index=True
                    )

                # Comeback/choke: compute inline per match to avoid storing full event DFs
                goals = events[events["type"] == "Shot"].copy()
                if "shot_outcome" in goals.columns:
                    goals = goals[goals["shot_outcome"].apply(
                        lambda x: x == "Goal" if isinstance(x, str) else
                        (x.get("name") == "Goal" if isinstance(x, dict) else False)
                    )]
                    team_goals_min = goals[goals["team"] == team_name]["minute"].tolist()
                    opp_goals_min = goals[goals["team"] != team_name]["minute"].tolist()
                    all_evts = sorted(
                        [(m, "team") for m in team_goals_min] +
                        [(m, "opp") for m in opp_goals_min]
                    )
                    s_t, s_o = 0, 0
                    was_trailing, was_leading = False, False
                    for _m, scorer in all_evts:
                        if scorer == "team":
                            s_t += 1
                        else:
                            s_o += 1
                        if s_t < s_o:
                            was_trailing = True
                        if s_t > s_o:
                            was_leading = True
                    final = "win" if s_t > s_o else ("draw" if s_t == s_o else "loss")
                    if was_trailing:
                        tme.comeback_opps += 1
                        if final in ("win", "draw"):
                            tme.comebacks += 1
                    if was_leading:
                        tme.choke_opps += 1
                        if final in ("loss", "draw"):
                            tme.chokes += 1

    return team_data
