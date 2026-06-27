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
  (b) mild **draw OVER-prediction** on robust historical data (predicted ≈0.255 > actual ≈0.219;
  gap −3.6pp) — the live-48 hinted the *opposite* (under-prediction) but was noise; **[corrected by 2F]**,
  (c) mild **W/D/L under-confidence** (REAL beats self-sim ⇒ over-dispersed; sharpening fights champion
  temperature).
- **Phase 2B lesson stands: globally fattening the distribution FAILED — do NOT do it.** Any
  high-total fix must be a *conditional* lever, gated on not regressing low-total games or W/D/L.
- The **live-48 audit is very noisy** (n=48: exact_top1 95% spread ~[0.04,0.21]); don't over-read it.

## Phase 2E — next experiment selection (SELECTION ONLY) — DONE
Memo: `docs/PHASE_2E_EXPERIMENT_SELECTION.md`. Compared 5 candidates on the validated weakness map.
**Recommendation = Candidate 2, Draw probability calibration** — the only lever that is real + cheap +
low-risk + champion-safe + needs no new data + fast to kill. Run offline (fit-on-train → walk-forward),
strict proper-score gate (accept only if RPS **and** NLL improve OOS without ECE/accuracy/champion
regression). **Deferred:** conditional high-total mean (no proven pre-match signal → gate behind a
feature kill-test and/or market data), market-total anchor (data-blocked + fetch-forbidden; it's the
*gate* for the conditional-mean path), temperature sharpening (run only as a diagnostic frontier sweep
— shipping it reopens the champion over-concentration tension). **Reporting-only = parallel, zero-risk,
always-worth-doing** but it's not a model experiment.

## Phase 2F — draw calibration experiment (OFFLINE) · commit `3cc31b6` — DONE, INCONCLUSIVE (not shipped)
Calibrators A (single γ) + B (isotonic), walk-forward OOS on martj42 2010-2025 (pooled n=5,713).
7 calibrator tests; full suite 620 passed. Report: `outputs/experiments/2F_draw_calibration/`.
- **Sign correction:** fitted **γ ≈ 0.84 (<1)** every fold ⇒ on robust historical data the model mildly
  **OVER-predicts** draws (predicted ≈0.255 > actual ≈0.219). The earlier "draw under-calibration"
  framing (from the noisy live-48 buckets) was **wrong direction** — live-48 draw signal is not reliable.
- **Result:** A and B slightly improve OOS **RPS/Brier/ECE**, but the **NLL gain is WITHIN bootstrap
  noise** ⇒ the pre-registered "RPS *and* NLL beyond noise" gate is **NOT met**; W/D/L mass shift
  (~4–5%) also exceeds the 3% champion proxy. **Verdict: INCONCLUSIVE/FAIL for both.**
- **Decisions:** **do NOT ship draw calibration**; **do NOT treat draw recall as a model target**;
  **do NOT pursue draw calibration further unless new evidence appears.**
- Pattern note: **2B (fat tail) and 2F (draw calibration) both failed to produce a shippable change.**

## Phase 2G — next experiment reassessment (ANALYSIS ONLY) — DONE
Memo: `docs/PHASE_2G_EXPERIMENT_REASSESSMENT.md`. **Verdict: another model-MATH experiment is NOT
justified now.** Evidence: 2D ceiling audit (model near its floor) + 2B and 2F both failed; the only
real remaining signals are data-blocked (market→conditional high-total) or champion-entangled
(temperature) or aim at a demoted diagnostic (rank).
- **Eliminated:** draw calibration (2F), global distribution shape (2B), optimising exact-score/rank as
  targets (2D).
- **Ranked recommendation:** (1) **Reporting-only / honesty — DO NEXT** (GREEN-LANE display; zero model
  risk; operationalises 2D). (2) **Freeze the model math** (adopt "no change" as the stance). (3) Optional
  cheap offline diagnostics to *close* open paths with evidence: 3a high-total feature→total-goals OOS
  regression (kill-test for conditional high-total), 3b temperature/champion frontier sweep. (4) Defer
  market data acquisition (separate data decision; unlock for conditional high-total).
