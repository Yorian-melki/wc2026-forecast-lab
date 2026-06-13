# Final Action Plan — WC2026 Forecast

**Based on:** Mega maturity matrix (62 items), global maturity score (5.25/10), done/fake-done analysis, probability output audit, and wording risk report.

**Instruction:** Do not modify model code. Do not edit beta_elo. Do not regenerate probabilities. Exceptions explicitly noted.

---

## BUCKET 1: MUST FIX BEFORE PUBLICATION

*These are errors, misleading claims, or risks that will damage credibility if left unfixed.*

### 1.1 Add "heuristic" label to temperature correction
**File:** MODEL_CARD.md, README.md  
**Current:** "Temperature correction validated internally only"  
**Fix:** "Temperature correction is a heuristic choice (β×0.55). Internally consistent: same model on pre-WC2018/2022 Elo snapshots gives 35–39% top-3. Not externally validated against WC champion outcomes."  
**Why:** "Validated" implies something was tested. The circular internal check is not validation. A technical reader will call this out.

---

### 1.2 Replace "Elo-calibrated model" terminology
**Files:** MODEL_CARD.md, MODEL_FREEZE.md, README.md, chart footer, linkedin_post.md  
**Current:** "Elo-calibrated model" (implies ECE calibration)  
**Fix:** "Elo-fitted Poisson model" — "Elo-fitted" correctly describes MLE on the Elo→xG mapping; "calibrated" incorrectly implies ECE correction was applied.  
**Why:** Technical readers distinguish "parameter estimation" from "probability calibration." ECE=0.017 was measured but not corrected. The model is NOT calibrated in the probability calibration sense.  
**Note:** This is a naming fix only — no model changes, no probability regeneration.

---

### 1.3 Add StatsBomb 30/48 disclosure to LinkedIn post
**File:** outputs/public/linkedin_post.md  
**Current:** "using StatsBomb data" — implies full coverage  
**Fix:** Add parenthetical: "(30 of 48 teams; 18 teams use analyst defaults)"  
**Why:** The LinkedIn post is the highest-reach document. A reader with StatsBomb knowledge will notice the coverage gap. Not disclosing it is the closest thing to active misleading in the current package.

---

### 1.4 Add USA/MAR explanation to chart or LinkedIn
**File:** linkedin_post.md or chart footnote  
**Issue:** USA at 0.33% champion will confuse every American reader of the LinkedIn post. USA is a co-host.  
**Fix:** Add one sentence: "USA ranks 31st in Elo (1726), reflecting their competitive match history. The host advantage (+8% xG) is included — it boosts their group survival probability more than their final probability."  
**Why:** Without this, the first comment on LinkedIn will be "why is the USA at 0.33%?"

---

## BUCKET 2: SHOULD FIX (HIGH VALUE, LOW EFFORT)

*These are improvements that significantly increase credibility with 2–6 hours of effort. Recommended before any technical audience.*

### 2.1 WC2022 retroactive champion probability
**What:** Run the Elo simulation using pre-WC2022 Elo ratings (already in `historical_tournament_concentration.csv` infrastructure) but save per-team champion probabilities, not just top-3 concentration.  
**Why:** Argentina (the actual WC2022 winner) should have been assigned 10–15% by our model pre-WC2022. Showing this one number — "our model assigned Argentina 12.3% pre-WC2022, they won" — transforms the historical check from circular to actually informative. This is the single highest-ROI addition to the project.  
**Effort:** 2–3 hours. The infrastructure is already there.  
**Note:** This requires RUNNING THE SIMULATION ONCE (retroactively). NOT changing beta_elo. NOT changing 2026 probabilities. A new output file only.

---

### 2.2 Compute significance test variance from data
**File:** `src/wc2026/calibration/significance.py`  
**Issue:** variance=0.40 hardcoded. Should be computed from the variance of NLL differences across the test set.  
**Why:** All significance claims in ablation_summary.md and significance_report.csv are based on this hardcoded assumption. With computed variance, they become defensible.  
**Effort:** 1–2 hours. The test set NLLs are already available in ablation_results.csv.

---

### 2.3 Clarify 49,450 vs 10,555 everywhere
**Files:** MODEL_CARD.md, README.md, linkedin_post.md, claims_checklist.md  
**Current:** "49,450 international matches" without explaining 10,555 competitive for MLE  
**Fix:** "49,450 matches for rolling Elo computation; 10,555 competitive-only matches for MLE parameter estimation"  
**Effort:** 30 minutes.

---

### 2.4 Add reliability diagram to MODEL_CARD
**File:** MODEL_CARD.md  
**Current:** calibration_curve.png exists in outputs/calibration/ but not referenced in MODEL_CARD  
**Fix:** Add a sentence: "Calibration reliability diagram: `outputs/calibration/calibration_curve.png` — ECE=0.017 (Elo-fitted), ECE=0.020 (Full Hybrid)"  
**Why:** The calibration curve is the most direct visual evidence for the ECE claims. Not including it in the card that claims ECE superiority is a missed opportunity.  
**Effort:** 15 minutes.

---

### 2.5 Add test: Elo rank → champion prob monotone
**File:** tests/test_p4_publication_package.py or new test_p5_post_audit.py  
**What:** Test that top-10 Elo teams account for ≥7 of top-10 champion probability teams.  
**Current:** r=0.992 passes this trivially. Adding the test documents and enforces it.  
**Effort:** 30 minutes.

---

### 2.6 Add test: host nation home advantage works
**File:** same as above  
**What:** Test that MEX/USA/CAN have above-average group survival probability.  
**Why:** If someone changes the home advantage config to 0, this catches it.  
**Effort:** 30 minutes.

