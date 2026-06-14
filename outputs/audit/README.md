# `outputs/audit/` — what to trust

This folder accumulated many point-in-time audit reports across build sessions. Most are
**historical snapshots** kept for traceability — they are NOT the current state. Read the
authoritative files below; treat everything else as a dated record.

## Authoritative / current
| File | What it is |
|---|---|
| `model_card_public.md` | The public model card (purpose, limits, uncertainty, failure modes). |
| `final_maturity_score_v6.{json,md}` | Current self-assessed maturity (6.93/10). Supersedes v2–v5 + `global_maturity_score.*`. |
| `wc_historical_backtest.{json,md}` | WC2018/2022 backtest (champion Brier vs the uniform-1/48 null — no "vs 0.25" skill claim). |
| `ml_validation_report.{json,md}` | Leak-free single-match ML 1X2 gate (Brier 0.508 vs 0.529). |
| `tournament_walkforward_validation.json` · `upset_robust_ml_weighting.json` | Walk-forward evidence that set the ML tournament weight to 0.20. |
| `beta_bootstrap_ci.json` | β_elo bootstrap CI (raw MLE 0.9884 → production 0.5436 = ×0.55). |
| `model_stack_final_decision.{json,md}` · `ml_ensemble_integration_decision.json` | Final model-stack decision. |
| `data_lineage_map.{json,md}` · `reviewer_attack_audit.{json,md}` | Lineage + 20-point self-hostile review. |

## Historical (do NOT cite as current)
- Older maturity passes: `final_maturity_score_v2..v5.*`, `global_maturity_score.*`, `mega_maturity_matrix.*`, `maturity_score_before_after.json`.
- Phase/state snapshots: `pre_final_state.*`, `pre_stratospheric_state.*`, `final_stratospheric_report.json`, `phase10_final_report.md`, `done_vs_fake_done.md`, `final_remaining_actions_v*.md`, `final_action_plan.md`.
- Earlier provider probes (note: TheStatsAPI was later **re-activated** via trial — see `../../data/live/provider_status.json`): `provider_*`, `api_football_deep_probe.*`, `thestatsapi_*`.

Per-folder model attribution for `outputs/tournament_run/` lives in `outputs/tournament_run/ARTIFACTS.md`.
File-authority across the whole repo: `docs/FILE_AUTHORITY_TABLE.md`.
