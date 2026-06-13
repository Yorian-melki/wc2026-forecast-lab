# Artifact Consistency Audit

Generated 2026-06-13T17:19:52 UTC

## Canonical truth (single source)

- **ml_weight**: 0.2
- **ml_weight_mode**: fixed (dynamic available)
- **maturity**: 6.43
- **tests**: 558
- **thestatsapi**: active
- **xg_upstream**: Highlightly==TSA (not independent)
- **intervals**: beta sampling floor (not total uncertainty)
- **market**: benchmark only, not integrated
- **champion_top3**: ESP 19.0%, ARG 15.7%, FRA 10.8%

## Artifact status

| File | Status | Issue | Action |
|---|---|---|---|
| `README.md` | STALE | 278 tests (now 558), Spain 16.97% (now 19.0%), no ML/TSA/intervals/4-WC validation | REWRITTEN this batch |
| `MODEL_CARD.md` | SUPERSEDED | P4 'frozen', no ML/intervals/providers | superseded by outputs/audit/model_card_public.md (kept as historical) |
| `MODEL_FREEZE.md` | CONTRADICTORY | 'do not modify before publication' but model evolved (ML added) | label historical; model_stack_config.json is current source of truth |
| `outputs/audit/final_maturity_score_v2/v3/v4.*` | HISTORICAL | earlier maturity snapshots | v5 is canonical |
| `outputs/audit/stratospheric_final_report.json / macro_upgrade_final_report.json` | HISTORICAL | per-batch checkpoints | latest = uncertainty_robustness_final_report.json + this batch |
| `outputs/audit/global_maturity_score.json` | HISTORICAL_BASELINE | 2026-06-10 baseline (5.21) | used as before-baseline, keep |
| `data/model_stack_config.json` | CURRENT | none — weight 0.20, mode fixed | source of truth |
| `tests/test_no_overclaim.py` | CURRENT | none — passing | keep enforcing |

No files deleted. Stale prose (README) rewritten to canonical truth; historical audit snapshots retained for provenance.