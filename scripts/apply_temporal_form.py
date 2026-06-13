"""#19 — Apply temporal decay form scores to teams.csv."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.temporal_form import compute_all_temporal_forms

FORM_HISTORY = ROOT / "data" / "form_history.csv"
TEAMS_CSV = ROOT / "data" / "teams.csv"


def main(dry_run: bool = False) -> None:
    temporal_scores = compute_all_temporal_forms(FORM_HISTORY)
    teams = pd.read_csv(TEAMS_CSV)
    updated = 0
    print(f"{'Code':<6} {'Old form':>9} {'New form':>9} {'Delta':>7}")
    print("-" * 36)
    for idx, row in teams.iterrows():
        code = row['code']
        if code in temporal_scores:
            new_form = temporal_scores[code]
            old_form = float(row['form'])
            delta = new_form - old_form
            print(f"{code:<6} {old_form:>9.1f} {new_form:>9.1f} {delta:>+7.1f}")
            if not dry_run:
                teams.at[idx, 'form'] = float(new_form)
            updated += 1
    print(f"\n{updated} teams updated.")
    if not dry_run:
        teams.to_csv(TEAMS_CSV, index=False)
        print(f"Saved: {TEAMS_CSV}")
    else:
        print("DRY RUN — no changes written.")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
