# Pre-Stratospheric State — 2026-06-13T12:37:05 UTC

- **Git**: NOT a git repository (no .git) — no version-control safety net; backups made before destructive edits
- **Baseline tests**: 504 passed (before session)
- **Maturity at start**: 5.25 (D+/C-)

## Providers at start
- highlightly: A (xG, working)
- api_football: B (working)
- football_data_org: B (working)
- thestatsapi: KEY_REVOKED (old key, unverified for new key)
- openfootball: C (fallback)

## Known gaps at start
- TheStatsAPI new key never live-probed
- xG present but not integrated into probabilities
- no walk-forward validation (existing WC backtest circular)
- no ML model
- no beta_elo CI
- no calibration layer applied
- sklearn/statsmodels not installed
