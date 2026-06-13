"""Circadian rhythm / jet lag performance penalty model."""
from __future__ import annotations

from dataclasses import dataclass

# UTC offsets for WC 2026 host cities (standard time, no DST)
STADIUM_UTC_OFFSET: dict[str, float] = {
    "New York":      -4.0,
    "Los Angeles":   -7.0,
    "Dallas":        -5.0,
    "San Francisco": -7.0,
    "Miami":         -4.0,
    "Seattle":       -7.0,
    "Boston":        -4.0,
    "Houston":       -5.0,
    "Philadelphia":  -4.0,
    "Kansas City":   -5.0,
    "Atlanta":       -4.0,
    "Mexico City":   -6.0,
    "Guadalajara":   -6.0,
    "Monterrey":     -6.0,
    "Toronto":       -4.0,
    "Vancouver":     -7.0,
}

# Approximate home UTC offset per confederation/nation
TEAM_HOME_UTC: dict[str, float] = {
    # Europe
    "ESP": 2.0, "FRA": 2.0, "ENG": 1.0, "GER": 2.0, "POR": 1.0,
    "NED": 2.0, "BEL": 2.0, "CRO": 2.0, "AUT": 2.0, "SCO": 1.0,
    "SUI": 2.0, "NOR": 2.0, "SWE": 2.0, "DEN": 2.0,
    # South America
    "ARG": -3.0, "BRA": -3.0, "COL": -5.0, "URU": -3.0, "ECU": -5.0,
    "PAR": -4.0, "CHL": -4.0,
    # North/Central America
    "USA": -5.0, "MEX": -6.0, "CAN": -4.0, "CRC": -6.0, "PAN": -5.0,
    "JAM": -5.0, "SLV": -6.0, "HAI": -5.0,
    # Africa
    "MAR": 1.0, "SEN": 0.0, "EGY": 2.0, "CIV": 0.0, "CMR": 1.0,
    "GHA": 0.0, "TUN": 1.0, "ALG": 1.0, "RSA": 2.0, "COD": 1.0,
    # Asia
    "JPN": 9.0, "KOR": 9.0, "IRN": 3.5, "AUS": 10.0, "KSA": 3.0,
    "QAT": 3.0, "UZB": 5.0, "JOR": 3.0, "IRQ": 3.0,
    # Europe East
    "CZE": 2.0, "TUR": 3.0, "BIH": 2.0, "CPV": -1.0,
    # Pacific/Other
    "NZL": 12.0, "CUW": -4.0,
}

OPTIMAL_KICKOFF_LOCAL = 15.0  # 3 PM local = optimal performance window
CIRCADIAN_PENALTY_SCALE = 0.004  # per hour of deviation from optimal window
JETLAG_DAYS_TO_RECOVER = 1.5    # days to fully adapt per timezone hour crossed


@dataclass
class JetLagPenalty:
    team_code: str
    venue_city: str
    timezone_delta: float      # hours crossed
    kickoff_utc: float         # 0-24
    kickoff_local_home: float  # kickoff in team's home timezone
    performance_factor: float  # multiplier on xG (0.90 – 1.00)


def compute_jet_lag(team_code: str, venue_city: str, kickoff_utc: float,
                    days_since_arrival: float = 3.0) -> JetLagPenalty:
    home_offset = TEAM_HOME_UTC.get(team_code, 0.0)
    venue_offset = STADIUM_UTC_OFFSET.get(venue_city, -5.0)
    tz_delta = abs(home_offset - venue_offset)
    kickoff_local_home = (kickoff_utc + home_offset) % 24

    # Circadian disruption: deviation from 15h local
    circadian_dev = abs(kickoff_local_home - OPTIMAL_KICKOFF_LOCAL)
    if circadian_dev > 12:
        circadian_dev = 24 - circadian_dev

    # Jet lag recovery: reduces with days since arrival
    recovery_ratio = min(1.0, days_since_arrival / (tz_delta * JETLAG_DAYS_TO_RECOVER + 1e-9))
    effective_tz_dev = tz_delta * (1.0 - recovery_ratio)

    penalty = CIRCADIAN_PENALTY_SCALE * (circadian_dev + 0.5 * effective_tz_dev)
    performance_factor = max(0.85, 1.0 - penalty)

    return JetLagPenalty(
        team_code=team_code,
        venue_city=venue_city,
        timezone_delta=round(tz_delta, 1),
        kickoff_utc=kickoff_utc,
        kickoff_local_home=round(kickoff_local_home, 1),
        performance_factor=round(performance_factor, 4),
    )


def worst_jet_lag_teams(venue_city: str, kickoff_utc: float = 21.0) -> list[JetLagPenalty]:
    results = [
        compute_jet_lag(code, venue_city, kickoff_utc)
        for code in TEAM_HOME_UTC
    ]
    return sorted(results, key=lambda x: x.performance_factor)
