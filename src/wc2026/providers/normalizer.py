"""Normalize raw provider data into consistent structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizedMatch:
    provider: str
    home: str
    away: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    date: str
    group: str = ""
    round: str = ""
    status: str = "SCHEDULED"  # FT / 1H / HT / 2H / ET / PEN / NS / SCHEDULED
    minute: Optional[int] = None
    venue: str = ""
    scorers_home: list[str] = field(default_factory=list)
    scorers_away: list[str] = field(default_factory=list)
    quality_level: str = "D"  # A/B/C/D
    source_timestamp: Optional[str] = None
    match_id: Optional[str] = None
    notes: str = ""

    @property
    def is_completed(self) -> bool:
        return self.status == "FT" and self.home_goals is not None

    @property
    def is_live(self) -> bool:
        return self.status in ("1H", "HT", "2H", "ET", "BT", "P")

    @property
    def home_goals_safe(self) -> int:
        return self.home_goals or 0

    @property
    def away_goals_safe(self) -> int:
        return self.away_goals or 0


@dataclass
class NormalizedStandings:
    team: str
    group: str
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    points: int
    provider: str
    quality_level: str = "C"


@dataclass
class NormalizedMatchStats:
    match_id: str
    provider: str
    home_team: str
    away_team: str
    possession_home: Optional[float] = None
    possession_away: Optional[float] = None
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None
    fouls_home: Optional[int] = None
    fouls_away: Optional[int] = None
    yellow_cards_home: Optional[int] = None
    yellow_cards_away: Optional[int] = None
    red_cards_home: Optional[int] = None
    red_cards_away: Optional[int] = None
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    quality_level: str = "D"

    def has_xg(self) -> bool:
        return self.xg_home is not None or self.xg_away is not None

    def has_shots(self) -> bool:
        return self.shots_home is not None

    def effective_quality(self) -> str:
        if self.has_xg():
            return "A"
        if self.has_shots():
            return "B"
        return "D"


def from_provider_dict(d: dict) -> NormalizedMatch:
    """Convert a raw provider dict to NormalizedMatch."""
    return NormalizedMatch(
        provider=d.get("provider", "unknown"),
        home=d.get("home", ""),
        away=d.get("away", ""),
        home_goals=d.get("home_goals"),
        away_goals=d.get("away_goals"),
        date=d.get("date", ""),
        group=d.get("group", ""),
        round=d.get("round", ""),
        status=d.get("status", "SCHEDULED"),
        minute=d.get("minute"),
        venue=d.get("venue", ""),
        scorers_home=d.get("scorers_home", []),
        scorers_away=d.get("scorers_away", []),
        quality_level=d.get("quality_level", "D"),
        source_timestamp=d.get("source_timestamp"),
        match_id=str(d["match_id"]) if d.get("match_id") else None,
        notes=d.get("notes", ""),
    )