- **"No model change" is now the strongest posture for the math** — paired with reporting improvements.

## Phase 2H — reporting / model-honesty improvements (DISPLAY-ONLY) · commit `6043b88` — DONE & PUSHED
Shipped: **Scorecard** honesty notes + tooltips (EN+FR) — exact-score & scoreline-rank labelled
**diagnostics, not targets**; exact-score near-ceiling note; small-sample (<64 matches) caveat. **Model
Lab → Limitations** "What we tested — and won't chase" block recording the 2B fat-tail rejection, the 2F
draw-calibration non-result, and the 2D/2G model-math freeze.
- **Verification:** full suite **626 passed**; `tests/test_honesty_copy.py` (6); **production math/data/
  config/nav untouched** (`src/wc2026/`, `data/`, `configs/` byte-identical; live blob `bbcd3ef…648271`);
  site **HTTP 200**. Display/copy only — GREEN LANE.
- **Model math remains FROZEN per Phase 2G.** 1D-B nav still deferred.

## Phase 3A — Evidence Lab / model-improvement search (OFFLINE RESEARCH) — DONE · verdict RESEARCH
Doc: `docs/PHASE_3A_EVIDENCE_LAB.md`. Isolated research files only (`src/wc2026/experimental/
match_features.py`, `scripts/exp_feature_search.py`, `outputs/experiments/3A_evidence_lab/`,
`tests/test_match_features.py`). 631 suite passes; **production model/data/config/nav untouched**.
- **First POSITIVE evidence after 2B & 2F:** recent-form features (recent goals-against `ga_diff` +
  points momentum `form_diff`) add **genuine OOS signal beyond Elo-alone** on W/D/L — log-loss −0.0083
  [−0.0126,−0.0041], RPS −0.0025 [−0.0037,−0.0014], Brier −0.0059 (all CIs entirely < 0). Small (~1%)
  but real; features are history-derivable ⇒ no train/serve skew.
- **High-total lever stays DEAD:** derivable features do NOT predict total goals OOS (CIs straddle 0).
  No usable conditioning signal without external data (market totals / xG / lineups — none in-repo as
  time-series).
- **Critical caveat:** baseline was pure-Elo logistic; **production already blends an ML 1X2 layer
  @0.20**, so this may overstate the gain vs the deployed model. **RESEARCH, not READY — do not integrate.**

## Phase 3B — External data access recon (OFFLINE, real keys from .env.yorian) — DONE
Doc: `docs/PHASE_3B_EXTERNAL_DATA_ACCESS_RECON.md`; research files `scripts/research/`,
`outputs/research/phase_3b_external_data/`. Secret-safe (keys never printed/committed; leak scan clean;
`.env.yorian` gitignored). **Auth results:**
- **The Odds API ✅** — 500 req/mo free, 15 soccer markets incl. World Cup (live odds). Historical odds = paid.
- **Sportmonks ✅** — **Pro trial until 2026-07-09**, ~53k req/hr; rich football data (xG/lineups plan-dep, not yet probed). Strongest breadth.
- **API-Football ❌** — rejected on direct + RapidAPI hosts (verify key/product).
- **TheOdds.io ⚠️** — domain ambiguous/times out; **key withheld** (not sent anywhere); confirm provider.
- **Key gap unchanged:** *historical* odds/totals for OOS backtesting still blocked (free tiers = current
  only). Live odds usable **prospectively**, not for backtesting past matches.

## Phase 3C — Sportmonks deep capability probe (OFFLINE) — DONE
Doc: `docs/PHASE_3C_SPORTMONKS_CAPABILITY_PROBE.md`; research `scripts/research/probe_sportmonks_
capabilities.py`, `outputs/research/phase_3c_sportmonks_probe/`. Secret-safe (token never printed/
committed; leak scan clean). Plan: **Pro trial → 2026-07-09, ~53k/hr.** All probes HTTP 200.
- **HEADLINE: historical ODDS confirmed** — 3,748 odds rows on a 2022 fixture; markets incl. 1X2
  (Fulltime Result), Over/Under totals, Asian Handicap; fields incl. `probability` + `winning`
  (settlement). **Unblocks OOS backtesting of market-implied features** (the 2G/3A market anchor).
