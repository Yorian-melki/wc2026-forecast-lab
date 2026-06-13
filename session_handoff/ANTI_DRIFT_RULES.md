# ANTI-DRIFT RULES — WC2026 Forecast
# These rules prevent Claude from drifting toward over-engineering,
# false confidence, or unauthorized changes.
# Read before every response in this project.

---

## RULE 1: No new phase without explicit user instruction

Do NOT start P5, P6, or any new work phase without the user explicitly saying GO.  
"What should we do next?" is a question, not an instruction to act.  
The correct response to that question: "P5 wording fix. Read session_handoff/NEXT_ACTION_PROMPT.md for exact scope. GO when ready."

---

## RULE 2: No model changes unless explicitly requested

Do NOT modify:
- `data/elo_calibrated_params.json` (beta_elo=0.543593 is frozen)
- `outputs/tournament_run/elo_calibrated_summary.csv` (frozen simulation output)
- Any file in `src/wc2026/` (model code — no changes without explicit request)
- `data/model_freeze_manifest.json` (frozen manifest)

If you find a bug in model code: REPORT IT. Do NOT fix it without confirmation.  
The model is frozen for publication purposes even if improvements are theoretically possible.

---

## RULE 3: No probability regeneration

The champion probabilities (ESP 16.97%, ARG 14.76%, etc.) are frozen from seed=20260609, 100K iterations.  
Do NOT rerun simulations to "fix" probabilities.  
Do NOT adjust probabilities for any reason except if user explicitly says "regenerate simulation."

---

## RULE 4: No replacing audit conclusions with optimistic summaries

The mega audit score is 5.25/10. This is honest. Do not soften it.  
If asked "how good is the model?", say 5.25/10 with the breakdown, then explain what would raise it.  
Do NOT say "it's solid for a personal project" as the primary framing — add it only as context.

---

## RULE 5: Always distinguish these four things

When describing any result, claim, or feature:

| Category | Meaning | Example |
|----------|---------|---------|
| **Statistically estimated** | MLE/CV/regression with fit quality measured | beta_elo=0.543593 (MLE on 10,555 matches) |
| **Heuristic** | Chosen by judgment, no objective criterion | beta_mul=0.55 (chosen to give "reasonable" top3) |
| **Internal sanity check** | Consistent with itself, not validated externally | historical 36–39% concentration |
| **External validation** | Tested against real outcomes independent of model construction | NOT DONE in this project |
| **Analyst prior** | Human judgment as model input | Expert model coefficients (attack=0.060 etc.) |
| **Publication wording** | What we say publicly | "Temperature correction applied heuristically" |

Never conflate these. The confusion between "statistically estimated" and "heuristic" is the main source of false confidence in this project.

---

## RULE 6: No saying "ready to publish" without mentioning caveats

If you say "ready to publish," you MUST also say:
- "Temperature correction is heuristic"
- "Expert coefficients are analyst priors"
- "No external WC champion prediction validation"
- "Publication tier: personal portfolio, not investment-grade"

The reproducibility_log.txt says "READY TO PUBLISH" — this refers to the technical package (files, tests, parameters). It does NOT mean the statistical claims are industry-grade.

---

## RULE 7: No "let's improve everything" drift

If you notice something that could be improved during P5 wording work:
- Fix the wording that was explicitly requested
- REPORT the improvement opportunity
- Do NOT implement the improvement without user GO

Examples of drift to avoid:
- "While fixing the wording, I also added isotonic regression calibration..."
- "I noticed the significance variance was hardcoded so I fixed that too..."
- "I added 5 new tests while I was in the test file..."

These are good intentions that violate the freeze protocol. Report. Wait. Act when asked.

---

## RULE 8: No hidden file edits

Every file you edit must be reported to the user BEFORE or IMMEDIATELY AFTER the edit.  
No batch-editing 10 files and saying "fixed everything" at the end.  
One change at a time, confirmed.

---

## RULE 9: No claiming the temperature correction is "optimal"

beta_mul=0.55 is a heuristic. The correct description:
- "We chose beta_mul=0.55 because it brought top-3 concentration to ~42%."
- "There is no objective function that determined this value."
- "The choice appears reasonable by internal consistency check."
- "It is not an optimized parameter."

Do NOT say "beta=0.55 was validated" — validated implies testing against real outcomes.

---

## RULE 10: No using test count as statistical validation

"350 tests pass" means the simulation runs correctly and outputs consistent numbers.  
It does NOT mean the champion probabilities are calibrated.  
It does NOT mean the model outperforms naive benchmarks.  
It does NOT mean the temperature correction is correct.  
It does NOT mean the Expert coefficients are correct.

When someone asks "is the model statistically validated?", the honest answer is:
"Match-level MLE and ECE were validated on temporal cross-validation (P2.5). Tournament-level champion prediction accuracy has NOT been validated against actual WC outcomes."

---

## RULE 11: Maintain distinction between Expert model and Elo model

These are two separate models with fundamentally different backing:

**Expert model:**
- 16 hand-tuned coefficients (0 statistical estimation)
- Uses StatsBomb data for 30/48 teams as INPUT (coefficients not from StatsBomb)
- Flatter probabilities (analyst compression)
- Top champion: FRA 8.19%, ARG 7.82%, ESP 7.32%
- Do not describe as "statistically estimated"

**Elo-fitted Poisson model:**
- 3 MLE parameters (beta_elo, log_base, rho)
- + 1 heuristic temperature correction
- More concentrated probabilities
- Top champion: ESP 16.97%, ARG 14.76%, FRA 10.03%
- Do not describe as "calibrated" (ECE measured, not corrected)

---

## RULE 12: Do not start today what should wait until tomorrow

The tournament starts 2026-06-11. If the user wants to publish before tomorrow, P5 wording fix is all there is time for. Do NOT suggest adding new model features, running new simulations, or doing major new analysis that cannot be completed in 2–3 hours. The window is closing. Focus.
