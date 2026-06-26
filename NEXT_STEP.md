# NEXT_STEP — the ONE approved next action

> Read `HANDOFF.md` first. This file defines **exactly one** next action. Do not exceed it.
> Do not start any later phase. Plan + show files/commands + get approval BEFORE editing; do not
> push until explicitly approved.

## ✅ Phase 1D-A — DONE & PUSHED · commit `37a743f`
Low-risk display-only a11y polish: invisible utility iframes labelled + `aria-hidden`; cookie banner
mobile safe-area / `max-height` / `overflow` / `role="region"`; `tests/test_a11y_iframe_consent.py`
(5 tests). 586 tests pass. Model/config/forecast/scorecard/data byte-identical to baseline. Site
HTTP 200 post-deploy. Contrast (already AA) and typography (already consolidated) deliberately left
untouched. See HANDOFF.md "Completed phases".

## ✅ Phase 1D-B PLANNING — DONE · memo `docs/PHASE_1D-B_NAV_PLAN.md`
Read-only investigation complete. 3 options analysed (A: ARIA overlay / B: `st.navigation` migration /
C: custom button nav). **Recommendation = DEFER implementation** — proper fix (B) is a RED-LINE nav
rewrite disproportionate to an "announced-wrong" (not unusable) nit; cheap fix (A) is unverifiable
a11y theater. No code touched; `st.radio` + `_goto`/`page_nav`/`dna_sel` plumbing untouched.

## ✅ Phase 1E — metric/tooltip clarity — DONE · commit `8b09044`
Plain-language tooltips for ECE / NLL / ρ / `log_base` / headline Brier + a glossary caption
(display-only, GREEN LANE). `tests/test_metric_tooltips.py` (6 tests). 592 tests pass. No model /
config / data change.

## ✅ Phase 2A — Model improvement planning — DONE · memo `docs/PHASE_2A_MODEL_PLAN.md`
Read-only analysis off the live 48-match audit. **Diagnosis:** W/D/L signal solid (acc 58.3%, RPS
0.180 vs 0.229); scoreline **tail too thin** (5+ goals mean rank 18.0 vs ~4) = biggest gap; **draw
recall 0/14 partly a decision-rule artifact**. **Recommendation:** first experiment = offline
overdispersion / fat-tail scoreline distribution test. No model/config/data/probability change.

## ✅ Phase 2B — tail-overdispersion experiment (OFFLINE) — DONE · commit `fb739a8` — NEGATIVE result
NegBin vs Poisson on martj42 2010-2025 (10,555 matches). `NegBin(r=∞)==Poisson==prod _build_dc_flat`
(15 equivalence tests; 607 suite passes). **0/27 candidates pass.** Fattening the tail buys only ~4%
rel on 5+ goals rank while degrading Brier/RPS/NLL/ECE + dropping top-3 coverage — bad trade.
**Tail overdispersion alone is NOT worth a production change.** Production files byte-identical.

## ✅ Phase 2C — full weakness & solution research MAP (RESEARCH ONLY) — DONE · `docs/PHASE_2C_FULL_MODEL_RESEARCH_MAP.md`
15 research lenses + full weakness/solution maps. Grounded: `expected_goals` is **Elo-only** (no
market/lineups/style/incentives in μ). Honest findings: draw recall 0/14 ≈ decision-rule artifact;
exact top-1 8.3% ≈ entropy floor; much of rank weakness is metric-induced (rank ↔ calibration
tension); validation rests on n≈4 tournaments. **Best next move = NOT a model change.**

## ✅ Phase 2D — Objective & ceiling audit (OFFLINE) — DONE · commit `6d04da3`
Report: `outputs/experiments/2D_objective_ceiling/`. **Key decisions (validated weakness map):**
- Exact-score top-1/top-3 → **do NOT optimize directly** (top-1 ceiling ~12.7%; top-3/5 at ceiling).
- Scoreline rank → **demote to DIAGNOSTIC, not a target** (aggregate ~1 above ceiling; signal only in
  minority high-total bucket; optimizing it trades against W/D/L calibration).
- Draw recall 0/14 → **decision-rule artifact** (ceiling recall ≈ 0 under argmax).
- **Real remaining weaknesses:** (a) high-total/blowout **conditional** ranking (5+ real 21.78 vs
  ceiling 7.03, ~17% of matches), (b) mild **draw OVER-prediction** on robust historical data
  (predicted ≈0.255 > actual ≈0.219; −3.6pp gap) — **[corrected by 2F]**; the live-48 hinted
  under-prediction but was noise, (c) mild **W/D/L under-confidence** (over-dispersed; sharpening
  fights champion temperature).
- **Phase 2B fat-tail FAILED → do NOT globally fatten the distribution.** Any high-total fix must be
  a *conditional* lever, gated on not regressing low-total games or W/D/L.

