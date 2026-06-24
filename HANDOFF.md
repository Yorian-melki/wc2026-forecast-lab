# HANDOFF — WC2026 Forecast Lab (for a fresh Claude Code session)

> Read this + `NEXT_STEP.md` first. Then **verify the live state from the repo** (git log, tags,
> configs, tests) — do NOT trust any number from memory. See "What must NOT be inferred from memory".

## Project objective
A transparent **probabilistic** World Cup 2026 forecasting lab (NOT a betting product, NOT a
single prediction). It quantifies uncertainty, shows its work, admits limits, and tracks whether
the model is actually right ("probabilities, not predictions" must be preserved).

## What this is (stack & deploy)
- **Python / Streamlit** single-page app: `app.py` (~3000 lines) + `src/wc2026/` (model, providers,
  `scorecard.py`, `live_engine.py`, `version.py`). **NOT Node/Vercel** — ignore any npm/Vercel
  guidance; rollback = git + `pytest`, not `npm`.
- Deployed on **Render** at `https://wc2026.yorian-melki.com`, **auto-deploys on `git push origin main`** (~2–3 min build). No separate CI gate.
- venv: `PYTHONPATH=src .venv/bin/python`. Tests: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`.
- Model: Calibrated Elo → Dixon-Coles Poisson → ML 1X2 ensemble @0.20 → 100k Monte Carlo.
  Config `data/model_stack_config.json`, params `data/elo_calibrated_params.json`. Version manifest
  `configs/model_version.json` + read-only loader `src/wc2026/version.py`.
- The structured handoff that drives this work: `handoff/wc2026_claude_code_handoff_v3/`
  (gitignored). Key docs: `06_claude_prompts/CLAUDE_CODE_MASTER_PROMPT.md`,
  `11_next_release_spec/NEXT_RELEASE_SPEC_V2.md`, `03_model_audit/MODEL_AUDIT.md`,
  `12_external_audits/TALOS_UI_UX_REPORT.md`.

## Working method (non-negotiable)
Phased, one approved phase at a time. **Plan → show exact files/commands → get approval → implement
→ verify → commit → get approval → push.** Never change model math before the versioning/rollback
layer exists (it now does). Every metric movement must be reproducible. Never present hand-tuned
priors as measured. Keep all honesty/disclaimer copy.

## Completed phases (all pushed to `main`)
- **Phase 1A — versioning/rollback/changelog** · commit `3197091` (pushed).
  - git tag `model-baseline-v0.6.93-ml20-dc` → commit `4e58489` (the deployed model baseline).
  - `configs/archive/` (baseline config+params snapshots), `configs/model_version.json`,
    `src/wc2026/version.py`, `CHANGELOG_MODEL.md`, empty `outputs/releases/` +
    `outputs/audit/live_metric_snapshots/`, and a **read-only** "Model version & changelog" panel
    in the Model Lab page. No model math change.
- **Phase 1B — read-only metric audit + snapshot** · commit `e3770f4` (pushed).
  - `scripts/audit_live_scorecard.py` (read-only; `--live` sources the full set via
    `fetch_live_state`). Official snapshot `outputs/audit/live_metric_snapshots/2026-06-24_14-54.json`
    = **48 matches** (outcome 58.3%, RPS 0.180 vs 0.229, exact top-1 8.3% / top-3 29.2%, avg rank
    7.98, **draw recall 0.0**). Tests: deterministic, in-bounds, read-only.
- **Phase 1C — no-raw-`nan` / missing-data display guards** · commit `4429f8f` (pushed).
  - `format_optional_number()` helper; Nation DNA squad-DNA shows "Default prior used" / "No provider
    coverage" instead of `nan`; penalty notes hidden when NaN (Nation DNA + Head-to-Head).
  - `tests/test_no_nan_ui.py`: 0 raw `nan` across all 11 pages + all 48 Nation DNA teams.
- **Phase 1D-A — low-risk a11y polish (display-only)** · commit `37a743f` (pushed; latest impl commit. Current repo HEAD is the later docs commit `42e9ee2`).
  - Two invisible (`height=0`) utility iframes (analytics shim in `src/wc2026/web_analytics.py`,
    countdown in `app.py`) now set `window.frameElement` `title` + `aria-hidden`/`tabindex=-1` so
    screen readers no longer announce a meaningless "st.iframe".
  - Cookie consent banner (`src/wc2026/web_analytics.py`): mobile `env(safe-area-inset-bottom)` +
    `max-height:60vh;overflow:auto` (never blankets the screen), `role="region"` + localized
    `aria-label`. Buttons were already semantic `<button>`s.
  - `tests/test_a11y_iframe_consent.py`: 5 static source-text assertions.
  - NOT touched: nav/`st.radio`, contrast tokens (already AA), typography (already consolidated),
    any model/config/data file. Site healthy (HTTP 200) post-deploy.

## Model/config/forecast/scorecard files — UNCHANGED through 1A–1C
`data/model_stack_config.json`, `data/elo_calibrated_params.json`, `data/elo_live_params.json`,
`src/wc2026/calibrated_elo_model.py`, `src/wc2026/scorecard.py` are all byte-identical to the
baseline tag `model-baseline-v0.6.93-ml20-dc`. `data/wc2026_live.json` stays at blob
`bbcd3ef82b520034bd51f8fce58d41c49e648271`.

## Latest tests
**586 passed** (`PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`) — 581 baseline + 5 from 1D-A.

## Working protocol (updated)
**GREEN LANE** (implement → test → commit → push → report, no per-step approval): docs-only,
tests-only, small display-only UI fixes, accessibility micro-fixes, read-only audit tooling.
**RED LINE** (ASK FIRST): model math, probabilities, forecast generation, scorecard calculations,
model/config/data files, secrets/API keys, delete operations, navigation rewrite / `st.radio`
replacement, broad `app.py` refactor, visible product redesign.

## Next step
**Phase 1D-B planning is DONE** — options memo at `docs/PHASE_1D-B_NAV_PLAN.md` (3 options + risk +
recommendation). **Recommendation = DEFER** nav implementation (proper fix = RED-LINE rewrite; cheap
ARIA overlay = unverifiable). No approved implementation action right now; nav stays `st.radio`
untouched until Yorian picks a trigger/option. See `NEXT_STEP.md`.
