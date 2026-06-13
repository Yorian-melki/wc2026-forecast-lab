"""Live tournament state: fetch, parse, and condition simulations on real results."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from .group_rules import PlayedMatch
from .name_map import to_code

OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json"
    "/master/2026/worldcup.json"
)

GROUP_ROUNDS = {f"Matchday {i}" for i in range(1, 18)}  # all group matchdays


@dataclass
class LiveMatchResult:
    team1: str          # 3-letter code
    team2: str          # 3-letter code
    goals1: int
    goals2: int
    group: Optional[str]   # 'A'…'L' or None for KO
    round_name: str        # 'Matchday 1', 'Round of 32', etc.
    decided_in: str        # '90', 'ET', 'PEN'
    match_date: date


@dataclass
class LiveState:
    fetched_at: datetime
    completed: List[LiveMatchResult] = field(default_factory=list)
    # group_code → list of PlayedMatch already done
    group_results: Dict[str, List[PlayedMatch]] = field(default_factory=dict)
    # KO: match_no string (e.g. 'M73') → winner code  (not used until KO data available)
    ko_winners: Dict[str, str] = field(default_factory=dict)
    eliminated: set = field(default_factory=set)  # team codes definitely out

    @property
    def n_completed(self) -> int:
        return len(self.completed)

    @property
    def last_result_date(self) -> Optional[date]:
        if not self.completed:
            return None
        return max(r.match_date for r in self.completed)


def _parse_score(score_obj: dict) -> tuple[int, int, str]:
    """Return (goals1, goals2, decided_in) from a score dict."""
    if 'p' in score_obj:
        # Penalties: use ET score as final, decided_in = 'PEN'
        et = score_obj.get('et', score_obj['ft'])
        return et[0], et[1], 'PEN'
    if 'et' in score_obj:
        et = score_obj['et']
        return et[0], et[1], 'ET'
    ft = score_obj['ft']
    return ft[0], ft[1], '90'


def _infer_group(group_str: str) -> Optional[str]:
    """'Group A' → 'A'"""
    if group_str and group_str.startswith('Group '):
        return group_str.split(' ', 1)[1]
    return None


def fetch_live_state(url: str = OPENFOOTBALL_URL, timeout: int = 15) -> LiveState:
    """Fetch worldcup.json and return a LiveState with all completed matches."""
    req = urllib.request.Request(url, headers={'User-Agent': 'wc2026-quant/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read().decode())

    state = LiveState(fetched_at=datetime.now())

    for m in raw.get('matches', []):
        if 'score' not in m:
            continue  # not yet played

        # Skip KO bracket placeholder names (e.g. '1A', 'W73')
        t1_raw, t2_raw = m.get('team1', ''), m.get('team2', '')
        try:
            t1 = to_code(t1_raw)
            t2 = to_code(t2_raw)
        except ValueError:
            continue  # placeholder name — KO bracket not yet resolved

        goals1, goals2, decided_in = _parse_score(m['score'])
        group_code = _infer_group(m.get('group', ''))
        round_name = m.get('round', '')

        match_date = date.fromisoformat(m['date'])

        result = LiveMatchResult(
            team1=t1, team2=t2,
            goals1=goals1, goals2=goals2,
            group=group_code, round_name=round_name,
            decided_in=decided_in, match_date=match_date,
        )
        state.completed.append(result)

        if group_code is not None and round_name in GROUP_ROUNDS:
            state.group_results.setdefault(group_code, []).append(
                PlayedMatch(
                    team_a=t1, team_b=t2,
                    goals_a=goals1, goals_b=goals2,
                    conduct_a=0, conduct_b=0,  # conduct not tracked in live feed
                )
            )

    # Derive eliminated teams (after group stage: teams with 0 points in full groups)
    # A group is "complete" when 6 matches are played
    for grp, results in state.group_results.items():
        if len(results) == 6:
            pts: Dict[str, int] = {}
            for r in results:
                pts.setdefault(r.team_a, 0)
                pts.setdefault(r.team_b, 0)
                if r.goals_a > r.goals_b:
                    pts[r.team_a] += 3
                elif r.goals_a < r.goals_b:
                    pts[r.team_b] += 3
                else:
                    pts[r.team_a] += 1
                    pts[r.team_b] += 1
            # Bottom 2 eliminated (simplified — doesn't account for best thirds)
            ranked = sorted(pts.items(), key=lambda x: x[1])
            state.eliminated.update(c for c, _ in ranked[:2])

    return state


def load_live_state_from_file(path: str) -> LiveState:
    """Load a previously-saved state JSON (for offline testing)."""
    with open(path) as f:
        raw = json.load(f)

    state = LiveState(fetched_at=datetime.fromisoformat(raw['fetched_at']))
    for m in raw.get('completed', []):
        r = LiveMatchResult(
            team1=m['team1'], team2=m['team2'],
            goals1=m['goals1'], goals2=m['goals2'],
            group=m.get('group'), round_name=m['round_name'],
            decided_in=m['decided_in'],
            match_date=date.fromisoformat(m['match_date']),
        )
        state.completed.append(r)
        if r.group:
            state.group_results.setdefault(r.group, []).append(
                PlayedMatch(
                    team_a=r.team1, team_b=r.team2,
                    goals_a=r.goals1, goals_b=r.goals2,
                    conduct_a=0, conduct_b=0,
                )
            )
    state.eliminated = set(raw.get('eliminated', []))
    return state


def save_live_state(state: LiveState, path: str) -> None:
    obj = {
        'fetched_at': state.fetched_at.isoformat(),
        'n_completed': state.n_completed,
        'completed': [
            {
                'team1': r.team1, 'team2': r.team2,
                'goals1': r.goals1, 'goals2': r.goals2,
                'group': r.group, 'round_name': r.round_name,
                'decided_in': r.decided_in,
                'match_date': r.match_date.isoformat(),
            }
            for r in state.completed
        ],
        'eliminated': sorted(state.eliminated),
    }
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)
