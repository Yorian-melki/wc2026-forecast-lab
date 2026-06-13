"""Shannon entropy for group-of-death detection."""
from __future__ import annotations

import math
import pandas as pd


def group_death_scores(summary_csv: str | None = None, teams_csv: str | None = None,
                       summary_df: pd.DataFrame | None = None,
                       teams_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Compute normalized Shannon entropy of group survival probs per group.
    High entropy = tightly contested group (group of death).
    Low entropy = one or two dominant teams.

    Returns DataFrame sorted by normalized_entropy descending.
    """
    if summary_df is None:
        summary_df = pd.read_csv(summary_csv)
    if teams_df is None:
        teams_df = pd.read_csv(teams_csv)[['code', 'group']]

    df = summary_df[['team', 'group_survival_prob']].merge(
        teams_df.rename(columns={'code': 'team'}), on='team'
    )
    rows = []
    for group, grp in df.groupby('group'):
        probs = grp['group_survival_prob'].values
        n = len(probs)
        H = -sum(p * math.log2(p) if p > 1e-12 else 0.0 for p in probs)
        H_max = math.log2(n) if n > 1 else 1.0
        teams_in_group = grp['team'].tolist()
        rows.append({
            'group': group,
            'entropy': round(H, 4),
            'normalized_entropy': round(H / H_max, 4),
            'teams': ' '.join(teams_in_group),
            'min_survival': round(float(probs.min()), 4),
            'max_survival': round(float(probs.max()), 4),
        })
    result = pd.DataFrame(rows).sort_values('normalized_entropy', ascending=False).reset_index(drop=True)
    result['rank'] = result.index + 1
    return result
