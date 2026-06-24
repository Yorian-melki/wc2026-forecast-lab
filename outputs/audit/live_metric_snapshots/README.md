# outputs/audit/live_metric_snapshots/

Immutable, timestamped scorecard metric snapshots — one file per public app update, named
`YYYY-MM-DD_HH-mm.json`. They let us compare metric movements over time and reproduce what the
Scorecard showed at any point.

Populated by the metric-audit script (Phase 1, step 3 — `scripts/audit_live_scorecard.py`), which
is **not** part of Phase 1A. This folder is created now so the structure is in place.
