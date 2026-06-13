"""#30/#52 — Bracket difficulty score per team based on expected KO opponent strength."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SUMMARY_CSV = ROOT / "outputs" / "tournament_run" / "summary.csv"
STAGE_PROBS_CSV = ROOT / "outputs" / "tournament_run" / "stage_probs.csv"
TEAMS_CSV = ROOT / "data" / "teams.csv"
GROUPS_JSON = ROOT / "data" / "groups.json"
OUT_CSV = ROOT / "outputs" / "tournament_run" / "bracket_difficulty.csv"


def _bracket_slot(group: str, position: int) -> str:
    return f"{group}{position}"


def main() -> None:
    summary = pd.read_csv(SUMMARY_CSV)
    stage_probs = pd.read_csv(STAGE_PROBS_CSV)
    teams_df = pd.read_csv(TEAMS_CSV)[['code', 'group']]
    with open(GROUPS_JSON) as f:
        groups = json.load(f)

    champ_map = dict(zip(summary['team'], summary['champion_prob']))
    sf_map = dict(zip(summary['team'], summary['sf_prob']))
    qf_map = dict(zip(summary['team'], summary['qf_prob']))

    # Group qualification probs per position from stage_probs
    group_pos = stage_probs[stage_probs['stage'] == 'group_survived'].set_index('team')['probability'].to_dict()
    group_map = dict(zip(teams_df['code'], teams_df['group']))

    # For each team, compute expected strength of opponents at each stage
    # Strategy: for each team T, sum over all possible opponents O: P(O is in that slot) * champ_prob(O)
    rows = []
    for team_code in summary['team']:
        grp = group_map.get(team_code, '?')
        if grp == '?':
            continue
        group_teams = groups.get(grp, [])
        teammates = [t for t in group_teams if t != team_code]

        # R32 opponent expected strength: average champ_prob of likely opponents
        # (simplified: opponents from qualifying slots we face in R32)
        r32_opp_strength = sum(champ_map.get(t, 0.0) for t in summary['team']
                               if group_map.get(t) != grp) / max(1, len(summary) - len(group_teams))

        # QF/SF: weighted by stage reach probability
        qf_strength = sum(
            qf_map.get(t, 0.0) * champ_map.get(t, 0.0) for t in summary['team'] if t != team_code
        ) / max(1e-9, sum(qf_map.get(t, 0.0) for t in summary['team'] if t != team_code))

        sf_strength = sum(
            sf_map.get(t, 0.0) * champ_map.get(t, 0.0) for t in summary['team'] if t != team_code
        ) / max(1e-9, sum(sf_map.get(t, 0.0) for t in summary['team'] if t != team_code))

        # Bracket difficulty index: weighted sum, earlier rounds weight more
        bdi = 0.40 * r32_opp_strength + 0.35 * qf_strength + 0.25 * sf_strength

        rows.append({
            'team': team_code,
            'group': grp,
            'r32_opp_strength': round(r32_opp_strength * 100, 3),
            'qf_opp_strength': round(qf_strength * 100, 3),
            'sf_opp_strength': round(sf_strength * 100, 3),
            'bracket_difficulty_index': round(bdi * 1000, 3),
        })

    result = pd.DataFrame(rows).sort_values('bracket_difficulty_index', ascending=False).reset_index(drop=True)
    result['rank'] = result.index + 1
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)

    print("BRACKET DIFFICULTY INDEX (higher = harder road to the title)\n")
    print(f"{'Rank':<5} {'Team':<6} {'Grp':<5} {'R32 opp':>9} {'QF opp':>9} {'SF opp':>9} {'BDI':>8}")
    print("-" * 60)
    for _, row in result.head(20).iterrows():
        print(f"{int(row['rank']):<5} {row['team']:<6} {row['group']:<5} "
              f"{row['r32_opp_strength']:>9.3f} {row['qf_opp_strength']:>9.3f} "
              f"{row['sf_opp_strength']:>9.3f} {row['bracket_difficulty_index']:>8.3f}")
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
