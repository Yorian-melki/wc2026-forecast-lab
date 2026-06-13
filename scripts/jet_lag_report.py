"""#48 — Jet lag / circadian penalty report for WC 2026."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.jet_lag import worst_jet_lag_teams, compute_jet_lag, TEAM_HOME_UTC

# Example: opening match New York, 21h UTC (5 PM ET)
OPENING_MATCH_VENUE = "New York"
OPENING_KICKOFF_UTC = 21.0
DAYS_ARRIVAL = 4.0  # teams arrive ~4 days before first match


def main() -> None:
    all_codes = list(TEAM_HOME_UTC.keys())
    results = [
        compute_jet_lag(code, OPENING_MATCH_VENUE, OPENING_KICKOFF_UTC, DAYS_ARRIVAL)
        for code in all_codes
    ]
    results.sort(key=lambda x: x.performance_factor)

    print(f"JET LAG PENALTIES — venue: {OPENING_MATCH_VENUE}, kickoff UTC: {OPENING_KICKOFF_UTC:.0f}h\n")
    print(f"{'Team':<6} {'TZ Δ':>6} {'Local kick':>11} {'Perf factor':>12}  {'Impact'}")
    print("-" * 55)
    for r in results:
        impact = "SEVERE" if r.performance_factor < 0.94 else ("HIGH" if r.performance_factor < 0.97 else "LOW")
        print(f"{r.team_code:<6} {r.timezone_delta:>6.1f} {r.kickoff_local_home:>11.1f}h {r.performance_factor:>12.4f}  {impact}")

    print("\n--- WORST AFFECTED TEAMS (performance < 0.95) ---")
    severe = [r for r in results if r.performance_factor < 0.95]
    for r in severe:
        print(f"  {r.team_code}: factor={r.performance_factor:.4f}  (TZ diff={r.timezone_delta:.0f}h)")


if __name__ == "__main__":
    main()
