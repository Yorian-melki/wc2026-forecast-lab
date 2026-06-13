"""
Elo ratings engine: fetch eloratings.net World.tsv for all 48 WC 2026 teams.

Column layout (0-indexed):
  0  rank
  1  prev_rank
  2  code2 (eloratings own 2-letter code)
  3  elo_current
  4  rank_1yr_peak
  5  elo_1yr_peak
  6  rank_5yr_ago
  7  elo_5yr_ago
  8  rank_10yr_ago
  9  elo_10yr_ago
  10 d_1m_rank  11 d_1m_elo
  12 d_3m_rank  13 d_3m_elo
  14 d_6m_rank  15 d_6m_elo
  16 d_1yr_rank 17 d_1yr_elo
  18 d_2yr_rank 19 d_2yr_elo
  20 d_5yr_rank 21 d_5yr_elo
  22 total_matches 23 wins 24 draws 25 losses
  26..30 home/away breakdown
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ELO_URL = "https://www.eloratings.net/World.tsv"

# FIFA-3 → eloratings 2-letter code.
# eloratings uses its own system (not ISO 3166-1 alpha-2 for all nations).
# Verified empirically by cross-referencing Elo values with known FIFA rankings.
FIFA3_TO_ELO2: dict[str, str] = {
    # Group A
    "MEX": "MX", "RSA": "ZA", "KOR": "KR", "CZE": "CZ",
    # Group B
    "CAN": "CA", "BIH": "BA", "QAT": "QA", "SUI": "CH",
    # Group C
    "BRA": "BR", "MAR": "MA", "HAI": "HT", "SCO": "SQ",  # SC=Seychelles, SQ=Scotland
    # Group D
    "USA": "US", "PAR": "PY", "AUS": "AU", "TUR": "TR",
    # Group E
    "GER": "DE", "CUW": "CW", "CIV": "CI", "ECU": "EC",
    # Group F
    "NED": "NL", "JPN": "JP", "SWE": "SE", "TUN": "TN",
    # Group G
    "BEL": "BE", "EGY": "EG", "IRN": "IR", "NZL": "NZ",
    # Group H
    "ESP": "ES", "CPV": "CV", "KSA": "SA", "URU": "UY",
    # Group I
    "FRA": "FR", "SEN": "SN", "IRQ": "IQ", "NOR": "NO",
    # Group J
    "ARG": "AR", "ALG": "DZ", "AUT": "AT", "JOR": "JO",
    # Group K
    "POR": "PT", "COD": "CD", "UZB": "UZ", "COL": "CO",
    # Group L
    "ENG": "EN", "CRO": "HR", "GHA": "GH", "PAN": "PA",
}

ELO2_TO_FIFA3: dict[str, str] = {v: k for k, v in FIFA3_TO_ELO2.items()}


@dataclass
class EloRecord:
    fifa3: str
    elo2: str
    elo_current: int
    elo_5yr_ago: int       # ~June 2021 (closest proxy for pre-WC2022)
    d_1m: int
    d_3m: int
    d_6m: int
    d_1yr: int
    d_2yr: int
    d_5yr: int
    total_matches: int
    wins: int
    draws: int
    losses: int

    @property
    def win_rate(self) -> float:
        if self.total_matches == 0:
            return 0.5
        return self.wins / self.total_matches

    @property
    def elo_wc2022_approx(self) -> int:
        """
        Best proxy for pre-WC2022 Elo.
        d_2yr = Elo gained in last 2 years (Jun2024→Jun2026).
        elo_current - d_2yr ≈ Jun2024 Elo (~1.5yr post-WC2022).
        This is the closest computable proxy without a historical feed.
        Teams that won WC2022 (ARG) or ran deep will show lower 'approx' values
        because their d_2yr captures the WC2022 Elo boost.
        """
        return self.elo_current - self.d_2yr

    @property
    def form_momentum(self) -> float:
        """
        Recent-form score ∈ [-1, 1]:
        +1 = strongly rising (d1yr +200), -1 = strongly falling.
        """
        return max(-1.0, min(1.0, self.d_1yr / 200.0))

    @property
    def form_score(self) -> float:
        """Map Elo delta momentum to [0, 100] form score."""
        return round(50.0 + 50.0 * self.form_momentum, 1)


def _parse_int(s: str) -> int:
    """Parse eloratings signed integers: '+134', '−26', '1991'."""
    return int(s.replace("−", "-").replace("–", "-").replace("+", "").strip())


def fetch_elo_data(
    url: str = ELO_URL,
    timeout: int = 15,
    cache_path: Optional[Path] = None,
) -> dict[str, EloRecord]:
    """
    Fetch World.tsv and return {fifa3: EloRecord} for all 48 WC 2026 teams.
    If cache_path is set and the file exists, load from disk instead.
    """
    if cache_path and Path(cache_path).exists():
        raw = Path(cache_path).read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "wc2026-quant/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        if cache_path:
            Path(cache_path).write_text(raw, encoding="utf-8")

    elo2_map: dict[str, list[str]] = {}
    for line in raw.strip().split("\n"):
        cols = line.split("\t")
        if len(cols) < 26:
            continue
        elo2_map[cols[2]] = cols

    records: dict[str, EloRecord] = {}
    missing = []
    for fifa3, elo2 in FIFA3_TO_ELO2.items():
        if elo2 not in elo2_map:
            missing.append((fifa3, elo2))
            continue
        c = elo2_map[elo2]
        try:
            rec = EloRecord(
                fifa3=fifa3,
                elo2=elo2,
                elo_current=_parse_int(c[3]),
                elo_5yr_ago=_parse_int(c[7]),
                d_1m=_parse_int(c[11]),
                d_3m=_parse_int(c[13]),
                d_6m=_parse_int(c[15]),
                d_1yr=_parse_int(c[17]),
                d_2yr=_parse_int(c[19]),
                d_5yr=_parse_int(c[21]),
                total_matches=_parse_int(c[22]),
                wins=_parse_int(c[23]),
                draws=_parse_int(c[24]),
                losses=_parse_int(c[25]),
            )
            records[fifa3] = rec
        except (IndexError, ValueError) as e:
            missing.append((fifa3, elo2))

    if missing:
        raise RuntimeError(f"EloEngine: failed to load {len(missing)} teams: {missing}")

    return records


def elo_to_form(elo_current: int, d_1yr: int) -> float:
    """
    Convert raw Elo + 1-year delta into a [0, 100] form score.
    Absolute Elo anchors the midpoint; delta adds/subtracts up to ±20 pts.
    """
    # Normalise Elo to [0,100]: 1400=0, 2200=100
    elo_norm = max(0.0, min(100.0, (elo_current - 1400) / 8.0))
    # Delta momentum ∈ [-20, +20]
    delta_bonus = max(-20.0, min(20.0, d_1yr / 10.0))
    return round(max(0.0, min(100.0, elo_norm + delta_bonus)), 1)
