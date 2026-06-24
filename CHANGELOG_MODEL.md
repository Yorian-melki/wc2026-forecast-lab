# Model Changelog — WC2026 Forecast Lab

Notable **model/engine** changes, tracked separately from app/UI commits
([Keep a Changelog](https://keepachangelog.com) style). Each entry: version · date ·
Added / Changed / Fixed / Validation / Known limitations / Rollback.

> The model math, parameters, probabilities and forecast generation are NOT changed by the
> versioning layer itself. Any future entry that changes them will say so explicitly and ship
> behind a flag with an archived previous version.

## [v0.6.93-ml20-dc] — 2026-06-24 — Baseline (Phase 1A)

First **versioned baseline**. This entry establishes version/rollback infrastructure around the
existing, already-deployed engine — **no model math change**.

- **Engine**: Calibrated Elo → Dixon-Coles Poisson → ML 1X2 ensemble (weight 0.20) → 100,000 Monte Carlo simulations.
- **Parameters**: β_elo = 0.5436 · ρ (Dixon-Coles) = −0.021 · log_base = 0.2269 · ML weight = 0.20 (fixed).
- **Flags**: `use_ml_match_model` = true · `use_xg_live_adjustment` = true · `use_isotonic_calibrator` = false.
- **Validation (as deployed)**: walk-forward on WC2010/14/18/22; ML weight 0.20 chosen by the upset-robustness rule.

### Added (Phase 1A — infrastructure only, no math/probability change)
- Baseline git tag `model-baseline-v0.6.93-ml20-dc` (points at the deployed model commit `4e58489`).
- Archived config + params snapshot in `configs/archive/`.
- Empty `outputs/audit/live_metric_snapshots/` and `outputs/releases/` for future metric snapshots & releases.
- `configs/model_version.json` manifest + `src/wc2026/version.py` (read-only loader).
- Read-only "Model version & changelog" panel in the **Model Lab** page.
- This changelog file.

### Known limitations (carried from MODEL_AUDIT, unchanged)
- Exact-score top-1 weak (~8%); average rank of the real score ≈ 8 (scoreline mass too dispersed).
- Draws under-predicted; blowouts (≥5 goals / margin ≥3) under-ranked.
- Champion-level Brier ≈ uniform 1/48 null — edge is narrowing the field, not pinpointing the winner.

### Rollback
- Code: `git checkout model-baseline-v0.6.93-ml20-dc -- <files>` (or `git revert <sha>`), then `pytest`.
- Config: `cp configs/archive/v0.6.93-ml20-dc__model_stack_config.json data/model_stack_config.json`.
- Params: `cp configs/archive/v0.6.93-ml20-dc__elo_calibrated_params.json data/elo_calibrated_params.json`.