## ✅ Phase 2E — next experiment selection (SELECTION ONLY) — DONE · `docs/PHASE_2E_EXPERIMENT_SELECTION.md`
Compared 5 candidates. **Recommendation = Candidate 2, Draw probability calibration** (only real +
cheap + low-risk + champion-safe + no-new-data + fast-kill lever). **Deferred:** conditional high-total
mean (no proven signal; gate behind feature kill-test/market data), market anchor (data-blocked; it
gates the conditional-mean path), temperature sharpening (diagnostic-only sweep; shipping reopens the
champion over-concentration tension). **Reporting-only = parallel, zero-risk, always-worth-doing.**

## ✅ Phase 2F — draw calibration experiment (OFFLINE) — DONE · commit `3cc31b6` — INCONCLUSIVE (not shipped)
Calibrators A (γ) + B (isotonic), walk-forward OOS on martj42 2010-2025 (pooled n=5,713; 7 tests; full
suite 620). Report: `outputs/experiments/2F_draw_calibration/`.
- **Sign correction:** fitted **γ ≈ 0.84 (<1)** ⇒ model mildly **OVER-predicts** draws on robust
  historical data; the earlier "under-calibration" framing (from the noisy live-48) was wrong direction.
- A/B slightly improve OOS RPS/Brier/ECE but **NLL gain is within noise** → pre-registered gate NOT met;
  W/D/L mass shift (~4–5%) also exceeds the 3% champion proxy. **INCONCLUSIVE/FAIL for both.**
- **Decisions:** do NOT ship draw calibration · do NOT treat draw recall as a model target · do NOT
  pursue draw calibration further unless new evidence appears.

## ✅ Phase 2G — next experiment reassessment (ANALYSIS ONLY) — DONE · `docs/PHASE_2G_EXPERIMENT_REASSESSMENT.md`
**Verdict: another model-MATH experiment is NOT justified now.** 2D ceiling audit + 2B & 2F failures ⇒
the model is near its floor; the only real remaining signals are data-blocked (market→conditional
high-total), champion-entangled (temperature), or aimed at a demoted diagnostic (rank).
- **Ranked:** (1) **Reporting-only / honesty — DO NEXT** (GREEN-LANE display, zero model risk).
  (2) **Freeze the model math** ("no change" stance). (3) Optional cheap offline diagnostics to *close*
  open paths with evidence: 3a high-total feature→total-goals OOS regression, 3b temperature/champion
  frontier sweep. (4) Defer market data acquisition (unlock for conditional high-total).
- **Eliminated:** draw calibration (2F), global distribution shape (2B), exact-score/rank as targets (2D).
- **"No model change" is the strongest posture for the math**, paired with reporting improvements.

## ✅ Phase 2H — reporting / model-honesty improvements (DISPLAY-ONLY) — DONE & PUSHED · commit `6043b88`
Scorecard honesty notes + tooltips (EN+FR): exact-score & scoreline-rank = **diagnostics, not targets**;
near-ceiling note; small-sample (<64) caveat. Model Lab Limitations "What we tested — and won't chase"
block (2B rejected · 2F not shipped · 2D/2G math frozen). **626 passed; production math/data/config/nav
untouched; site HTTP 200.** Model math remains FROZEN per 2G.

## ✅ Phase 3A — Evidence Lab / model-improvement search (OFFLINE RESEARCH) — DONE · verdict **RESEARCH**
Doc: `docs/PHASE_3A_EVIDENCE_LAB.md`; isolated research files only; 631 suite passes; production
model/data/config/nav untouched. **First positive evidence after 2B & 2F:** recent-form features
(`ga_diff` defensive form + `form_diff` momentum) add **genuine OOS W/D/L signal beyond Elo-alone**
(log-loss −0.0083, RPS −0.0025, Brier −0.0059, all CIs entirely < 0; pooled OOS n=6,961). Small (~1%)
but real, history-derivable (no train/serve skew). **High-total/total-goals lever stays DEAD** (no OOS
signal). **Caveat:** baseline was pure-Elo logistic; production already has an ML 1X2 layer @0.20, so
the gain may not survive vs the deployed model ⇒ **RESEARCH, not READY; do not integrate.**

## ✅ Phase 3B — External data access recon (OFFLINE, real keys) — DONE · `docs/PHASE_3B_EXTERNAL_DATA_ACCESS_RECON.md`
Secret-safe smoke tests (keys from `.env.yorian`, never printed/committed; leak scan clean). **The Odds
API ✅** (500/mo free, World Cup odds; historical=paid) · **Sportmonks ✅** (Pro trial → 2026-07-09, ~53k/hr,
rich data) · **API-Football ❌** (rejected both hosts; verify key) · **TheOdds.io ⚠️** (ambiguous domain;
key withheld). Key gap unchanged: *historical* odds/totals for OOS backtesting still blocked on free tiers.

