from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .data_loader import Team
from .group_rules import TeamTable


@dataclass
class ThirdPlacedRecord:
    group: str
    code: str
    points: int
    gd: int
    gf: int
    conduct_penalty: int
    fifa_rank: int


def rank_best_thirds(group_tables: Dict[str, Dict[str, TeamTable]], group_orders: Dict[str, List[str]], teams: Dict[str, Team]) -> List[ThirdPlacedRecord]:
    records: List[ThirdPlacedRecord] = []
    for group, order in group_orders.items():
        third = order[2]
        rec = group_tables[group][third]
        records.append(
            ThirdPlacedRecord(
                group=group,
                code=third,
                points=rec.points,
                gd=rec.gd,
                gf=rec.gf,
                conduct_penalty=rec.conduct_penalty,
                fifa_rank=teams[third].fifa_rank,
            )
        )
    ranked = sorted(
        records,
        key=lambda r: (r.points, r.gd, r.gf, -r.conduct_penalty, -r.fifa_rank, r.code),
        reverse=True,
    )
    return ranked
