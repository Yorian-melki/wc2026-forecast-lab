# NEXT SESSION BOOT — WC2026 Forecast
# Created: 2026-06-10
# Read this first in any new session.

---

## A. EXACT COMMAND TO PASTE TOMORROW

Copy and paste this VERBATIM into Claude Code at the start of the session:

```
Read session_handoff/PROJECT_CONTEXT_LOCK.md, session_handoff/NEXT_SESSION_BOOT.md, session_handoff/STATE_VERIFICATION.md, and session_handoff/NEXT_ACTION_PROMPT.md. Do not act yet. First summarize the current state, risks, and recommended next action. Then wait for my confirmation.
```

**Do not ask Claude to do anything else until it has read all 4 files and confirmed the state.**

---

## B. 10-LINE EMERGENCY SUMMARY

If you only have 30 seconds, here is everything:

1. **Project** = WC2026 probabilistic tournament simulator, built over P0→P4 + mega audit
2. **Model state** = Two-model view recommended (Expert flat + Elo-fitted temperature-adjusted)
3. **beta_elo FIXED** = 0.543593 — do NOT change, do NOT ask to change
4. **P4 done** — 350 tests pass, READY TO PUBLISH from reproduce script — but wording still risky
5. **Mega audit score** = 5.25/10 (global maturity, quant-lab standard, pessimistic)
6. **Strongest dimensions** = Reproducibility (8.0), Claims honesty (7.5), Documentation (7.0)
7. **Weakest dimensions** = Validation methodology (2.5), Calibration (3.0), Uncertainty (3.0)
8. **Fake confidence** = 350 tests ≠ statistics; beta_mul=0.55 is a heuristic; Expert coefficients are analyst priors
9. **Next action** = P5 wording fix only — no model changes, no probability regeneration
10. **Do not modify model** — Read, confirm, wait before touching anything

---

## C. WHAT CLAUDE MUST DO TOMORROW — IN ORDER

1. **Read all 4 handoff files** (PROJECT_CONTEXT_LOCK, NEXT_SESSION_BOOT, STATE_VERIFICATION, NEXT_ACTION_PROMPT)
2. **Run verification commands** from STATE_VERIFICATION.md — report what they return
3. **Summarize** current state in 5–10 bullet points
4. **Identify risks** from wording_risk_report.md (3–5 highest priority)
5. **Wait for user confirmation** before touching any file
6. **Never start P5** without user saying "GO P5"
7. **Never modify beta_elo, probabilities, or model files** without explicit instruction

### If tests fail at startup:
- Do NOT rerun simulations to "fix" test failures
- Read the failing test first
- Investigate the cause before acting
- Report to user and wait

### If user asks "what should we do next?":
- Answer: "P5 wording fix. See session_handoff/NEXT_ACTION_PROMPT.md for the exact scope."
- Do not start doing it without confirmation

---

## D. WORKING DIRECTORY

```
/Users/yorian/FinderProjects/wc2026_june2026
```

Not a git repository. No remote. Local files only.

Test command:
```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --ignore=tests/test_data_and_mapping.py
```
Expected: `350 passed in ~14s`

---

## E. WHAT THE USER (YORIAN) CARES ABOUT

- Precision over comfort. Say exactly what is true.
- Route survivante only — no bullshit optimism.
- Distinguish: statistically estimated / heuristic / internal sanity check / analyst prior
- Do not recap what you just did — show the results
- Frontal, no fluff, no "great question"
- He knows the codebase — don't explain basics
- Publication is the goal: LinkedIn post + technical chart + honest framing