## ✅ Phase 3C — Sportmonks deep capability probe (OFFLINE) — DONE · `docs/PHASE_3C_SPORTMONKS_CAPABILITY_PROBE.md`
All probes HTTP 200 (Pro trial → 2026-07-09). **Historical ODDS confirmed** (3,748 rows/fixture; 1X2 +
O/U totals + Asian Handicap; `probability` + `winning` settlement) — unblocks OOS market-feature
backtesting. **FIFA WC = league 732 (6 seasons)**; historical lineups/events/statistics/referees/squads
confirmed. **xG/pressure entitled but EMPTY for the sampled international fixture** (coverage unconfirmed);
expected-lineups + injuries unclear. READY_FOR_FEATURE_LAB: odds, lineups, fixtures, squads.

## ✅ Phase 3D — Sportmonks coverage closure (OFFLINE, 6 req) — DONE · `docs/PHASE_3D_SPORTMONKS_COVERAGE_CLOSURE.md`
All 3C unknowns closed. **xG CONFIRMED** (club 5/5, WC-732 2018 = 20 rows; 3C's empty was a qualifier/old
fixture); **pressure index empty on WC → WATCHLIST**. **Odds: WC 2018/2022/2026 full** (2006/2010/2014 none);
1X2 + O/U + Asian Handicap + probability + settlement back to 2018 ⇒ **3 WCs**. **Injuries/sidelined
CONFIRMED** (dates + games_missed, historically reconstructable). Expected-XI forward-only (low priority).

## ✅ Phase 3E — market-odds feature lab (OFFLINE) — DONE · verdict **READY_FOR_MODEL_LAB (conditional)**
Doc: `docs/PHASE_3E_MARKET_ODDS_FEATURE_LAB.md`. Frozen 188-fixture WC dataset captured (2018/2022 = 128
usable 1X2; 2026 O/U-only). **Market beats the frozen model OOS beyond bootstrap noise (pooled n=128):**
RPS 0.202 vs 0.234 (CI[−0.056,−0.007]), NLL 0.970 vs 1.063 (CI[−0.169,−0.012]), acc 54.7% vs 47.7%; best
blend α=1.0 (pure market). 2018 significant, 2022 within noise. Not leaky (pre-match lines; settlement
diagnostic only). **First proper-score-backed win after 2B/2F/3A.** Caveats: 2 WCs only; baseline = Elo→DC
not full Elo→DC→ML@0.20; "use market" = a product-identity decision.

## ✅ Phase 3F — market vs FULL production baseline (OFFLINE) — DONE · verdict **READY_FOR_MODEL_LAB (confirmed)**
Doc: `docs/PHASE_3F_MARKET_VS_PRODUCTION_BASELINE.md`. Full production W/D/L reproduced (`0.8·DC + 0.2·ML`;
128/128 matched). **ML@0.20 does NOT close the gap** (full-prod 0.2338 ≈ dc 0.2341). **Market beats FULL
production beyond noise (pooled n=128):** RPS 0.202 vs 0.234 (CI[−0.055,−0.007]), NLL 0.970 vs 1.062, acc
54.7% vs 47.7%, ECE 0.047 vs 0.109 (market better calibrated). Best blend α=1.0 (pure market). 2018
significant; 2022 within noise. Anchoring *improves* calibration; real constraint = **identity risk**.
**Phase 3F-B reconciliation (DONE):** RPS formula + class order identical across 1B/2D/3E/3F; 3F
reconstruction validated (native recompute = 0.2338 exactly; full set reproduces 0.193). **0.2338 = WC
final-tournament difficulty, not a bug** — prior 0.18/0.19 were easier samples. Market edge survives;
recommendation PRESERVED. Doc: `docs/PHASE_3F_B_RPS_BASELINE_RECONCILIATION.md`.

## THE NEXT ACTION: Phase 3G — bounded international generalization (SEPARATE APPROVAL; not started)
Gating evidence: does the market edge hold **beyond 2 World Cups**? Bounded Sportmonks extract of
international odds 2018+ (Euro / Copa / Nations League / WC qualifiers — find league ids, document, cap
requests), compare **market vs FULL production** OOS with bootstrap CIs at MATCH level.
- **Allowed:** `scripts/research/`, outputs under `outputs/research/phase_3g_*`, reuse 3E/3F harness.
  **FORBIDDEN:** ❌ production model/app/data/config change, ❌ integration, ❌ key printed/committed,
  ❌ betting exec, ❌ scraping behind login, ❌ quota-rotation, ❌ uncontrolled crawl.
- **Only after 3G clears** does Model-Lab integration get considered — and it must add: champion-calibration
  guardrail (W/D/L → MC), an **identity-preserving blend weight** (not α=1.0), live-odds availability +
  fallback for WC2026. Prudent before 2026-07-09 trial expiry: capture any new odds extract offline.
