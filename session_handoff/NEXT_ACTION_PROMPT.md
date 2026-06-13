# NEXT ACTION PROMPT — P5 WORDING FIX
# Created: 2026-06-10
# ⚠️ DO NOT RUN AUTOMATICALLY. Wait for user to say "GO P5".
# This file describes the next action only. No model changes. No beta changes.

---

## ⚠️ BEFORE RUNNING P5 — MANDATORY CHECKS

1. User must explicitly say "GO P5" or equivalent
2. Run STATE_VERIFICATION.md first — all 10 checks must pass
3. Tests must be at 350 passing before any changes
4. Confirm: no probability regeneration, no beta_elo change, no model file changes

---

## WHAT P5 IS

P5 = wording credibility fix only.

**Scope:**
- Fix terminology in public documents (MODEL_CARD, README, MODEL_FREEZE, LinkedIn post)
- No model code changes
- No changes to `data/elo_calibrated_params.json`
- No changes to `outputs/tournament_run/elo_calibrated_summary.csv`
- No new simulations
- No new features

**Total estimated effort:** 2–3 hours of file editing + test run

---

## P5 EXACT ITEMS (ordered by priority)

### P5.1 — MUST: Replace "Elo-calibrated" terminology
**Files:** MODEL_CARD.md, MODEL_FREEZE.md, README.md, chart footer (regenerate chart), linkedin_post.md  
**Change:** "Elo-calibrated model" → "Elo-fitted Poisson model"  
**Why:** "Calibrated" implies ECE correction was applied. It was not. ECE was measured (0.017) but not corrected.  
**Also:** Anywhere "calibrated" refers to the MLE fitting process → "fitted"  
**Preserve:** "Elo-calibrated backbone" in the ablation context can stay if it means "the Elo-parameterized model used as reference in ablation"

---

### P5.2 — MUST: Label temperature correction as heuristic
**Files:** MODEL_CARD.md, README.md  
**Current:** "Temperature correction validated internally only"  
**Change to:** "Temperature correction is a heuristic (beta_mul=0.55, not optimized). Internally consistent: same model on pre-WC2018/WC2022 Elo snapshots gives 35–39% top-3 concentration. Not externally validated against WC champion outcomes."  
**Why:** "Validated" implies rigorous testing. The circular consistency check is not validation.

---

### P5.3 — MUST: StatsBomb disclosure in LinkedIn post
**File:** outputs/public/linkedin_post.md  
**Current:** "using StatsBomb data" (implies full coverage)  
**Change to:** Add "(30 of 48 teams; 18 use analyst-assigned defaults)" immediately after any StatsBomb mention  
**Why:** Highest-reach document. A StatsBomb user will notice the gap.

---

### P5.4 — MUST: USA/host nation explanation
**File:** outputs/public/linkedin_post.md (add footnote or parenthetical)  
**Add:** "USA ranks 31st in rolling Elo (1726) — home advantage (+8% xG) is already included, boosting their group-stage advancement probability more than their overall champion probability (0.3%)."  
**Why:** The first LinkedIn comment will be "why is the host USA at 0.3%?"

---

### P5.5 — SHOULD: Clarify 49,450 vs 10,555
**Files:** MODEL_CARD.md, README.md, linkedin_post.md  
**Current:** "49,450 international matches" without clarification  
**Change to:** "49,450 matches ingested for rolling Elo computation; 10,555 competitive-only matches used for MLE parameter estimation"  
**Why:** 49K is the database; 10.5K is what actually trained the parameters.

---

### P5.6 — SHOULD: Add reliability diagram reference to MODEL_CARD
**File:** MODEL_CARD.md  
**Add:** "Calibration reliability diagram available at `outputs/calibration/calibration_curve.png` — average ECE=0.017 (Elo-fitted model), 0.020 (Full Hybrid)"  
**Why:** The curve exists but is not referenced. It is the most direct evidence for the ECE claim.

---

### P5.7 — SHOULD: Adopt two-model framing in LinkedIn
**File:** outputs/public/linkedin_post.md  
**Current:** Primarily presents Elo-fitted model as the result  
**Add:** One sentence presenting the two-model view and the key divergence: "Our analyst-prior model gives Spain 7.3%; our data-driven model gives 17.0%. The honest answer is: somewhere between those."  
**Why:** This is the most intellectually honest sentence about the project, and it shows methodological awareness.

---

### P5.8 — COULD: Add one retroactive WC2022 number
**New output file:** `outputs/calibration/wc2022_retroactive_champion_probs.csv`  
**What:** Run simulation with pre-WC2022 Elo ratings (from `historical_tournament_concentration.csv` infrastructure) and save PER-TEAM champion probabilities  
**Why:** "Our model (retroactively applied) would have given Argentina 11.4% pre-WC2022. They won." — transforms circular sanity check into informative historical reference  
**This IS a new simulation run** — requires explicit user go-ahead  
**Note:** Does NOT change WC2026 probabilities. Does NOT change beta_elo. New output file only.

---

## P5 VERIFICATION AFTER WORDING CHANGES

After all wording changes:

```bash
# 1. Tests must still pass at 350
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --ignore=tests/test_data_and_mapping.py

# 2. Reproduction script must still pass
PYTHONPATH=src .venv/bin/python scripts/reproduce_public_outputs.py

# 3. Forbidden claims still absent
# (handled by reproduce_public_outputs.py step 5)
```

**Expected after P5:** `READY TO PUBLISH` from reproduce script, `350 passed` from pytest.

---

## P5 WHAT DOES NOT CHANGE

- `beta_elo` = 0.543593 (frozen)
- `outputs/tournament_run/elo_calibrated_summary.csv` (frozen)
- `data/elo_calibrated_params.json` (frozen)
- `data/model_freeze_manifest.json` (frozen)
- Any file in `src/wc2026/` (no model changes)
- Champion probabilities (ESP 16.97%, ARG 14.76%, FRA 10.03%, etc.)
- Conservation laws

---

## AFTER P5 COMPLETES

The project is DONE in its current scope.

Optional future work (separate explicit decision by user):
- P6: WC2022 retroactive validation (2–3 hours, new output only)
- P7: Bootstrap CI on beta_elo (3–4 hours, new output only)
- P8: Expert model MLE coefficient estimation (1–2 days, major addition)
- P9: Bookmaker odds comparison table (1–2 hours, data gathering only)

None of these are required for the current LinkedIn/portfolio publication.
