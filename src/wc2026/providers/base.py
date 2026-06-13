"""Base provider interface for WC2026 live data."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderStatus:
    name: str
    available: bool
    plan: str = "unknown"
    requests_used: Optional[int] = None
    requests_limit: Optional[int] = None
    wc2026_accessible: bool = False
    error: str = ""
    quality_level: str = "D"  # A/B/C/D


@dataclass
class RawProviderResponse:
    provider: str
    endpoint: str
    data: Any
    timestamp: str
    status_code: int = 200
    error: str = ""


class BaseProvider(ABC):
    name: str = "base"
    quality_level: str = "D"  # A=xG+full, B=shots+cards, C=score/min, D=stale

    @abstractmethod
    def get_status(self) -> ProviderStatus:
        """Check provider availability and plan."""
        ...

    @abstractmethod
    def get_live_matches(self) -> list[dict]:
        """Return currently live/in-play matches."""
        ...

    @abstractmethod
    def get_today_fixtures(self) -> list[dict]:
        """Return all fixtures for today (live + scheduled + finished)."""
        ...

    @abstractmethod
    def get_completed_matches(self, since_date: Optional[str] = None) -> list[dict]:
        """Return all completed WC2026 matches."""
        ...

    @abstractmethod
    def get_standings(self) -> list[dict]:
        """Return group standings."""
        ...

    def get_match_stats(self, match_id: Any) -> dict:
        """Return in-play or post-match statistics for a given match."""
        return {}

    def get_match_events(self, match_id: Any) -> list[dict]:
        """Return goals/cards/subs events for a given match."""
        return []

    def get_lineups(self, match_id: Any) -> list[dict]:
        """Return starting lineups for a given match."""
        return []

    def get_injuries(self) -> list[dict]:
        """Return current injury/availability data."""
        return []

    def get_odds(self, match_id: Any) -> dict:
        """Return pre-match or live odds if available."""
        return {}
