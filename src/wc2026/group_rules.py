from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .constants import GROUP_MATCH_TEMPLATE
from .data_loader import Team
from .match_model import MatchModel, MatchSummary


@dataclass
class TeamTable:
    code: str
    points: int = 0
    gf: int = 0
    ga: int = 0
    conduct_penalty: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga


@dataclass
class PlayedMatch:
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    conduct_a: int
    conduct_b: int


def _add_match_to_table(table: Dict[str, TeamTable], match: PlayedMatch) -> None:
    a = table[match.team_a]
    b = table[match.team_b]
    a.gf += match.goals_a
    a.ga += match.goals_b
    b.gf += match.goals_b
    b.ga += match.goals_a
    a.conduct_penalty += match.conduct_a
    b.conduct_penalty += match.conduct_b
    if match.goals_a > match.goals_b:
        a.points += 3
    elif match.goals_a < match.goals_b:
        b.points += 3
    else:
        a.points += 1
        b.points += 1


def _mini_table(team_codes: Iterable[str], matches: List[PlayedMatch]) -> Dict[str, TeamTable]:
    team_codes = list(team_codes)
    subset = {code: TeamTable(code=code) for code in team_codes}
    code_set = set(team_codes)
    for match in matches:
        if match.team_a in code_set and match.team_b in code_set:
            _add_match_to_table(subset, match)
    return subset


def _group_by_equal_keys(ordered_codes: List[str], key_map: Dict[str, Tuple[int, ...]]) -> List[List[str]]:
    groups: List[List[str]] = []
    current: List[str] = []
    current_key = None
    for code in ordered_codes:
        key = key_map[code]
        if current_key is None or key == current_key:
            current.append(code)
            current_key = key
        else:
            groups.append(current)
            current = [code]
            current_key = key
    if current:
        groups.append(current)
    return groups


def _rank_subset(codes: List[str], all_matches: List[PlayedMatch], overall: Dict[str, TeamTable], teams: Dict[str, Team]) -> List[str]:
    if len(codes) <= 1:
        return list(codes)

    mini = _mini_table(codes, all_matches)
    key1 = {code: (mini[code].points, mini[code].gd, mini[code].gf) for code in codes}
    ordered1 = sorted(codes, key=lambda c: key1[c], reverse=True)
    tied_groups = _group_by_equal_keys(ordered1, key1)

    # If step-1 creates separation, recurse on the unresolved sub-groups only.
    if len(tied_groups) > 1:
        resolved: List[str] = []
        for grp in tied_groups:
            if len(grp) == 1:
                resolved.extend(grp)
            else:
                resolved.extend(_rank_subset(grp, all_matches, overall, teams))
        return resolved

    # Still unresolved: move to overall criteria.
    key2 = {
        code: (
            overall[code].gd,
            overall[code].gf,
            -overall[code].conduct_penalty,
            -teams[code].fifa_rank,
            code,
        )
        for code in codes
    }
    ordered2 = sorted(codes, key=lambda c: key2[c], reverse=True)
    return ordered2


def rank_group(group_codes: List[str], matches: List[PlayedMatch], teams: Dict[str, Team]) -> List[str]:
    overall = {code: TeamTable(code=code) for code in group_codes}
    for match in matches:
        _add_match_to_table(overall, match)

    base_key = {code: (overall[code].points,) for code in group_codes}
    ordered = sorted(group_codes, key=lambda c: base_key[c], reverse=True)
    tied_groups = _group_by_equal_keys(ordered, base_key)
    final_order: List[str] = []
    for grp in tied_groups:
        if len(grp) == 1:
            final_order.extend(grp)
        else:
            final_order.extend(_rank_subset(grp, matches, overall, teams))
    return final_order


def simulate_group_conditioned(
    group_name: str,
    group_codes: List[str],
    teams: Dict[str, Team],
    model: MatchModel,
    rng,
    fixed_matches: List[PlayedMatch],
) -> tuple[Dict[str, TeamTable], List[PlayedMatch], List[str]]:
    """Like simulate_group but starts from already-played matches (fixed real results)."""
    played_pairs: set[frozenset] = {frozenset([m.team_a, m.team_b]) for m in fixed_matches}
    all_matches: List[PlayedMatch] = list(fixed_matches)
    for left_pos, right_pos in GROUP_MATCH_TEMPLATE:
        team_a = group_codes[int(left_pos) - 1]
        team_b = group_codes[int(right_pos) - 1]
        if frozenset([team_a, team_b]) in played_pairs:
            continue
        result: MatchSummary = model.simulate_group_match(teams[team_a], teams[team_b], rng)
        all_matches.append(PlayedMatch(
            team_a=team_a, team_b=team_b,
            goals_a=result.goals_a, goals_b=result.goals_b,
            conduct_a=result.conduct_a, conduct_b=result.conduct_b,
        ))
    table = {code: TeamTable(code=code) for code in group_codes}
    for match in all_matches:
        _add_match_to_table(table, match)
    order = rank_group(group_codes, all_matches, teams)
    return table, all_matches, order


def simulate_group(group_name: str, group_codes: List[str], teams: Dict[str, Team], model: MatchModel, rng) -> tuple[Dict[str, TeamTable], List[PlayedMatch], List[str]]:
    matches: List[PlayedMatch] = []
    for left_pos, right_pos in GROUP_MATCH_TEMPLATE:
        team_a = group_codes[int(left_pos) - 1]
        team_b = group_codes[int(right_pos) - 1]
        result: MatchSummary = model.simulate_group_match(teams[team_a], teams[team_b], rng)
        matches.append(
            PlayedMatch(
                team_a=team_a,
                team_b=team_b,
                goals_a=result.goals_a,
                goals_b=result.goals_b,
                conduct_a=result.conduct_a,
                conduct_b=result.conduct_b,
            )
        )
    table = {code: TeamTable(code=code) for code in group_codes}
    for match in matches:
        _add_match_to_table(table, match)
    order = rank_group(group_codes, matches, teams)
    return table, matches, order


def summarize_group(order: List[str], table: Dict[str, TeamTable]) -> List[dict]:
    rows = []
    for idx, code in enumerate(order, start=1):
        rec = table[code]
        rows.append({
            'position': idx,
            'team': code,
            'points': rec.points,
            'gd': rec.gd,
            'gf': rec.gf,
            'ga': rec.ga,
            'conduct_penalty': rec.conduct_penalty,
        })
    return rows
