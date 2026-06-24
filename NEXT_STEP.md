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

## THE NEXT ACTION: NONE APPROVED — awaiting Yorian's decision on 1D-B
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
