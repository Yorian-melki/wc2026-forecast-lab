# NEXT_STEP — the ONE approved next action

> Read `HANDOFF.md` first. This file defines **exactly one** next action. Do not exceed it.
> Do not start any later phase. Plan + show files/commands + get approval BEFORE editing; do not
> push until explicitly approved.

## THE NEXT ACTION: Phase 1D-A only — low-risk accessibility / UI polish

Display/markup-only accessibility fixes from the Talos audit
(`handoff/wc2026_claude_code_handoff_v3/12_external_audits/TALOS_UI_UX_REPORT.md`) that do NOT
restructure navigation and do NOT touch the model.

### In scope (1D-A) — pick from these only
1. **Iframe title** — the live spotlight / analytics `components.html` iframe is exposed as
   "st.iframe". Give it a descriptive `title` (e.g. "WC2026 live dashboard") or hide decorative
   iframes from the a11y tree.
2. **Contrast tokens** — lift muted/teal microcopy + badge colors toward WCAG AA (≥4.5:1 for small
   text) via the existing CSS variables. No layout change.
3. **Cookie consent banner** — semantic `<button>`s, non-obstructive on mobile (safe-area), respect
   reduced motion. (Find it first; it's injected by the analytics/consent code.)
4. **Typography consolidation** — one primary UI font; reserve JetBrains Mono for code/figures only;
   no accidental monospace in prose. Centralize in CSS tokens.
5. (Optional, if trivial & display-only) **beginner metric tooltips** via `help=`/expanders for
   RPS / ECE / NLL / λ / β / entropy / Dixon-Coles.

### EXPLICITLY FORBIDDEN in 1D-A (do NOT do these now)
- ❌ **Navigation rewrite / `st.radio` replacement.** The sidebar nav is `st.radio(..., key="page_nav")`
  at `app.py` (search `key="page_nav"`). Talos flags its radio semantics, BUT replacing it
  (st.page_link / st.tabs / custom component) is broad + risky + would touch the `_goto`/`page_nav`
  cross-page navigation plumbing. **Deferred to a later, separately-approved phase (1D-B).** Leave
  the nav exactly as is.
- ❌ Any model math / probabilities / forecast generation / scorecard calculation change.
- ❌ Any change to config/params/data files.
- ❌ Visual redesign / layout restructure beyond a11y tokens.
- ❌ Pushing without explicit approval.

### Allowed files
- `app.py` — only: the global CSS/style block (contrast & typography tokens), the iframe `title`
  argument, the cookie-banner markup, optional `help=` tooltips. Display-only edits.
- New `tests/test_*.py` (e.g. an a11y/contrast or iframe-title smoke test).
- (If the cookie banner lives in `src/wc2026/web_analytics.py`, that file is allowed **for markup
  only** — semantic buttons / title — never for model/data logic.)

### Forbidden files (do not modify)
`data/model_stack_config.json` · `data/elo_calibrated_params.json` · `data/elo_live_params.json` ·
`data/wc2026_live.json` (must stay blob `bbcd3ef82b520034bd51f8fce58d41c49e648271`) ·
`src/wc2026/calibrated_elo_model.py` · `src/wc2026/scorecard.py` · the `st.radio` nav.

### Tests to run (before commit)
```
PYTHONPATH=src .venv/bin/python -m py_compile app.py
WC2026_DISABLE_PERSIST=1 PYTHONPATH=src .venv/bin/python -m pytest tests/test_no_nan_ui.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q        # expect 581+ passed
# then: confirm model/config/forecast/scorecard == baseline tag, and wc2026_live blob unchanged
git restore data/wc2026_live.json   # AppTest may mutate it; always restore to bbcd3ef…
```

### Risks
- Streamlit limits DOM control: a11y fixes are best-effort via injected CSS/attributes; some Talos
  items (esp. nav roles) can't be fully fixed without a custom component → that's why nav is deferred.
- The countdown/analytics use `st.components.v1.html` (deprecation-warned but works on Streamlit 1.56).
- Render free tier: ~10s page loads under throttled CPU — not a code bug; don't "fix" by changing logic.
- AppTest with live keys can write `data/wc2026_live.json` → always `git restore` it.

### Rollback strategy
- Commit is additive/display-only → `git reset --hard HEAD~1` (if unpushed) or `git revert <sha>`.
- Model rollback (not relevant to 1D-A): `git checkout model-baseline-v0.6.93-ml20-dc -- <files>`
  or `cp configs/archive/v0.6.93-ml20-dc__*.json data/…`, then `pytest`.

### Done criteria (1D-A)
- Targeted a11y items shipped; nav untouched; no raw `nan` regression; `pytest` ≥ 581 passed;
  model/config/forecast/scorecard byte-identical to baseline; site loads (HTTP 200) after deploy;
  "probabilities, not predictions" + honesty copy intact.

## What must NOT be inferred from memory (verify from the repo)
- **Current HEAD / phase / commits** → `git log --oneline -8`, `git tag`. (HEAD at writing: `4429f8f`.)
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