- **FIFA World Cup = league 732 (6 historical seasons)** + qualifiers (711). Fixtures carry
  **confirmed lineups, events, statistics, referees** historically; squads/players + news confirmed.
- **xG/pressure:** entitled (200, no error) but **EMPTY for the sampled international fixture** →
  coverage for international/WC UNCONFIRMED (RESEARCH, needs coverage kill-test). Expected-lineups
  (type_id mapping) + injuries/sidelined (empty) unclear.
- **READY_FOR_FEATURE_LAB:** historical odds (strongest), lineups, fixtures/leagues, squads.

## Phase 3D — Sportmonks coverage closure (OFFLINE, 6 req) — DONE
Doc: `docs/PHASE_3D_SPORTMONKS_COVERAGE_CLOSURE.md`; research under `outputs/research/phase_3d_*`.
Secret-safe (leak scan clean). **All 3C unknowns closed:**
- **xG CONFIRMED** (corrects 3C): `xGFixture` non-empty for **club 5/5** and **WC-732 2018** (20 metric
  rows); 3C's empty was a CAF-qualifier/older fixture. **Pressure index empty on WC** → WATCHLIST.
- **Odds across WC seasons:** **2018/2022/2026 = full**, 2006/2010/2014 = none. Markets 1X2 + O/U totals +
  Asian Handicap + implied `probability` + `winning` settlement confirmed back to **2018** (819 rows on a
  2018 fixture). ⇒ **3 WCs of odds.**
- **Injuries/sidelined CONFIRMED:** 6 rows with start/end dates + games_missed → historically
  reconstructable.
- **Expected lineups:** Lineup type_id=11; expected-XI is forward-only, not isolated → low priority.
- **Unblocked for OFFLINE OOS:** market-implied features (intl/WC 2018+; small n at tournament level, large
  at match level), xG (club + WC2018+), injuries/availability.

## Phase 3E — market-odds feature lab (OFFLINE) — DONE · verdict **READY_FOR_MODEL_LAB** (with conditions)
Doc: `docs/PHASE_3E_MARKET_ODDS_FEATURE_LAB.md`; data `outputs/research/phase_3e_market_odds_feature_lab/`.
Secret-safe (leak scan clean); production untouched; settlement used only as a leakage diagnostic.
**Frozen offline dataset captured: 188 WC-732 fixtures** (2018: 64 + 2022: 64 with usable 1X2; 2026: 60
O/U-only). Median-bookmaker no-vig 1X2.
- **HEADLINE — market beats the frozen model OOS, beyond bootstrap noise (pooled n=128):** RPS 0.202 vs
  0.234 (Δ−0.032 CI[−0.056,−0.007]), NLL 0.970 vs 1.063 (Δ−0.093 CI[−0.169,−0.012]), Brier 0.570 vs 0.641,
  acc 54.7% vs 47.7%. 2018 significant on both; 2022 directional but within noise. **Best blend α=1.0
  (pure market)** — frozen model adds ~nothing on top. **First clear proper-score-backed candidate** after
  2B/2F/3A failures.
- **Caveats:** n=128 = only 2 WCs; baseline = Elo→DC **not** full Elo→DC→ML@0.20; "use market" = anchoring to
  bookmakers (identity decision). Not leaky (pre-match closing lines; no settlement feature).

