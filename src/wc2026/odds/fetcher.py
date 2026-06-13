"""
The Odds API client — fetch WC 2026 tournament and match odds.

Modes:
  LIVE  — requires ODDS_API_KEY env var → real bookmaker data
  DEMO  — no key needed → synthetic odds from model summary.csv

The Odds API v4 docs: https://the-odds-api.com/liveapi/guides/v4/
Sport key for WC 2026: soccer_fifa_world_cup
Markets: h2h (1X2), outrights (tournament winner)
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CACHE_DIR = ROOT / "data" / "odds_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
WC_SPORT_KEY = "soccer_fifa_world_cup"


@dataclass
class MatchOdds:
    """H2H odds for a single match (1X2)."""
    match_id: str
    home_team: str           # full name as returned by API
    away_team: str
    home_code: str           # FIFA-3 code
    away_code: str
    commence_time: Optional[datetime]
    # bookmaker_key → {home_price, draw_price, away_price}
    bookmakers: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def best_home_odds(self) -> float:
        return max((b.get("home", 0) for b in self.bookmakers.values()), default=0.0)

    @property
    def best_draw_odds(self) -> float:
        return max((b.get("draw", 0) for b in self.bookmakers.values()), default=0.0)

    @property
    def best_away_odds(self) -> float:
        return max((b.get("away", 0) for b in self.bookmakers.values()), default=0.0)

    @property
    def consensus_odds(self) -> dict[str, float]:
        """Average odds across all bookmakers (consensus market)."""
        if not self.bookmakers:
            return {"home": 0.0, "draw": 0.0, "away": 0.0}
        keys = ["home", "draw", "away"]
        return {
            k: sum(b.get(k, 0) for b in self.bookmakers.values()) / len(self.bookmakers)
            for k in keys
        }


@dataclass
class OutrightOdds:
    """Tournament winner (outright) odds for all teams."""
    sport_key: str
    # team_code → {bookmaker_key → decimal_odds}
    teams: dict[str, dict[str, float]] = field(default_factory=dict)
    fetched_at: Optional[datetime] = None

    def consensus_odds(self, team_code: str) -> float:
        """Median odds for a team across all bookmakers."""
        bk = self.teams.get(team_code, {})
        if not bk:
            return 0.0
        vals = sorted(bk.values())
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    def best_odds(self, team_code: str) -> float:
        """Best (highest) decimal odds available for a team."""
        bk = self.teams.get(team_code, {})
        return max(bk.values(), default=0.0)

    def covered_teams(self) -> set[str]:
        return {c for c, bk in self.teams.items() if bk}


def _get_api_key() -> Optional[str]:
    return os.environ.get("ODDS_API_KEY") or os.environ.get("THE_ODDS_API_KEY")


def _fetch_json(url: str, params: dict, timeout: int = 15) -> dict | list:
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"
    req = urllib.request.Request(full_url, headers={"User-Agent": "wc2026-quant/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_outright_odds(
    api_key: Optional[str] = None,
    regions: str = "uk,eu,us",
    cache_ttl_minutes: int = 60,
) -> OutrightOdds:
    """
    Fetch WC 2026 tournament winner odds from The Odds API.
    Falls back to demo mode if no API key is available.
    """
    key = api_key or _get_api_key()
    if not key:
        return _demo_outright_odds()

    cache_file = CACHE_DIR / "outrights_latest.json"
    if cache_file.exists():
        age_minutes = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 60
        if age_minutes < cache_ttl_minutes:
            raw = json.loads(cache_file.read_text())
            return _parse_outright_response(raw)

    url = f"{ODDS_API_BASE}/sports/{WC_SPORT_KEY}/outrights/"
    params = {"apiKey": key, "regions": regions, "oddsFormat": "decimal"}
    raw = _fetch_json(url, params)

    cache_file.write_text(json.dumps(raw, indent=2))
    return _parse_outright_response(raw)


def fetch_match_odds(
    api_key: Optional[str] = None,
    regions: str = "uk,eu,us",
    cache_ttl_minutes: int = 30,
) -> list[MatchOdds]:
    """
    Fetch H2H (1X2) odds for all upcoming WC 2026 matches.
    Falls back to demo mode if no API key is available.
    """
    key = api_key or _get_api_key()
    if not key:
        return _demo_match_odds()

    cache_file = CACHE_DIR / "matches_latest.json"
    if cache_file.exists():
        age_minutes = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 60
        if age_minutes < cache_ttl_minutes:
            raw = json.loads(cache_file.read_text())
            return _parse_match_response(raw)

    url = f"{ODDS_API_BASE}/sports/{WC_SPORT_KEY}/odds/"
    params = {
        "apiKey": key,
        "regions": regions,
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    raw = _fetch_json(url, params)

    cache_file.write_text(json.dumps(raw, indent=2))
    return _parse_match_response(raw)


def _parse_outright_response(raw: list) -> OutrightOdds:
    """Parse The Odds API outrights response into OutrightOdds."""
    from wc2026.name_map import to_code

    result = OutrightOdds(sport_key=WC_SPORT_KEY, fetched_at=datetime.now())
    for event in raw:
        for bk in event.get("bookmakers", []):
            bk_key = bk["key"]
            for market in bk.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = float(outcome.get("price", 0))
                    if price <= 1.0:
                        continue
                    try:
                        code = to_code(name)
                    except ValueError:
                        continue
                    result.teams.setdefault(code, {})[bk_key] = price
    return result


def _parse_match_response(raw: list) -> list[MatchOdds]:
    """Parse The Odds API h2h response into MatchOdds list."""
    from wc2026.name_map import to_code

    matches = []
    for event in raw:
        home_name = event.get("home_team", "")
        away_name = event.get("away_team", "")
        try:
            home_code = to_code(home_name)
            away_code = to_code(away_name)
        except ValueError:
            continue

        t_str = event.get("commence_time", "")
        try:
            commence = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            commence = None

        mo = MatchOdds(
            match_id=event.get("id", ""),
            home_team=home_name,
            away_team=away_name,
            home_code=home_code,
            away_code=away_code,
            commence_time=commence,
        )

        for bk in event.get("bookmakers", []):
            bk_key = bk["key"]
            for market in bk.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                prices = {}
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = float(outcome.get("price", 0))
                    if name == home_name:
                        prices["home"] = price
                    elif name == away_name:
                        prices["away"] = price
                    elif name == "Draw":
                        prices["draw"] = price
                if prices:
                    mo.bookmakers[bk_key] = prices

        matches.append(mo)
    return matches


# =============================================================================
# Demo / synthetic mode
# =============================================================================

def _demo_outright_odds(seed: int = 20260611) -> OutrightOdds:
    """
    Generate synthetic tournament winner odds from the model's summary.csv.

    Realistic simulation:
    - Base overround: 12% (typical for outright winner markets)
    - Bookmaker biases: favorites slightly over-rounded (shorter odds than fair),
      selected underdogs mis-priced by ±15% to create visible value bets in demo
    - 3 bookmakers with different biases so best_odds meaningfully beats consensus
    """
    import numpy as np

    summary_path = ROOT / "outputs" / "tournament_run" / "summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(
            "Run the tournament simulation first: python3 -m wc2026.cli simulate-tournament"
        )

    import pandas as pd
    df = pd.read_csv(summary_path).reset_index(drop=True)
    n = len(df)
    rng = np.random.default_rng(seed)

    # Structured bias: reflect real bookmaker inefficiencies
    # 1. Top-6 favourites: market overvalues them → odds too short → negative edge for bettor
    # 2. Randomly selected mid-tier teams: mis-priced ±15-20% → value bets appear
    top6_idx = df.nlargest(6, "champion_prob").index.tolist()
    biases = np.zeros(n)
    biases[top6_idx] = rng.uniform(0.08, 0.15, len(top6_idx))   # top teams over-rounded by 8-15%

    # Pick 6 random mid-tier teams to under-round (potential value bets)
    mid_idx = df[~df.index.isin(top6_idx)].nlargest(20, "champion_prob").sample(6, random_state=seed).index.tolist()
    biases[mid_idx] = rng.uniform(-0.15, -0.08, len(mid_idx))   # under-priced by 8-15%

    # Add per-bookmaker noise on top of biases
    bk_configs = {
        "bet365_synthetic":  (biases + rng.normal(0, 0.04, n), 1.12),
        "pinnacle_synthetic": (biases * 0.7 + rng.normal(0, 0.02, n), 1.08),  # tighter market
        "betfair_synthetic":  (biases * 1.2 + rng.normal(0, 0.06, n), 1.15),  # looser market
    }

    result = OutrightOdds(sport_key=WC_SPORT_KEY, fetched_at=datetime.now())

    for bk_key, (total_bias, overround) in bk_configs.items():
        # Apply bias: positive bias → worse odds (overpriced for bettor)
        raw_probs = df["champion_prob"].values * (1 + total_bias)
        raw_probs = np.maximum(raw_probs, 1e-5)
        # Scale to desired overround
        implied = raw_probs / raw_probs.sum() * overround
        decimal = np.round(1.0 / implied, 2)

        for i, row in df.iterrows():
            code = row["team"]
            result.teams.setdefault(code, {})[bk_key] = float(decimal[i])

    return result


def _demo_match_odds() -> list[MatchOdds]:
    """
    Generate synthetic H2H odds for WC 2026 group matches from model match probs.
    Uses Dixon-Coles Poisson model to derive match-level probabilities.
    """
    import numpy as np
    from wc2026.data_loader import load_teams, load_groups, load_config
    from wc2026.match_model import MatchModel
    from wc2026.constants import GROUP_MATCH_TEMPLATE
    from wc2026.name_map import CODE_TO_NAME

    config = load_config()
    teams = load_teams()
    groups = load_groups()
    model = MatchModel(config)
    rng = np.random.default_rng(20260611)

    ITERATIONS = 5000
    matches = []

    for grp_name, codes in groups.items():
        for left_pos, right_pos in GROUP_MATCH_TEMPLATE:
            home_code = codes[int(left_pos) - 1]
            away_code = codes[int(right_pos) - 1]
            home_team = teams[home_code]
            away_team = teams[away_code]

            # Simulate N times to get H/D/A probs
            home_wins = draws = away_wins = 0
            for _ in range(ITERATIONS):
                res = model.simulate_group_match(home_team, away_team, rng)
                if res.goals_a > res.goals_b:
                    home_wins += 1
                elif res.goals_a == res.goals_b:
                    draws += 1
                else:
                    away_wins += 1

            p_h = home_wins / ITERATIONS
            p_d = draws / ITERATIONS
            p_a = away_wins / ITERATIONS

            # Synthetic bookmaker: 7% overround, small noise
            overround = 1.07
            noise = rng.normal(0, 0.02, 3)
            raw = np.array([p_h, p_d, p_a]) * (1 + noise)
            raw = np.maximum(raw, 0.02)
            implied = raw / raw.sum() * overround
            dec = np.round(1.0 / implied, 2)

            home_name = CODE_TO_NAME.get(home_code, home_code)
            away_name = CODE_TO_NAME.get(away_code, away_code)
            mo = MatchOdds(
                match_id=f"{home_code}v{away_code}",
                home_team=home_name,
                away_team=away_name,
                home_code=home_code,
                away_code=away_code,
                commence_time=None,
                bookmakers={
                    "consensus": {
                        "home": float(dec[0]),
                        "draw": float(dec[1]),
                        "away": float(dec[2]),
                    }
                },
            )
            matches.append(mo)

    return matches
