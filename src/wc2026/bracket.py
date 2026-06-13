from __future__ import annotations

import csv
import itertools
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .constants import BEST_THIRD_SLOT_ORDER, R16_MATCHES, R32_MATCHES, QF_MATCHES, SF_MATCHES, SLOT_FAMILIES


def _try_complete(slot_index: int, slots: List[str], remaining_groups: tuple[str, ...], partial: Dict[str, str]) -> bool:
    if slot_index >= len(slots):
        return True
    slot = slots[slot_index]
    candidates = [g for g in remaining_groups if g in SLOT_FAMILIES[slot]]
    for group in candidates:
        next_groups = tuple(x for x in remaining_groups if x != group)
        partial[slot] = group
        if _try_complete(slot_index + 1, slots, next_groups, partial):
            return True
        partial.pop(slot, None)
    return False


def solve_third_place_mapping(selected_groups: Iterable[str]) -> Dict[str, str]:
    selected = tuple(sorted(selected_groups))
    if len(selected) != 8:
        raise ValueError(f'exactly 8 third-placed groups required, got {selected}')
    mapping: Dict[str, str] = {}
    ok = _try_complete(0, BEST_THIRD_SLOT_ORDER, selected, mapping)
    if not ok:
        raise ValueError(f'no valid assignment found for groups={selected}')
    return {slot: mapping[slot] for slot in BEST_THIRD_SLOT_ORDER}


@lru_cache(maxsize=512)
def cached_third_place_mapping(selected_groups: tuple[str, ...]) -> Dict[str, str]:
    return solve_third_place_mapping(selected_groups)


def enumerate_all_third_place_mappings() -> List[dict]:
    rows = []
    for idx, combo in enumerate(itertools.combinations('ABCDEFGHIJKL', 8), start=1):
        mapping = solve_third_place_mapping(combo)
        row = {'option': idx, 'combination': ''.join(combo)}
        row.update(mapping)
        rows.append(row)
    return rows


def export_all_third_place_mappings(path: str | Path) -> None:
    rows = enumerate_all_third_place_mappings()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['option', 'combination'] + BEST_THIRD_SLOT_ORDER
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_round_of_32(placements: Dict[str, Dict[str, str]], best_third_groups: List[str]) -> OrderedDict[str, tuple[str, str]]:
    third_map = cached_third_place_mapping(tuple(sorted(best_third_groups)))

    def resolve(token: str) -> str:
        if token.startswith('3@'):
            slot = token[2:]
            group = third_map[slot]
            return placements[group]['3']
        group = token[-1]
        pos = token[0]
        return placements[group][pos]

    fixtures: OrderedDict[str, tuple[str, str]] = OrderedDict()
    for match_no, (left, right) in R32_MATCHES.items():
        fixtures[match_no] = (resolve(left), resolve(right))
    return fixtures


def build_knockout_round(previous_winners: Dict[str, str], round_mapping: OrderedDict[str, tuple[str, str]]) -> OrderedDict[str, tuple[str, str]]:
    fixtures: OrderedDict[str, tuple[str, str]] = OrderedDict()
    for match_no, (left, right) in round_mapping.items():
        fixtures[match_no] = (previous_winners[left], previous_winners[right])
    return fixtures


def build_round_of_16(r32_winners: Dict[str, str]) -> OrderedDict[str, tuple[str, str]]:
    return build_knockout_round(r32_winners, R16_MATCHES)


def build_quarterfinals(r16_winners: Dict[str, str]) -> OrderedDict[str, tuple[str, str]]:
    return build_knockout_round(r16_winners, QF_MATCHES)


def build_semifinals(qf_winners: Dict[str, str]) -> OrderedDict[str, tuple[str, str]]:
    return build_knockout_round(qf_winners, SF_MATCHES)


def build_final(sf_winners: Dict[str, str]) -> OrderedDict[str, tuple[str, str]]:
    return OrderedDict([('M104', (sf_winners['M101'], sf_winners['M102']))])