## Phase 3F — market vs FULL production baseline (OFFLINE) — DONE · verdict **READY_FOR_MODEL_LAB (confirmed)**
Doc: `docs/PHASE_3F_MARKET_VS_PRODUCTION_BASELINE.md`. No new API calls (reused 3E dataset + ML pickle +
rolling Elo, read-only). **Full production W/D/L reproduced** = `0.8·DC + 0.2·ML` (ML features
`[elo_diff,neutral]`; 128/128 matched). **3E caveat RESOLVED: the ML@0.20 layer does NOT close the gap**
(pooled full-prod RPS 0.2338 ≈ dc-only 0.2341).
- **Market beats FULL production beyond noise (pooled n=128):** RPS 0.202 vs 0.234 (Δ−0.032 CI[−0.055,−0.007]),
  NLL 0.970 vs 1.062 (beyond noise), acc 54.7% vs 47.7%, and **market is BETTER calibrated** (ECE 0.047 vs
  0.109). 2018 significant; 2022 within noise. **Best blend α=1.0 (pure market)** — production adds no
  incremental W/D/L signal here.
- **Guardrail:** market anchoring *improves* calibration (no damage); the real constraint is **identity risk**
  (α=1.0 = "become the bookmaker" — integrate as a principled anchor/blend, not full deferral).
- **Broader international sample = DEFERRED** (no new calls this phase; main remaining evidence gap).

## Phase 3F-B — RPS baseline reconciliation (OFFLINE, no API) — DONE · 3F recommendation PRESERVED
Doc: `docs/PHASE_3F_B_RPS_BASELINE_RECONCILIATION.md`. Explained the 0.2338-vs-0.18/0.19 discrepancy:
**RPS formula + class order identical across 1B/2D/3E/3F**; **3F reconstruction validated** (native
martj42 orientation on the same 128 = 0.2338 exactly; full competitive set reproduces 0.193 = matches 2D).
**0.2338 = WC-final-tournament difficulty, NOT a bug.** Segments: full set 0.191, WC incl. qualifiers 0.179
(≈ live-48 0.180), WC-final 2018+22 0.214 (n=228) / 0.234 (128 odds-subset). Model barely beats uniform
(0.2413) on the 128 → very low skill on hard balanced WC games; market's edge survives apples-to-apples.
**READY_FOR_MODEL_LAB stands** (still gated on 3G generalization).

## Phase 3G — international market generalization (OFFLINE) — DONE · verdict **READY_FOR_INTEGRATION_DESIGN**
Doc: `docs/PHASE_3G_MARKET_GENERALIZATION.md`. Bounded Sportmonks extract (Euro/Copa/AFCON/Asian Cup finals,
2019-2021 editions usable) + reuse WC 3E. Rate-limit-safe; **completed: 39 requests, 0 rate-limited**;
secret-safe; production untouched. Unified eval **n=356** (228 non-WC + 128 WC).
- **Edge GENERALIZES beyond WC:** pooled-ALL RPS 0.186 vs prod 0.212 (Δ−0.025 CI[−0.036,−0.015]); **pooled
  non-WC** 0.177 vs 0.199 (Δ−0.022 CI[−0.032,−0.011]) — both BEYOND noise; market better calibrated
  (ECE 0.050 vs 0.070). Best blend α=1.0.
- **Heterogeneous (informative):** edge largest where the model is weakest — Asian Cup Δ−0.055, WC −0.032,
  AFCON −0.013; **≈ zero on Euro** (Δ−0.004 within noise, blend α=0.8) where the Elo model holds its own.
- **Caveats:** 2023-2025 finals + WC2026 had **no usable 1X2** in-extract (recent intl 1X2 sparse) → era is
  mostly 2018-2022; post-2022 within noise. **LIVE WC2026 1X2 availability UNCONFIRMED = the binding gate.**

## Phase 3H-A — live WC2026 1X2 odds availability (OFFLINE smoke) — DONE · **binding gate CLEARED**
Doc: `docs/PHASE_3H_A_LIVE_ODDS_AVAILABILITY.md`. Keys parsed directly from `.env.yorian` (never os.getenv);
secret-safe; production untouched. **Two providers can supply live pre-match WC2026 1X2:**
- **The Odds API ✅ READY** — `soccer_fifa_world_cup`, **15/15 upcoming events have h2h (1X2)**; quota 499/500.
- **Sportmonks ✅ READY** — league 732 upcoming: **19/41 fixtures have Fulltime Result (market 1)** odds.
  Resolves the 3E/3G "empty" — that was *completed/settled* fixtures; pre-match odds DO exist for upcoming.
