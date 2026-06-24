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
**592 passed** (`PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`) — 581 baseline + 5 (1D-A) + 6 (1E).

## Phase 1E — metric/tooltip clarity (display-only) · commit `8b09044` (pushed)
Plain-language `help=` tooltips + a one-line glossary so non-experts can read the jargon metrics
that previously had no nearby definition: ECE, NLL, ρ (Dixon-Coles), `log_base`, and headline Brier
(Model Lab Math/Calibration tabs + Data Quality). RPS, λ, β, entropy, Dixon-Coles, Monte Carlo were
already explained. `tests/test_metric_tooltips.py` (6 static assertions). No calculation / model /
config / data change.

## Working protocol (updated)
**GREEN LANE** (implement → test → commit → push → report, no per-step approval): docs-only,
tests-only, small display-only UI fixes, accessibility micro-fixes, read-only audit tooling.
**RED LINE** (ASK FIRST): model math, probabilities, forecast generation, scorecard calculations,
model/config/data files, secrets/API keys, delete operations, navigation rewrite / `st.radio`
replacement, broad `app.py` refactor, visible product redesign.

## Phase 2A — Model improvement planning (PLANNING ONLY) — DONE
Memo at `docs/PHASE_2A_MODEL_PLAN.md`. Read-only analysis off the live 48-match audit. **No model/
config/data/probability change.**
- **Diagnosis:** W/D/L signal is **solid** (acc 58.3%, RPS 0.180 vs 0.229 baseline). The scoreline
  **tail is too thin** (5+ goals mean rank **18.0** vs ~4 for low totals; blowouts mean rank 13.73) —
  the **biggest model gap**. **Draw recall 0/14 is partly a decision-rule artifact** (`argmax` is
  structurally never draw under symmetric DC-Poisson; draw *calibration* only mildly low).
- **Recommendation:** first experiment = **offline overdispersion / fat-tail scoreline distribution
  test** (Negative-Binomial marginals / shared shock), gated by the existing leak-free walk-forward
  backtest. Draws (isotonic) = second. Decision-rule draw hack = rejected (metric-gaming).

## Phase 2B — tail-overdispersion experiment (OFFLINE) · commit `fb739a8` — NEGATIVE but VALUABLE
NegBin vs Poisson scoreline dist on martj42 2010-2025 (10,555 matches). `NegBin(r=∞)==Poisson==prod
_build_dc_flat` (15 equivalence tests). **0/27 candidates pass.** Fattening the tail buys only ~4%
rel improvement on 5+ goals rank while degrading Brier/RPS/NLL/ECE and dropping top-3 coverage — a
bad trade. **Conclusion: tail overdispersion alone is NOT worth a production change.** Deepest
insight: scoreline rank and proper calibration are partially in tension. Artifacts:
`outputs/experiments/2B_tail_dispersion/`, scratch code in `src/wc2026/experimental/nb_scoreline.py`
+ `scripts/exp_tail_dispersion.py` (never imported by app.py). Production files untouched.

## Phase 2C — full weakness & solution research MAP (RESEARCH ONLY) — DONE
Memo: `docs/PHASE_2C_FULL_MODEL_RESEARCH_MAP.md`. 15 research lenses + full weakness/solution maps.
Grounded fact: `expected_goals` is **Elo-only** (no market/lineups/style/incentives in μ). Key honest
findings: draw recall 0/14 ≈ decision-rule artifact; exact top-1 8.3% ≈ near the entropy floor; much
of the rank weakness is metric-induced (rank ↔ calibration tension); validation rests on n≈4
tournaments. **Recommended next = NOT a model change.**

## Phase 2D — Objective & ceiling audit (OFFLINE) · commit `6d04da3` — DONE
Analytic self-sim ceiling (cross-checked vs Monte-Carlo, 6 tests; 613 suite passes) on martj42
2010-2025. Report: `outputs/experiments/2D_objective_ceiling/`. **Validated weakness map:**
- **Exact-score top-1/top-3 → DO NOT optimize directly.** Top-1 ceiling is only ~12.7% (vs 10.9%
  always-guess-1-0); top-3/top-5 are AT ceiling. Irreducible noise, not model failure.
- **Scoreline rank → DEMOTE to diagnostic, not a target.** Aggregate is ~1 above ceiling (8.08 vs
  7.05); recoverable signal lives only in the minority high-total bucket; optimizing it trades
  against W/D/L calibration.
- **Draw recall 0/14 → decision-rule artifact** (ceiling recall ≈ 0 under argmax). Not a prob failure.
- **Real remaining weaknesses (bounded, entangled):** (a) high-total/blowout **conditional** ranking
  (5+ goals real rank 21.78 vs ceiling 7.03 = genuine mis-specification, but ~17% of matches),
  (b) mild **draw under-calibration** (actual − predicted P(draw) ≈ −3.6pp), (c) mild **W/D/L
  under-confidence** (REAL beats self-sim ⇒ over-dispersed; sharpening fights champion temperature).
- **Phase 2B lesson stands: globally fattening the distribution FAILED — do NOT do it.** Any
  high-total fix must be a *conditional* lever, gated on not regressing low-total games or W/D/L.
- The **live-48 audit is very noisy** (n=48: exact_top1 95% spread ~[0.04,0.21]); don't over-read it.

## Next step
**Phase 2E — NEXT MODEL EXPERIMENT SELECTION ONLY.** Compare 5 candidates (conditional high-total
mean / draw calibration / W-D-L sharpening / market-total anchor / reporting-only) on the validated
weakness map and pick the next offline experiment. **No implementation.** See `NEXT_STEP.md`.
(1D-B nav still deferred.)
