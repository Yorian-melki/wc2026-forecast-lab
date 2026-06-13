# Model Selection Re-Audit — Which Model to Publish

**Context:** The clarification audit (P4) concluded "Recommendation C — Expert vs Elo side-by-side, with honest framing." This re-audit revisits that recommendation with the full maturity matrix and fake-done findings in view.

---

## The five options

### Option A: Publish Elo-temp only
**Pros:** Single model, cleaner narrative, all outputs generated, beta_elo has real MLE backing. "Occam's razor: simplest model that passed ablation."

**Cons:** beta_mul=0.55 is a heuristic with no external validation. ESP 16.97% and ARG 14.76% are notably high — a general audience will challenge these. No external reference point. The honest answer to "why 0.55?" is "it looked reasonable," which is not defensible under scrutiny.

**Grade for publication: B-** — Acceptable for personal portfolio. Not acceptable for technical claim of calibrated champion probabilities.

---

### Option B: Publish Expert model only
**Pros:** More balanced probabilities (top-3=23%, no team above 8.2%). General audience finds this more credible. Narrative: "analyst-informed simulation using StatsBomb data."

**Cons:** 16 parameters have zero statistical estimation. The model is an opinion simulation. ECE was never measured for the Expert model because there is no per-team attack/defense in the Elo-backbone test set. The claim "Expert model uses StatsBomb data" is misleading — StatsBomb data is one of 16 hand-weighted inputs for 30/48 teams. 18 teams use defaults.

**Grade for publication: C** — The honest framing would be "a simulation of my prior beliefs about team strength" not "a statistical model." Publishing as a statistical model is overclaiming.

---

### Option C: Publish Expert and Elo side-by-side
**Pros:** Honest about disagreement. Shows the model sensitivity problem (7% vs 17% for Spain is a big gap — publishing both shows the range of uncertainty). Forces disclosure of why the two differ. More credible to a technical audience.

**Cons:** General audience will be confused by two sets of numbers. "Which one do you believe?" is a hard question to answer honestly (the correct answer is "neither is validated, but both are honest").

**Grade for publication: A-** — Best approach technically. Requires a clear explanation of why they differ and why neither is definitively correct. The current model_selection_report.md already does this.

---

### Option D: Blend (weighted average of Expert and Elo)
**Pros:** Would reduce extreme probabilities (ESP would be ~12%, ARG ~11%). Combination forecasts often outperform individual components.

**Cons:** The blending weights would need to be chosen — and by what criterion? Another heuristic. We'd have a heuristic blend of a heuristic-corrected Elo model and an uncalibrated Expert model. The result would be more confusing to explain and no more validated than either component.

**Grade: C+** — Only worth doing if we have a principled way to choose blend weights (e.g., ECE-weighted). We don't currently have that.

---

### Option E: Publish nothing; do more validation first
**Pros:** Honest. Avoids publishing champion probabilities without tournament-level validation.

**Cons:** The WC starts June 11. No time for meaningful additional validation.

**Grade: A for integrity, F for timing.** — This is what a quant fund would do if a deadline wasn't imminent. It is not a realistic option now.

---

## Re-audit finding: the model selection process was correct but incomplete

The P2.5 ablation study was the right approach and reached the right conclusion: Full Hybrid rejected, Elo-calibrated reference promoted. This is solid.

What was NOT done, and should have been done before the model selection decision:

1. **Expert model ECE measurement** — The Expert model's calibration was never formally measured against the P2.5 test splits. It was simply declared "available for comparison." We don't know if Expert ECE is 0.025 or 0.012.

2. **Champion prediction accuracy on past WCs** — Given the WC2018 Elo snapshot, what probability did each model variant assign to France? France won. Even one data point would anchor the discussion.

3. **Sensitivity test on beta_mul** — A chart showing "how champion probabilities change for ESP/ARG/FRA when beta_mul ∈ [0.40, 0.70]" would show how sensitive the recommendation is to the heuristic choice.

---

## Final recommendation (unchanged but better justified)

**Publish both models (Option C), with:**

1. The comparison table already in model_selection_report.md (row 70–87: Expert vs Elo champion probs for top 15 teams)
2. One explicit sentence: "Neither model was validated against actual WC champion outcomes. These are honest estimates with significant uncertainty."
3. If publishing Elo-temp probabilities as the headline (for technical credibility), add the line: "Temperature correction (beta_mul=0.55) is a heuristic choice, not an optimized parameter."

**Do NOT label either model "final" or "best" without the above caveats.**

---

## Risk table

| Option | Publication risk | Technical honesty | General audience clarity |
|--------|:---------------:|:---------------:|:------------------------:|
| A: Elo only | MEDIUM (ESP 17% challenged) | HIGH (labeled heuristic) | MEDIUM |
| B: Expert only | HIGH (no statistical backing) | LOW (analyst priors as model) | HIGH |
| C: Both side-by-side | LOW (disagreement disclosed) | HIGH | LOW (confusing) |
| D: Blend | MEDIUM | MEDIUM (new heuristic) | MEDIUM |
| E: Nothing | NONE | MAX | N/A |

**C is the right answer for technical publication. A with full disclosure is the right answer for LinkedIn.**
