"""
Apply June 2026 deltas to teams.csv
Zero-tolerance: bounds check [60,100], exact team count, validate_data() must pass.
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEAMS_CSV = ROOT / "data" / "teams.csv"
DELTA_CSV = ROOT / "data" / "delta_june2026.csv"

BOUNDS = (60.0, 100.0)
EXPECTED_TEAMS = 48

NUMERIC_DIMS = {
    "attack", "defense", "midfield", "transition", "setpiece",
    "goalkeeper", "depth", "coach", "penalties", "discipline",
    "health", "form", "climate_resilience", "altitude_resilience", "travel_resilience"
}


def load_teams_csv() -> tuple[list[str], list[dict]]:
    with open(TEAMS_CSV) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    return fieldnames, rows


def load_deltas() -> list[dict]:
    with open(DELTA_CSV) as f:
        return list(csv.DictReader(f))


def apply(fieldnames: list[str], rows: list[dict], deltas: list[dict]) -> list[dict]:
    team_map = {r["code"]: r for r in rows}
    changes_log = []

    for d in deltas:
        code = d["code"].strip()
        dim = d["dimension"].strip()
        delta = float(d["delta"].replace("+", ""))
        expected_new = float(d["new_value"])
        confidence = d["confidence"].strip()

        if code not in team_map:
            print(f"  ERROR: team code '{code}' not found in teams.csv", file=sys.stderr)
            sys.exit(1)

        if dim not in NUMERIC_DIMS:
            print(f"  ERROR: dimension '{dim}' not valid", file=sys.stderr)
            sys.exit(1)

        row = team_map[code]
        old_val = float(row[dim])
        new_val = old_val + delta

        # Verify consistency
        if abs(new_val - expected_new) > 0.01:
            print(f"  ERROR: {code}.{dim}: computed {new_val} != declared {expected_new}", file=sys.stderr)
            sys.exit(1)

        # Bounds check
        if not (BOUNDS[0] <= new_val <= BOUNDS[1]):
            print(f"  ERROR: {code}.{dim} = {new_val} out of bounds {BOUNDS}", file=sys.stderr)
            sys.exit(1)

        row[dim] = str(int(new_val)) if new_val == int(new_val) else str(new_val)
        changes_log.append(
            f"  [{confidence}] {code}.{dim}: {old_val:.0f} → {new_val:.0f} (Δ{delta:+.0f})"
        )

    return rows, changes_log


def write_teams_csv(fieldnames: list[str], rows: list[dict]):
    with open(TEAMS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_post_apply():
    sys.path.insert(0, str(ROOT / "src"))
    from wc2026.data_loader import validate_data, load_teams
    validate_data()
    teams = load_teams()
    assert len(teams) == EXPECTED_TEAMS, f"Expected {EXPECTED_TEAMS} teams, got {len(teams)}"
    # Check all numeric values in bounds
    for code, team in teams.items():
        for dim in NUMERIC_DIMS:
            val = getattr(team, dim)
            assert BOUNDS[0] <= val <= BOUNDS[1], f"{code}.{dim}={val} out of bounds"
    print(f"  POST-APPLY VALIDATION: {len(teams)} teams, all dims in [{BOUNDS[0]},{BOUNDS[1]}] ✓")


def main():
    print("=" * 64)
    print("STEP 5 — Applying June 2026 deltas to teams.csv")
    print("=" * 64)

    fieldnames, rows = load_teams_csv()
    print(f"Loaded {len(rows)} teams from teams.csv")

    deltas = load_deltas()
    print(f"Loaded {len(deltas)} delta entries from delta_june2026.csv")

    print("\nApplying changes:")
    rows, log = apply(fieldnames, rows, deltas)
    for line in log:
        print(line)

    print(f"\nWriting updated teams.csv ({len(rows)} rows)...")
    write_teams_csv(fieldnames, rows)

    print("\nRunning post-apply validation...")
    validate_post_apply()

    print("\n" + "=" * 64)
    print(f"STEP 5 COMPLETE — {len(log)} dimensions updated, all checks passed")
    print("=" * 64)


if __name__ == "__main__":
    main()