- **Parallel asks for Yorian:** verify the API-Football key product/host; confirm the real "TheOdds.io".

## ALSO OPEN (deferred) — Phase 3A → production W/D/L head-to-head
Test whether the recent-form signal survives **on top of the actual production W/D/L** (Elo→DC→ML@0.20),
offline. If it beats production OOS beyond noise → **READY_FOR_MODEL_LAB** (separate approved integration
with a champion guardrail). If not → **WATCHLIST/KILL**. No production change.

### Optional (parked) — evidence-closing diagnostics
- **High-total lever:** closed by 3A unless external data (market totals / xG / lineups) is acquired.
- **3b temperature/champion frontier sweep** (diagnostic-only) remains available if requested.

### 1D-B nav — STILL DEFERRED (unchanged)
No approved implementation action. Phase 1D-B implementation is **DEFERRED** pending a trigger (real
SR-user/audit report, better Streamlit native nav a11y, or a broader nav redesign) OR an explicit
Yorian decision to implement Option A/B/C. Until then, do NOT touch the nav. (Background on the
original investigation request kept below for context.)

### (archived) original 1D-B planning brief
Investigate the sidebar navigation accessibility issue Talos flagged (HIGH — "navigation exposed as
radio controls in the a11y tree"). The nav is `st.radio(..., key="page_nav")` in `app.py` (search
`key="page_nav"`), wired to `_goto` / `page_nav` cross-page plumbing.

### Allowed (1D-B planning)
- **Read-only investigation** of `app.py` nav (`st.radio`, `key="page_nav"`, `_goto`, session-state
  plumbing) and of the Streamlit a11y options (st.page_link, st.tabs, st.navigation/st.Page, custom
  HTML nav component, injected ARIA attributes).
- **Propose 2–3 options** to improve nav screen-reader semantics (announce "navigation" + link/button
  names + `aria-current`), each with what it touches and its blast radius.
- **Estimate risk** per option (does it touch the `_goto`/`page_nav` plumbing? deep-link behaviour?
  query-params? test impact?).
- **Recommend** whether to implement now or defer — and if defer, why.
- Write the plan into `HANDOFF.md` / a new doc; do NOT change app behaviour.

### FORBIDDEN in 1D-B planning
- ❌ No navigation rewrite. ❌ No `st.radio` replacement. ❌ No `app.py` implementation changes.
- ❌ No model math / probabilities / forecast / scorecard changes.
- ❌ No config/params/data file changes.
- ❌ Do not break the existing `_goto` / `page_nav` deep-linking.

### Forbidden files (do not modify for 1D-B)
`app.py` (no behaviour changes — planning only) · `data/model_stack_config.json` ·
`data/elo_calibrated_params.json` · `data/elo_live_params.json` ·
`data/wc2026_live.json` (must stay blob `bbcd3ef82b520034bd51f8fce58d41c49e648271`) ·
`src/wc2026/calibrated_elo_model.py` · `src/wc2026/scorecard.py`.

### Deliverable (1D-B planning)
A written options memo (2–3 options + risk + recommendation). No code. Implementation of the chosen
option becomes a separate, explicitly-approved Phase 1D-B-impl.

### Working protocol (now in effect)
- **GREEN LANE** (no per-step approval): docs-only, tests-only, small display-only UI fixes, a11y
  micro-fixes, read-only audit tooling → implement → test → commit → push → report.
- **RED LINE** (ASK FIRST): model math · probabilities · forecast generation · scorecard calc ·
  model/config/data files · secrets/API keys · delete ops · nav rewrite / `st.radio` replacement ·
  broad `app.py` refactor · visible product redesign.

## What must NOT be inferred from memory (verify from the repo)
- **Current HEAD / phase / commits** → `git log --oneline -8`, `git tag`. (HEAD at writing: `42e9ee2`;
  latest implementation commit = `37a743f` = Phase 1D-A.)
- **Model numbers** (β, ρ, log_base, ML weight, metrics) → read `data/elo_calibrated_params.json`,
  `configs/model_version.json`, `CHANGELOG_MODEL.md`, latest `outputs/audit/live_metric_snapshots/*.json`.
  Do not quote remembered values.
- **`data/wc2026_live.json`** is a frozen 6-match fixture/seed; the live **48-match** data is NOT in
  the repo — it is assembled at runtime by `live_engine.fetch_live_state()` from providers. Keep the
  blob at `bbcd3ef82b520034bd51f8fce58d41c49e648271`.
- **Live providers / API keys** live in local `.env` and Render env — never commit or print keys.
  ESPN is the authoritative live source (`src/wc2026/providers/espn.py`).
- The nav is intentionally still `st.radio` — its "radio semantics" issue is KNOWN and DEFERRED, not
  forgotten. Do not "helpfully" rewrite it.
