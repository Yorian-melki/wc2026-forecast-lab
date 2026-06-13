# Wording Risk Report — WC2026 Forecast

**Purpose:** Identify claims, phrases, and framings in public documents that could be technically challenged.  
**Scope:** MODEL_CARD.md, MODEL_FREEZE.md, README.md, outputs/public/*, linkedin_post.md  
**Risk levels:** HIGH (will be challenged), MEDIUM (can be challenged), LOW (defensible)

---

## HIGH RISK — Will be challenged by technical readers

### 1. "Elo-calibrated model"

**Location:** MODEL_CARD.md, MODEL_FREEZE.md, README.md, chart footer, LinkedIn post  
**The phrase implies:** ECE was measured and corrected. The model outputs are calibrated probabilities.  
**What is actually true:** "Elo-calibrated" means the Elo→xG mapping was fitted via MLE. ECE was measured (0.017) but NOT corrected. The model is not probability-calibrated — it is parameter-fitted.  
**Risk:** A technical reader will say: "Your ECE is 0.017. That means your probabilities are off by 1.7pp on average. In what sense is this 'calibrated'?"  
**Fix:** Replace "Elo-calibrated model" with "Elo-fitted model" or "Elo-parameterized Poisson model." Reserve "calibrated" for ECE-corrected outputs.

---

### 2. "Temperature correction validated internally"

**Location:** MODEL_CARD.md line ~45, README.md, model_selection_report.md line 68  
**The phrase implies:** There was a validation step that checked the temperature correction against some reference.  
**What is actually true:** We ran the same corrected model (beta=0.544) on WC2018 and WC2022 Elo snapshots and observed similar concentration (35.6%, 39.2%). This is circular: same parameter, different input, same output. It proves consistency, not correctness.  
**Risk:** "What did you validate against?" The answer is: our own model. That's not validation.  
**Fix:** "Temperature correction applied heuristically. Internally consistent (same beta applied to past WC Elo snapshots gives 35–39% top-3 concentration) but not externally validated."

---

### 3. "ECE +17% worse for Full Hybrid"

**Location:** MODEL_CARD.md, model_selection_report.md, README.md, LinkedIn post  
**The phrase:** True. ECE for Full Hybrid avg across 4 splits is 0.0199 vs 0.0170 for Elo-calibrated reference.  
**Risk:** The difference 0.0199 - 0.0170 = 0.0029. In absolute terms: the Full Hybrid probabilities are off by 0.29pp more than the reference. 0.29pp is hard to detect in any individual prediction. Publishing "+17% worse calibration error" sounds dramatic for what is a sub-0.3pp difference.  
**Not wrong, but:** Framing as a percentage amplifies a small absolute difference. A careful reader will note: ECE=0.017 vs ECE=0.020 is both models having sub-2% average error. The difference is real but small.  
**Fix:** Add absolute values: "ECE 0.0199 vs 0.0170 (difference: 0.0029, +17% relative)." Let readers judge the practical significance.

---

### 4. "49,450 international matches ingested"

**Location:** MODEL_CARD.md, claims_audit.md, README.md, LinkedIn post  
**What it means:** All matches in the martj42 dataset — including friendlies.  
**What MLE used:** 10,555 competitive matches only.  
**Risk:** A reader will say: "If you only used 10,555 matches for MLE, why does 49,450 matter?" The answer is: Elo ratings are computed on all 49,450 (rolling), and MLE is done only on competitive. This distinction is not obvious.  
**Fix:** Make the distinction explicit in one sentence wherever 49,450 appears: "49,450 matches for rolling Elo computation; 10,555 competitive matches used for MLE parameter estimation."

---

### 5. "100,000 Monte Carlo simulations"

**Location:** Chart footer, MODEL_CARD, README, LinkedIn  
**The phrase is accurate:** 100K simulations run. Conservation laws verified.  
**Subtle risk:** 100K simulations reduces sampling variance on champion probabilities to ±0.3pp (Wilson CI for ESP 17%). But the much larger source of uncertainty — parameter uncertainty from beta_elo MLE — is not quantified. The 100K number sounds precise but masks model uncertainty.  
**Not wrong, but:** Framing as a precision indicator when the dominant uncertainty is elsewhere is slightly misleading.  
**Fix:** Add a footnote or parenthetical: "Sampling error ±0.3pp at 95% CI; parameter uncertainty not separately quantified."

---

## MEDIUM RISK — Can be challenged, defensible with context

### 6. "Full Hybrid rejected after P2.5 ablation"

**Location:** Multiple documents  
**The claim:** True. ECE +17% worse, 0/4 clear-win splits, BORDERLINE_EXPERIMENTAL gate.  
**Possible challenge:** "Did you consider that the Full Hybrid NLL was lower on 4/4 splits?" Yes — but calibration (ECE) was worse. The trade-off of better NLL for worse calibration was judged unfavorable. This is a defensible methodological choice.  
**Risk level:** MEDIUM — requires a clear explanation of why ECE matters more than NLL for this application.  
**No change required** if accompanied by: "We prioritized calibration because we're reporting probabilities to a general audience, not maximizing log-likelihood on competitive matches."

---

### 7. "Exact 48-team WC2026 bracket mechanics"

**Location:** MODEL_CARD, README  
**The claim:** True. Bracket logic is correct.  
**Possible challenge:** "Do you account for group-stage tiebreaker rules?" — Partially. The best-3rd advancement is implemented. Head-to-head tiebreakers within a group are not fully modeled (group rank is assigned stochastically). For a WC forecast, this is an acceptable simplification.  
**Risk level:** MEDIUM — only if someone checks the group tiebreaker logic in detail.

---

### 8. "StatsBomb-derived pressing/shot-quality metrics for 30 of 48 teams"

**Location:** MODEL_CARD only  
**The claim:** True. But the coefficients applied to these features (ppda=0.030, shot_quality=5.000) are not StatsBomb-derived — they are analyst-assigned.  
**Risk:** A careful reader will notice: "So you have StatsBomb data, but the coefficients you apply to it are guesses?" Yes. That's correct.  
**Fix:** Be more explicit: "StatsBomb data used as input features. Feature coefficients are analyst-assigned priors, not estimated via regression on StatsBomb data."

---

### 9. "Conservation law verified: Σ P(champion) = 1.000000"

**Location:** README, reproducibility_log.txt  
**The claim:** True and verifiable.  
**Not a risk for being challenged** — this is genuinely correct.  
**Minor note:** Conservation laws verify simulation correctness, not forecast accuracy. A conservation law can hold for a completely wrong model. This is a floor, not a ceiling.

---

## LOW RISK — Defensible as-is

| Phrase | Status |
|--------|--------|
| "100,000 Monte Carlo simulations · seed=20260609" | Fully reproducible |
| "Full Hybrid rejected after calibration degradation" | Documented, defensible |
| "Temperature correction β=0.543" | Labeled as applied correction |
| "Internal sanity check: 35.6% and 39.2%" | Correctly framed after P4 fix |
| "Disclaimer: not a betting model, not financial advice" | Present in README |
| "Neither model externally validated against WC outcomes" | Present in model_selection_report.md and MODEL_CARD |

---

## Summary: wording changes recommended

| Priority | Location | Current wording | Recommended replacement |
|----------|----------|-----------------|------------------------|
| **HIGH** | All docs | "Elo-calibrated model" | "Elo-fitted Poisson model" |
| **HIGH** | MODEL_CARD, README | "validated internally" | "internally consistent (not externally validated)" |
| **MEDIUM** | All docs near "49,450" | "49,450 international matches" | "49,450 for Elo; 10,555 competitive for MLE" |
| **MEDIUM** | MODEL_CARD | "StatsBomb-derived" coefficients | "StatsBomb data used as input; coefficients are analyst-assigned" |
| **LOW** | MODEL_CARD, README | "ECE +17% worse" | "ECE 0.0199 vs 0.0170 (absolute difference: 0.0029)" |
| **LOW** | Chart footer | "Elo-calibrated" | "Elo-fitted temperature-corrected" |

None of these changes break the publication package or require re-running simulations. They are wording precision fixes.
