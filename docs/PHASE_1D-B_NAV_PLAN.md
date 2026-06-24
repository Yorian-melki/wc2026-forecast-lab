# Phase 1D-B — Navigation accessibility: options memo (PLANNING ONLY)

> Read-only investigation. **No implementation.** `st.radio` nav + all routing plumbing untouched.
> Status: planning complete · **recommendation = DEFER implementation** (see §5).
> Verified against repo at the time of writing (Streamlit 1.56.0).

## 1. Current nav implementation
- **Widget:** `app.py:792-793` — `st.radio("nav", list(NAV.keys()), format_func=…,
  label_visibility="collapsed", key="page_nav")`, inside `with st.sidebar:` (`app.py:760`).
- **Pages:** 11 entries in the `NAV` dict (`app.py:784-791`) — stable emoji keys
  (e.g. `"🎯 Match Predictor"`) → translated display labels via `format_func`.
- **Dispatch:** one `if/elif page == "<stable key>"` chain across 11 sites (`app.py:816`–`2668`).
  The radio's return value *is* the router.
- **Cross-page deep-linking:** in-app only, via a non-widget session key `_goto`, copied onto
  `page_nav` *before* the widget renders (`app.py:564-568`). Three setters: match card → Match
  Predictor (`app.py:1206`); H2H team A/B → Nation DNA (`app.py:1525-1527`, also sets `dna_sel`).
- **No URL query-param routing** (`grep query_params` = none). There is **no shareable / back-button
  URL state** to preserve — the only routing contract is `page_nav` + `_goto` + `dna_sel` in
  session state.

## 2. Why Talos flags it (HIGH)
`st.radio` renders as `role="radiogroup"` with 11 radio options. A screen reader announces
*"radio button, 1 of 11"* (a form-choice semantic) instead of *"navigation"* with link/menuitem
names and `aria-current="page"` for the active route. It is a **semantics mismatch, not an
operability bug**: radios are natively keyboard-operable (arrow keys) with a visible focus ring.
Real-world harm = "announced wrong," not "unusable."

## 3–4. Options & risk

### Option A — ARIA overlay on the existing radio (inject CSS/JS, like 1D-A)
Set `role="navigation"`/`aria-label` on the radiogroup container; add `aria-current="page"` to the
selected option. Keep `st.radio` and all plumbing. Display-only, reversible, no router change.
**Risk: low-ish but fragile.** Overriding ARIA on a *composite* widget is brittle — unless every
child radio role is also overridden you get a half-relabeled control that can confuse SR users
*more* than a consistent radiogroup. Streamlit DOM (`data-testid="stRadio"`) is fairly stable but
not contractual. **No automated way to verify SR output → cannot prove acceptance.**

### Option B — Migrate to `st.navigation` + `st.Page` (proper Streamlit multipage nav)
Renders a real `<nav>` with links; Talos-correct (navigation semantics, `aria-current`, keyboard).
**Risk: high.** Full app restructure: the 11 `if/elif` branches become page callables/files, the
`with st.sidebar` nav is replaced, and the `_goto`/`page_nav`/`dna_sel` plumbing
(`app.py:564-568`, `1206`, `1525-1527`) must be re-expressed (likely via `st.switch_page` +
state). `tests/test_no_nan_ui.py` iterates "all 11 pages" off the current dispatch → needs rework.
**This is a RED LINE nav rewrite, not a fix.**

### Option C — Custom button/link nav (replace the radio with `st.page_link`-style / `st.button`s)
Real `<button>`/`<a>` semantics without the full multipage migration.
**Risk: medium-high.** Removes the `page_nav` widget → the `_goto`→`page_nav` bridge (`app.py:568`)
and the 3 setters must be rewired; needs active-state styling + `aria-current` by hand; 11 buttons
reflow the sidebar (mild visual change). Still touches the router.

## 5. Recommendation — DEFER implementation
- **B is disproportionate** — a full nav rewrite (RED LINE) to fix an *announcement* nit on a niche
  analytics lab whose nav is already keyboard-operable and focus-visible.
- **A is the trap** — looks low-risk but ARIA-patching a composite radiogroup can produce a *worse*,
  half-relabeled state, and there is **no automated check** to confirm it helps a screen reader.
  Shipping it unverified = a11y theater, violates "preuve > plan."
- **No URL-routing safety net** → any router change (B/C) carries real regression risk to the
  `_goto` deep-links for modest benefit.
- **Defer until a trigger:** (a) a real screen-reader user/audit reports it as a blocker, (b)
  Streamlit ships better native nav a11y, or (c) a broader nav redesign happens anyway — then do
  **B** properly *with manual VoiceOver/SR verification*. If something is wanted now, **A** is the
  only GREEN-LANE-sized move, but only with an explicit "best-effort, unverified" label and a manual
  VoiceOver check before claiming it works.

## 6. Files that would be touched *if* implemented later
- **Option A:** `app.py` — one injected CSS/JS block near `app.py:792` (or a small helper in
  `src/wc2026/`); no dispatch/plumbing change. + new `tests/test_*` static assertion. *(Lowest.)*
- **Option B:** `app.py` extensively — 11 dispatch branches (`816`–`2668`), sidebar nav block
  (`760-793`), `_goto`/`page_nav` bridge (`564-568`), the 3 `_goto`+`dna_sel` setters (`1206`,
  `1525-1527`); likely new `pages/` modules; rework of `tests/test_no_nan_ui.py`. *(Largest.)*
- **Option C:** `app.py` — sidebar nav (`792-793`) + `_goto`→`page_nav` bridge (`568`) + rewire the
  3 setters; keep the dispatch chain. + active-state styling. *(Medium.)*
