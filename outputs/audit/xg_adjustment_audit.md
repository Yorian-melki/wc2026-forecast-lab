# xG Adjustment Audit

- N=100,000, seed=20260613 (common random numbers → delta is adjustment-only)
- weight=6.0, cap=±8.0 Elo/match
- matches with xG: 4/4
- **max champion move: 0.203pp** (guardrail 1.0pp) → **PASS**
- default mode: **xg_adjusted**
- beta_elo: UNCHANGED (xG adjustment never touches it)

See xg_probability_delta.md for per-team and per-match detail.
