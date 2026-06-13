"""
WC 2022 backtest: train on pre-2022 ratings, simulate WC 2022, compute Brier score.

Methodology:
  - Team ratings: current Elo + d_5yr interpolated to ~Nov 2022 (see elo_engine.elo_wc2022_approx)
  - Groups: hardcoded WC 2022 group draw
  - 100 000 Monte Carlo simulations
  - Brier score at 3 thresholds: group survival, quarterfinal, champion

Brier score B = (1/N) × Σ(p_i - o_i)²
  Lower is better. Random model = 0.25 (for binary events).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = ROOT / "data"

# WC 2022 group stage draw
WC2022_GROUPS: dict[str, list[str]] = {
    "A": ["QAT", "ECU", "SEN", "NED"],
    "B": ["ENG", "IRN", "USA", "WAL"],
    "C": ["ARG", "KSA", "MEX", "POL"],
    "D": ["FRA", "AUS", "DEN", "TUN"],
    "E": ["ESP", "CRC", "GER", "JPN"],
    "F": ["BEL", "CAN", "MAR", "CRO"],
    "G": ["BRA", "SRB", "SUI", "CMR"],
    "H": ["POR", "GHA", "URU", "KOR"],
}

# All 32 WC 2022 teams (for full Brier score denominator)
WC2022_ALL_TEAMS: set[str] = {
    "QAT", "ECU", "SEN", "NED",
    "ENG", "IRN", "USA", "WAL",
    "ARG", "KSA", "MEX", "POL",
    "FRA", "AUS", "DEN", "TUN",
    "ESP", "CRC", "GER", "JPN",
    "BEL", "CAN", "MAR", "CRO",
    "BRA", "SRB", "SUI", "CMR",
    "POR", "GHA", "URU", "KOR",
}

# Positive sets (teams that reached each stage)
WC2022_GROUP_SURVIVORS: set[str] = {
    "NED", "SEN", "ENG", "USA",
    "ARG", "POL", "FRA", "AUS",
    "ESP", "JPN", "MAR", "CRO",
    "BRA", "SUI", "POR", "KOR",
}

WC2022_QUARTERFINALISTS: set[str] = {
    "ARG", "NED", "ENG", "FRA",
    "CRO", "BRA", "MAR", "POR",
}

WC2022_SEMIFINALISTS: set[str] = {"ARG", "FRA", "CRO", "MAR"}

WC2022_CHAMPION: set[str] = {"ARG"}

# Teams in WC 2022 but NOT in current WC 2026 teams.csv
WC2022_ONLY_TEAMS = {
    "WAL", "POL", "DEN", "CRC", "SRB", "CMR", "ECU",  # note: ECU IS in 2026
}

# Default Elo for WC 2022-only teams (manually set from historical records)
WC2022_FALLBACK_ELO: dict[str, int] = {
    "WAL": 1682,   # Wales, Elo ~1680 pre-WC2022
    "POL": 1710,   # Poland, ~1710
    "DEN": 1840,   # Denmark had strong form in 2021, ~1840 before WC2022
    "CRC": 1620,   # Costa Rica, ~1620
    "SRB": 1750,   # Serbia, ~1750
    "CMR": 1620,   # Cameroon, ~1620
}


@dataclass
class BrierResult:
    n_teams: int
    brier_group_survival: float
    brier_quarterfinal: float
    brier_semifinal: float
    brier_champion: float
    model_champion: str        # team with highest champion probability
    model_champion_prob: float
    actual_champion: str = "ARG"

    def __str__(self) -> str:
        lines = [
            "=" * 50,
            "WC 2022 BACKTEST RESULTS",
            "=" * 50,
            f"Teams evaluated:          {self.n_teams}",
            f"Brier (group survival):   {self.brier_group_survival:.4f}  "
            f"[random baseline=0.250]",
            f"Brier (quarterfinal):     {self.brier_quarterfinal:.4f}",
            f"Brier (semifinal):        {self.brier_semifinal:.4f}",
            f"Brier (champion):         {self.brier_champion:.4f}",
            f"Model top pick:           {self.model_champion} "
            f"({self.model_champion_prob*100:.2f}%)",
            f"Actual champion:          {self.actual_champion}",
            "=" * 50,
        ]
        return "\n".join(lines)


def _brier_score(
    probs: dict[str, float],
    positive_set: set[str],
    all_teams: set[str],
) -> float:
    """
    Proper Brier score: B = (1/N) * Σ(p_i - o_i)² over ALL teams.
    o_i = 1 if team in positive_set, else 0.
    """
    squares = []
    for team in all_teams:
        p = probs.get(team, 0.0)
        o = 1 if team in positive_set else 0
        squares.append((p - o) ** 2)
    return float(np.mean(squares)) if squares else 1.0


def _build_wc2022_teams(elo_snapshot_path: Path) -> dict:
    """
    Build a minimal teams dict for WC 2022 simulation.
    Uses Elo from elo_wc2022 column (interpolated) where available,
    falls back to WC2022_FALLBACK_ELO for WC2022-only teams.
    """
    from wc2026.data_loader import Team

    elo_df = pd.read_csv(elo_snapshot_path).set_index("code")
    teams_df = pd.read_csv(DATA_DIR / "teams.csv").set_index("code")

    all_codes = {code for grp in WC2022_GROUPS.values() for code in grp}
    teams: dict[str, Team] = {}

    for code in all_codes:
        if code in teams_df.index:
            row = teams_df.loc[code]
            # Get historical Elo
            if code in elo_df.index:
                elo22 = int(elo_df.loc[code, "elo_wc2022"])
            else:
                elo22 = WC2022_FALLBACK_ELO.get(code, 1700)

            # Scale latent dimensions proportionally to Elo ratio
            elo_current = elo_df.loc[code, "elo_current"] if code in elo_df.index else 1750
            scale = elo22 / elo_current if elo_current > 0 else 1.0

            def scaled(val, s=scale):
                return max(0.0, min(100.0, float(val) * s))

            teams[code] = Team(
                code=code,
                name=str(row.get("name", code)),
                group="",
                fifa_rank=int(row.get("fifa_rank", 30)),
                attack=scaled(row.get("attack", 75)),
                defense=scaled(row.get("defense", 75)),
                midfield=scaled(row.get("midfield", 75)),
                transition=scaled(row.get("transition", 75)),
                setpiece=scaled(row.get("setpiece", 75)),
                goalkeeper=scaled(row.get("goalkeeper", 75)),
                depth=scaled(row.get("depth", 75)),
                coach=scaled(row.get("coach", 75)),
                penalties=scaled(row.get("penalties", 75)),
                discipline=scaled(row.get("discipline", 75)),
                health=scaled(row.get("health", 75)),
                form=scaled(row.get("form", 75)),
                climate_resilience=scaled(row.get("climate_resilience", 75)),
                altitude_resilience=scaled(row.get("altitude_resilience", 75)),
                travel_resilience=scaled(row.get("travel_resilience", 75)),
            )
        elif code in WC2022_FALLBACK_ELO:
            elo22 = WC2022_FALLBACK_ELO[code]
            base = max(0.0, min(100.0, (elo22 - 1400) / 8.0))
            teams[code] = Team(
                code=code, name=code, group="",
                fifa_rank=40,
                attack=base, defense=base, midfield=base, transition=base,
                setpiece=base, goalkeeper=base, depth=base, coach=base,
                penalties=base, discipline=75.0, health=90.0, form=base,
                climate_resilience=75.0, altitude_resilience=75.0,
                travel_resilience=75.0,
            )
        else:
            # Unknown team: use league-average stats
            teams[code] = Team(
                code=code, name=code, group="",
                fifa_rank=50,
                attack=60.0, defense=60.0, midfield=60.0, transition=60.0,
                setpiece=60.0, goalkeeper=60.0, depth=60.0, coach=60.0,
                penalties=60.0, discipline=75.0, health=90.0, form=60.0,
                climate_resilience=75.0, altitude_resilience=75.0,
                travel_resilience=75.0,
            )

    return teams


def run_wc2022_backtest(
    iterations: int = 100_000,
    seed: int = 20220620,
    save_path: Optional[Path] = None,
) -> BrierResult:
    """
    Simulate WC 2022 from pre-tournament ratings and compare to actual results.
    Returns BrierResult with Brier scores at multiple thresholds.
    """
    from wc2026.data_loader import load_config
    from wc2026.match_model import MatchModel
    from wc2026.group_rules import simulate_group

    elo_path = DATA_DIR / "elo_snapshot.csv"
    if not elo_path.exists():
        raise FileNotFoundError(
            "elo_snapshot.csv not found — run form_engine.run_form_pipeline() first"
        )

    config = load_config()
    teams = _build_wc2022_teams(elo_path)
    model = MatchModel(config)

    print(f"[backtest] Running WC 2022 backtest: {iterations:,} iterations...")

    # Accumulators: team → count reaching each stage
    n_group = {t: 0 for t in teams}
    n_qf = {t: 0 for t in teams}
    n_sf = {t: 0 for t in teams}
    n_champion = {t: 0 for t in teams}

    rng = np.random.default_rng(seed)

    for _ in range(iterations):
        # Group stage
        group_qualifiers: list[tuple[str, str]] = []  # (1st, 2nd) per group
        for grp_name, codes in WC2022_GROUPS.items():
            for c in codes:
                if c not in teams:
                    # Skip if team not in our teams dict (shouldn't happen)
                    continue
            table, matches, order = simulate_group(grp_name, codes, teams, model, rng)
            q1, q2 = order[0], order[1]
            group_qualifiers.append((q1, q2))
            n_group[q1] += 1
            n_group[q2] += 1

        # KO bracket: 16 teams in R16 → QF → SF → F
        # R16 pairs: 1A vs 2B, 1B vs 2A, 1C vs 2D, 1D vs 2C, ...
        r16_pairs = [
            (group_qualifiers[0][0], group_qualifiers[1][1]),  # 1A vs 2B
            (group_qualifiers[2][0], group_qualifiers[3][1]),  # 1C vs 2D
            (group_qualifiers[4][0], group_qualifiers[5][1]),  # 1E vs 2F
            (group_qualifiers[6][0], group_qualifiers[7][1]),  # 1G vs 2H
            (group_qualifiers[1][0], group_qualifiers[0][1]),  # 1B vs 2A
            (group_qualifiers[3][0], group_qualifiers[2][1]),  # 1D vs 2C
            (group_qualifiers[5][0], group_qualifiers[4][1]),  # 1F vs 2E
            (group_qualifiers[7][0], group_qualifiers[6][1]),  # 1H vs 2G
        ]

        # R16 → QF
        qf_teams = []
        for t1, t2 in r16_pairs:
            if t1 not in teams or t2 not in teams:
                continue
            res = model.simulate_knockout_match(teams[t1], teams[t2], rng)
            winner = t1 if res.goals_a >= res.goals_b else t2
            if res.goals_a == res.goals_b:
                # Penalties
                winner = t1 if rng.random() < (teams[t1].penalties / (teams[t1].penalties + teams[t2].penalties)) else t2
            qf_teams.append(winner)
            n_qf[winner] += 1

        # QF → SF
        sf_teams = []
        for i in range(0, len(qf_teams), 2):
            if i + 1 >= len(qf_teams):
                break
            t1, t2 = qf_teams[i], qf_teams[i + 1]
            res = model.simulate_knockout_match(teams[t1], teams[t2], rng)
            winner = t1 if res.goals_a >= res.goals_b else t2
            if res.goals_a == res.goals_b:
                winner = t1 if rng.random() < (teams[t1].penalties / (teams[t1].penalties + teams[t2].penalties)) else t2
            sf_teams.append(winner)
            n_sf[winner] += 1

        # SF → Final
        if len(sf_teams) >= 2:
            t1, t2 = sf_teams[0], sf_teams[1]
            res = model.simulate_knockout_match(teams[t1], teams[t2], rng)
            winner = t1 if res.goals_a >= res.goals_b else t2
            if res.goals_a == res.goals_b:
                winner = t1 if rng.random() < (teams[t1].penalties / (teams[t1].penalties + teams[t2].penalties)) else t2
            if len(sf_teams) >= 4:
                t3, t4 = sf_teams[2], sf_teams[3]
                res2 = model.simulate_knockout_match(teams[t3], teams[t4], rng)
                finalist2 = t3 if res2.goals_a >= res2.goals_b else t4
                if res2.goals_a == res2.goals_b:
                    finalist2 = t3 if rng.random() < (teams[t3].penalties / (teams[t3].penalties + teams[t4].penalties)) else t4
                # Final
                res_f = model.simulate_knockout_match(teams[winner], teams[finalist2], rng)
                champion = winner if res_f.goals_a >= res_f.goals_b else finalist2
                if res_f.goals_a == res_f.goals_b:
                    champion = winner if rng.random() < (teams[winner].penalties / (teams[winner].penalties + teams[finalist2].penalties)) else finalist2
                n_champion[champion] += 1

    # Convert counts to probabilities
    n = iterations
    prob_group = {t: n_group[t] / n for t in teams}
    prob_qf = {t: n_qf[t] / n for t in teams}
    prob_sf = {t: n_sf[t] / n for t in teams}
    prob_champion = {t: n_champion[t] / n for t in teams}

    brier_group = _brier_score(prob_group, WC2022_GROUP_SURVIVORS, WC2022_ALL_TEAMS)
    brier_qf = _brier_score(prob_qf, WC2022_QUARTERFINALISTS, WC2022_ALL_TEAMS)
    brier_sf = _brier_score(prob_sf, WC2022_SEMIFINALISTS, WC2022_ALL_TEAMS)
    brier_champ = _brier_score(prob_champion, WC2022_CHAMPION, WC2022_ALL_TEAMS)

    # Model's top pick
    model_champion = max(prob_champion, key=prob_champion.get)
    model_champion_prob = prob_champion[model_champion]

    result = BrierResult(
        n_teams=len(teams),
        brier_group_survival=round(brier_group, 5),
        brier_quarterfinal=round(brier_qf, 5),
        brier_semifinal=round(brier_sf, 5),
        brier_champion=round(brier_champ, 5),
        model_champion=model_champion,
        model_champion_prob=model_champion_prob,
    )

    if save_path is not None:
        summary_rows = []
        for t in sorted(teams.keys()):
            summary_rows.append({
                "team": t,
                "prob_group_survival": round(prob_group.get(t, 0), 5),
                "prob_quarterfinal": round(prob_qf.get(t, 0), 5),
                "prob_semifinal": round(prob_sf.get(t, 0), 5),
                "prob_champion": round(prob_champion.get(t, 0), 5),
                "actual_group": 1 if t in WC2022_GROUP_SURVIVORS else 0,
                "actual_qf": 1 if t in WC2022_QUARTERFINALISTS else 0,
                "actual_sf": 1 if t in WC2022_SEMIFINALISTS else 0,
                "actual_champion": 1 if t in WC2022_CHAMPION else 0,
            })
        pd.DataFrame(summary_rows).to_csv(save_path, index=False)
        print(f"[backtest] Saved detailed results → {save_path}")

    return result