- **TheStatsAPI ⚠️ WATCHLIST** — auth ok (`.env.yorian` key), but `matches/{id}/odds` = 404 for scheduled
  matches (finished-match odds only; no pre-match 1X2).
- **Old-key note:** `.env` (repo root) holds a DIFFERENT/old `THESTATSAPI_KEY` — treated invalid, **not
  used**; only `.env.yorian` used. No committed key value in tracked files.

## Phase 3H-B — market-odds integration DESIGN (DESIGN ONLY) — DONE · verdict **READY_FOR_MODEL_LAB_PROTOTYPE**
Doc: `docs/PHASE_3H_B_MARKET_INTEGRATION_DESIGN.md`. No code/provider calls/secrets.
- **Provider:** primary **The Odds API** (clean h2h, full upcoming coverage, quota-efficient bulk endpoint,
  no trial dependency); fallback/cross-check **Sportmonks** (same as historical pipeline, needs paid plan
  post-2026-07-09). Disagreement → consensus if close, else more-books/fresher; neither → frozen model.
- **De-vig:** FROZEN 3E–3G method (median-bookmaker no-vig, ≥3 books, lock = kickoff−15min, stale-skip).
- **Blend:** reject α=1.0 (bookmaker wrapper). Prototype = conservative fixed α; target = **regime-aware α**
  (mirror existing `ml_weight_mode:"dynamic"`); **cap α≤0.6** (identity); α fit/validated OOS, never hand-set.
- **Grid:** reuse existing `_reweight_flat_to_wdl(flat, target=blended W/D/L)` — same path as the ML layer; no
  scoreline redesign.
- **Champion guardrail (critical):** sharper W/D/L can re-concentrate champions (the thing ×0.55 fixed) →
  re-run 4-WC walk-forward; top-3 concentration in band, champion-Brier non-regression, conservation; cap α /
  keep temperature post-blend.
