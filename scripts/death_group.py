"""#17 — Group of death detector using Shannon entropy."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.entropy import group_death_scores

SUMMARY_CSV = ROOT / "outputs" / "tournament_run" / "summary.csv"
TEAMS_CSV = ROOT / "data" / "teams.csv"
OUT_CSV = ROOT / "outputs" / "tournament_run" / "death_group_scores.csv"


def main() -> None:
    result = group_death_scores(summary_csv=SUMMARY_CSV, teams_csv=TEAMS_CSV)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)
    print("GROUP OF DEATH RANKING (normalized Shannon entropy)\n")
    print(f"{'Rank':<5} {'Group':<7} {'Entropy':>9} {'Norm H':>8}  {'Teams'}")
    print("-" * 65)
    for _, row in result.iterrows():
        marker = "  ← GROUP OF DEATH" if row['rank'] == 1 else ""
        print(f"{int(row['rank']):<5} {row['group']:<7} {row['entropy']:>9.4f} {row['normalized_entropy']:>8.4f}  {row['teams']}{marker}")
    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