---

## BUCKET 3: COULD IMPROVE (MODERATE VALUE, MODERATE EFFORT)

*These would take the project from 5.25/10 to 6.5–7/10 maturity. Recommended if more time available.*

### 3.1 Expert coefficient MLE estimation
**What:** Run MLE on the Expert model coefficients (the 11 analyst ratings + 5 StatsBomb coefficients) using the same P2.5 temporal splits.  
**Value:** Transforms Expert model from "opinion simulation" to "data-backed simulation." Would make both models statistically defensible.  
**Effort:** 1–2 days. The infrastructure (data, splits, objective function) is already built for P2.5.

---

### 3.2 Bootstrap CI on beta_elo
**What:** Bootstrap resample the 10,555 training matches, refit beta_elo on each sample, compute 95% CI.  
**Value:** Shows "beta_elo = 0.544 ± 0.03" (or whatever the actual range is). Quantifies parameter uncertainty.  
**Effort:** 3–4 hours. scipy.minimize needs to be called ~1000 times on resampled data.

---

### 3.3 Full calibration correction (isotonic regression)
**What:** Apply isotonic regression on the ECE buckets to post-process champion probabilities.  
**Value:** Actually corrects the known 1.7pp average miscalibration.  
**Effort:** 2–3 hours. Standard isotonic regression available in sklearn.  
**Note:** Would require regenerating champion probabilities. Only do this if beta_elo is NOT being changed. This is a post-hoc probability correction, not a model change.

---

### 3.4 Temporal form for all 48 teams
**What:** Expand form_history.csv from 16 to 48 teams.  
**Value:** Removes the 32-team silent default (form=50.0). Makes the model less asymmetric.  
**Effort:** 4–6 hours to curate last 10 competitive matches per team from results.csv.

---

### 3.5 Bookmaker odds comparison table
**What:** Find pre-WC2026 Pinnacle/Betfair implied probabilities for top 10 teams and compare.  
**Value:** Answers "how does this compare to market?" One table shows whether we're close, higher, or lower.  
**Effort:** 1–2 hours to find and format.  
**Note:** This requires internet data. If our 17% for ESP vs market 14% for Spain, say so.

---

## BUCKET 4: DO NOT DO

*These would consume time without proportional benefit, or would violate the model freeze.*

### 4.1 Modify beta_elo
Frozen at 0.543593 since P3.5. Conservation laws pass. Probabilities generated. Any modification invalidates P4 package. **DO NOT.**

### 4.2 Add Dixon-Coles rho to Expert model
The Expert model has its own separate architecture. Adding rho to it would change both the Expert and the Elo model behavior if done to a shared function. **DO NOT.** If done later, it's a new model version, not a bug fix.

### 4.3 Run new simulations to "improve" probabilities
The 100,000 simulation results are frozen. Running new simulations to "improve" numbers by cherry-picking a seed or iteration count would undermine the reproducibility claim. **DO NOT.**

### 4.4 Add complex ensemble or model averaging without principled weights
Averaging Expert and Elo at 50/50 without a principled criterion adds another heuristic on top of existing heuristics. The publication is better served by honest disclosure of the two models than a blend that requires explaining "we averaged 50/50 because it looked reasonable." **DO NOT** (unless you have ECE-weighted blending from ablation — which would require rerunning P2.5 on both models jointly).

### 4.5 Add ANOVA, Bayesian model comparison, or other complex statistical tests post-hoc
The P2.5 ablation study is complete. Adding new statistical tests after seeing the results is p-hacking. The model selection decision was made. **DO NOT.**

### 4.6 Change public wording to make claims sound stronger
The trend in this project has been toward more honesty (the "historical WC reference" fix was the right call). Do not reverse this. If LinkedIn gets 3 likes instead of 300 because of honest caveating, that is correct.

---

## Action plan summary

| Bucket | Item | Hours | Impact |
|--------|------|------:|--------|
| MUST | 1.1 Heuristic label | 0.5h | Eliminates misleading claim |
| MUST | 1.2 Elo-fitted terminology | 1h | Correct statistical language |
| MUST | 1.3 StatsBomb LinkedIn disclosure | 0.5h | Honest coverage disclosure |
| MUST | 1.4 USA explanation | 0.5h | Prevents obvious LinkedIn challenge |
| SHOULD | 2.1 WC2022 retroactive | 2–3h | Transforms circular to real validation |
| SHOULD | 2.2 Significance variance | 1–2h | Makes significance claims defensible |
| SHOULD | 2.3 49K/10K clarification | 0.5h | Precision fix |
| SHOULD | 2.4 Reliability diagram reference | 0.25h | Supports ECE claim |
| SHOULD | 2.5 Elo monotone test | 0.5h | Documents real invariant |
| SHOULD | 2.6 Host advantage test | 0.5h | Tests real feature |
| COULD | 3.1 Expert MLE | 1–2 days | Would make Expert model real |
| COULD | 3.2 Bootstrap CI | 3–4h | Quantifies parameter uncertainty |
| COULD | 3.3 Calibration correction | 2–3h | Actually fixes calibration |
| COULD | 3.4 Full form coverage | 4–6h | Removes 32-team asymmetry |
| COULD | 3.5 Bookmaker comparison | 1–2h | Puts model in context |
| DO NOT | beta_elo modification | — | Frozen |
| DO NOT | New simulation run | — | Frozen |
| DO NOT | Post-hoc p-hacking tests | — | Invalidates study |