- **Identity:** present as **market-informed** (capped blend, show both numbers) — never a bookmaker wrapper.
- **Validation before prod:** offline replay → champion-MC → **live shadow mode** → calibration → fallback.
- **Verdict:** build an OFFLINE lab prototype + shadow logger (flagged, experimental pkg); NOT production-ready
  (champion-MC unvalidated, α untuned, shadow not run, 48-team map incomplete, identity = Yorian's call).

## Phase 3I — market-informed Model-Lab prototype (OFFLINE) — DONE · verdict **READY_FOR_SHADOW_MODE** (gated)
Doc: `docs/PHASE_3I_MARKET_MODEL_LAB_PROTOTYPE.md`. Isolated: `src/wc2026/experimental/market_blend.py`,
`scripts/research/market_model_lab_prototype.py`, `tests/test_market_blend.py` (8 tests, incl. reweight
parity vs production `_reweight_flat_to_wdl`); 639 suite passes; production untouched; no API/secrets.
- **Every capped blend beats production beyond noise (n=356):** α=0.25 RPS 0.2012 (Δ−0.010), α=0.40 0.1963
  (Δ−0.015), **α=0.60 0.1912 (Δ−0.020 CI[−0.027,−0.014])** — all RPS+NLL beyond bootstrap noise; both WC and
  non-WC segments beyond noise. α=0.60 captures ~80% of the market gain with 40% model voice and **better
  calibration** (ECE 0.058 vs 0.070). Tiny α (0.25) slightly *worsens* ECE → prefer moderate α 0.4–0.6.
- **Regime-aware ≈ fixed α=0.6 here** (balanced tournaments saturate entropy) → not yet proven valuable.
- **Market-only (α=1.0) = oracle reference only, rejected** (bookmaker wrapper).
- **Champion guardrail = PROXY only:** blend sharpens W/D/L (mean conf 0.474→0.517 at α=0.6) → modest
  re-concentration RISK. **FULL guardrail UNTESTABLE from match-level data — the 100k-MC-over-bracket harness
  (champion top-3/Brier vs baseline) is the MISSING gating deliverable.**

## Phase 3J — champion-MC guardrail (OFFLINE, controlled synthetic) — DONE · verdict **READY_FOR_MODEL_LAB_ONLY** (downgrade)
Doc: `docs/PHASE_3J_CHAMPION_MONTE_CARLO_GUARDRAIL.md`. Full replay infeasible (no market for hypothetical
matchups; champion-Brier not computable) → synthetic 32-team bracket + sharpening proxy (T=1.672 fit to real
market conf 0.558; proxy-blend conf ≈ real-blend, validated). N=20k.
- **NAIVE capped blends ALL FAIL the champion guardrail** — concentration compounds: α=0.25 top-3 +5.1pp,
  0.40 +7.6pp, 0.60 +11.9pp (entropy drops 0.23–0.53 bits). 3I's match-level proxy understated this. This is
  exactly the risk ×0.55 temperature controls.
- **Champion-safe path EXISTS — re-temper mitigation:** de-sharpen the blend back to baseline conf before the
  champion MC (S=0.794@0.4, 0.718@0.6) → **PASS** (top-3 ≈ baseline). And it **keeps ~73% of the match RPS
  gain** (0.6+retemper RPS 0.1985 vs prod 0.213; naive 0.1915). Market value = directional re-ranking (keep)
  + extra sharpness (drop for champions).
- **Verdict downgraded from 3I's gated-shadow to READY_FOR_MODEL_LAB_ONLY:** naive blend unsafe for champions;
  re-temper is the lab direction but tuned on a PROXY, unvalidated vs real per-matchup odds. Do NOT advance to
  shadow serving of any blended tournament/champion number yet.

## Phase 3K — champion-safe blend policy (OFFLINE lab) — DONE · verdict **READY_FOR_MODEL_LAB_ONLY** (policy defined)
Doc: `docs/PHASE_3K_CHAMPION_SAFE_BLEND_POLICY.md`. `experimental/market_temperature.py` (6 tests; 645 suite).
Policy = blend (α≤0.6) then temper W/D/L to baseline sharpness (`S` via match-confidence-restore), then
reweight grid via `_reweight_flat_to_wdl`. α×S grid (match-level on 356 + champion on the 3J synthetic bracket).
- **Naive (S=1) FAILS at every α; `match_conf_restore` PASSES at every α** (champion top-3 within ~1pp of
  baseline 0.517; all 14 teams ≥1%) while retaining **71–83%** of the match RPS gain (all beat prod beyond noise).
- **Candidates:** conservative α=0.25,S=0.903 (RPS 0.2039, 83%); **balanced α=0.40,S≈0.83 (0.2005, 77%)**;
  aggressive α=0.60,S=0.746 (0.1976, 71%).
- **Proxy-only validation → stays MODEL-LAB-ONLY** (not shadow/prod). A champion-safe policy now EXISTS &
  characterised (upgrade over 3J). Shadow needs: real per-matchup odds for a resolving bracket, real
  champion-Brier, S re-tuned on real data + the 48-team format.

## Next step
**No further offline lab step is required to characterise the signal — the evidence chain (3E→3K) is
complete.** Remaining work is GATED on Yorian product/cost decisions and live data, not on more research:
(a) **identity decision** (market-informed vs independent); (b) **provider/cost** (Sportmonks-paid vs Odds
API); (c) if both go ahead → a separate, explicitly-approved **shadow-mode design** (serves nothing; collects
real per-matchup odds to validate the champion side with policy α≈0.40, S≈0.83). Until then: model math
FROZEN, nothing integrated. Standing asks: verify API-Football key; confirm "TheOdds.io". (1D-B nav deferred.)
