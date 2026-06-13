# Global Maturity Score — WC2026 Forecasting System

**Scale:** 1 (broken) → 10 (publishable in JASA or used by a tier-1 quant fund)  
**Evaluator standard:** A probabilist or quant researcher with 10 years of forecasting budget at a hedge fund, rating agency, or top sports analytics firm.  
**Principle:** Score what exists and works, not what was intended. Penalize fake-done items.

---

## 1. Data Quality & Coverage — 6.0 / 10

**What's there:** 49,450 international matches from martj42. Competitive/friendly split. StatsBomb data for 30/48 teams. Temporal form history for 16/48 teams. Snapshot date documented.

**Why not higher:** 18/48 teams use StatsBomb defaults (hand-coded). 32/48 teams use static form (analyst prior). No independent verification of data accuracy. No deduplication audit at row level. Pre-tournament update procedure absent.

**What raises it to 8:** Full StatsBomb coverage OR proper imputation with stated uncertainty. Row-level dedup check. Form history for all 48 teams.

---

## 2. Feature Engineering — 3.5 / 10

**What's there:** Elo ratings (proper MLE). Dixon-Coles rho (MLE). Temporal form (wired for 16 teams). Jet lag (rough approximation, all 48). Home advantage (hard-coded multiplier).

**Why not higher:** The two most impactful features — Expert analyst ratings and StatsBomb coefficients — are hand-tuned priors with zero statistical calibration. The source code literally says "not statistically calibrated." Temporal form only covers 1/3 of teams. Jet lag uses a single city approximation for 15+ actual venues. Home advantage has no empirical grounding from WC host results.

**What raises it to 7:** Fit Expert coefficients via MLE or at minimum show them pass cross-validation. Expand temporal form to all 48 teams. Replace jet lag single-city with per-venue correction.

---

## 3. Model Specification — 6.0 / 10

**What's there:** Independent Poisson + Dixon-Coles correction is a well-understood, published approach (Maher 1982, Dixon-Coles 1997). 48-team bracket mechanics are exact. Tournament path dependencies captured by Monte Carlo.

**Why not higher:** Model is a 1997-era approach. No Skellam distribution. No negative-binomial (overdispersion). No bivariate Poisson. The independent Poisson model is known to underestimate draws and create spuriously high probabilities for top teams — which is exactly what we observed (top3=66%). Home advantage treated as a single multiplier.

**What raises it to 8:** Bivariate Poisson or Dixon-Coles properly correcting for correlations. Overdispersion test. Stadium-level effects.

---

## 4. Parameter Estimation Methodology — 3.5 / 10

**What's there:** MLE for beta_elo, log_base, and DC rho. These three parameters are properly estimated.

**Why not higher:** The Expert model — which is the second published model — has **zero statistical parameter estimation**. 16 parameters (11 analyst + 5 StatsBomb coefficients) are human judgment. Temperature correction beta_mul=0.55 was chosen to produce a "reasonable-looking" concentration — no objective function, no optimization. No confidence intervals on any parameter.

**What raises it to 7:** MLE on Expert model coefficients. Bootstrap CIs on beta_elo and rho. Documented grid search or cross-validation on beta_mul.

---

## 5. Model Selection Rigor — 6.0 / 10

**What's there:** 9-model ablation, 4 temporal splits, NLL and ECE both measured. Full Hybrid correctly rejected based on ECE degradation (+17%). Gate thresholds documented. Logic defensible.

**Why not higher:** Significance test variance is hardcoded (not computed from data). WC-level tournament champion prediction test is absent — this is the one test that directly validates the champion probability output. Comparison to any external benchmark is absent.

**What raises it to 8:** Compute variance from actual test data in significance tests. Add at least one test: "what P(champion) did model assign to actual WC2018 and WC2022 winners?" Even one data point is better than zero.

---

## 6. Calibration Quality — 3.0 / 10

**What's there:** ECE measured (0.017 for Elo-calibrated, 0.020 for Full Hybrid). Calibration curve plotted. ECE comparison used as model selection criterion.

**Why not higher:** ECE is measured but not corrected. The model is known to be miscalibrated by ~1.7pp average. No isotonic regression, no Platt scaling, no temperature post-processing applied to outputs. Match-level calibration is not equivalent to tournament champion calibration — compounding over 7 rounds with mean bias can produce systematic under/over-confidence on champion probability. This was not tested.

**What raises it to 6:** Apply isotonic regression calibration. Report reliability diagram in public docs. Add tournament-level Brier score test on historical WC.

---

## 7. Validation Methodology — 2.5 / 10

**What's there:** 4 temporal train/test splits for match-level validation. 1 WC tournament holdout (64 matches). Conservation laws verified (necessary but not sufficient).

**Why not higher:** Match-level temporal CV validates only match-level predictions, not champion probabilities. The 64-match WC holdout is the only tournament-level validation, and it tests match outcomes, not tournament outcomes. The "historical WC validation" is circular (same model, different Elo input). No comparison to any external forecast. No test on actual WC champion prediction accuracy over WC2014/2018/2022.

**This is the biggest structural weakness of the project.** A quant fund would not publish champion probabilities without at least one tournament-level out-of-sample test.

**What raises it to 6:** Even a single number: "Before WC2022, our model (had it existed) would have assigned Brazil 16%, Argentina 11.5%. Argentina won (probability 11.5%). This is consistent with an honest forecast." This is honest, verifiable, and shows the model is not obviously broken.

---

## 8. Uncertainty Quantification — 3.0 / 10

**What's there:** Wilson CIs on champion probabilities from Monte Carlo sampling variance (100K simulations). These quantify simulation noise, not model uncertainty.

**Why not higher:** Wilson CIs capture only one source of uncertainty: simulation sampling. They do not capture: (a) uncertainty in beta_elo (which has no CI), (b) uncertainty in analyst ratings (which are treated as fixed truths), (c) model specification uncertainty (Poisson vs bivariate Poisson), (d) data uncertainty (measurement error in Elo ratings), (e) irreducible uncertainty (we genuinely don't know the future). Presenting Wilson CIs as the uncertainty bound is a precision illusion.

**What raises it to 6:** Bootstrap beta_elo and propagate through simulation. Report confidence interval on ESP champion probability that accounts for parameter uncertainty, not just sampling noise.

---

## 9. Code Quality — 7.0 / 10

**What's there:** Clean module structure. Lazy init pattern. Data loader with apply_temporal_form flag. Temporal form properly wired (for 16 teams). Jet lag wired for all 48. Tests pass.

**Why not higher:** Magic constants (config.json rho=0.08 vs MLE rho=-0.021 — which one runs?). Significance test variance hardcoded. 32/48 teams have form=50.0 default that flows silently through the model.

**What raises it to 9:** Resolve config rho vs MLE rho discrepancy. Compute significance variance from data. Warn (don't fail) when form_history doesn't cover a WC team.

---

## 10. Test Quality — 4.5 / 10

**What's there:** 350 tests passing. Conservation law tests (real). Probability sum tests (real). Forbidden claims tests (real, automated). File existence tests (CI safety).

**Why not higher:** ~200 of 350 tests are existence/schema/conservation checks that verify infrastructure, not statistical validity. The probability calibration of the output is not tested post-simulation. No test asks "does the model assign higher probability to higher-Elo teams in monotone fashion across all 48 teams?" No test for the actual claim we're publishing: "are champion probabilities reasonable?"

**What raises it to 7:** Add 5 tests: (1) Elo rank vs champion probability rank monotone, (2) Expert vs Elo correlation above 0.7, (3) calibration ECE post-simulation below 0.04, (4) form_history covers exactly 16 known teams, (5) temp-corrected beta gives top3 in [35%, 48%].

---

## 11. Reproducibility — 8.0 / 10

**What's there:** Seed fixed. Parameters frozen. SHA256 hashes (first 16 chars). End-to-end reproduction script. MODEL_FREEZE documents exact commands.

**Why not higher:** SHA256 is truncated (16 chars is not cryptographically secure, but sufficient for accidental change detection). No Docker/venv lock file published alongside outputs. Python 3.13.11 is not pinned in a requirements.txt with all dependency versions locked.

**What raises it to 9:** Full SHA256 (64 chars). requirements.txt with pinned versions. Docker image or conda lock file.

---

## 12. Documentation — 7.0 / 10

**What's there:** MODEL_CARD, MODEL_FREEZE, README all comprehensive. Claims audit present. Forbidden phrases documented. Limitations explicit. Temperature correction and circular validation acknowledged.

**Why not higher:** StatsBomb 30/48 coverage not prominent in chart/LinkedIn. Reliability diagram not in public docs. Academic citations absent. "Heuristic" word absent from temperature correction description.

**What raises it to 9:** Add "Heuristic temperature correction" label. Add reliability diagram to MODEL_CARD. Cite Maher/Dixon-Coles. Add 30/48 StatsBomb note to LinkedIn.

---

## 13. Claims & Disclosure Honesty — 7.5 / 10

**What's there:** Forbidden claims list (8 phrases). Historical reference correctly labeled as internal after P4 clarification. No "beats betting markets" claim. Expert model limitations documented.

**Why not higher:** The phrase "temperature-corrected Elo model" sounds more rigorous than "Elo model with a hand-picked scaling factor." The "calibrated" in "Elo-calibrated" implies ECE correction — it means Elo-fitted, which is different. The word "validated" appears in documents where the only validation is circular.

**What raises it to 9:** Replace "calibrated" with "fitted" everywhere it refers to the MLE process. Add explicit sentence: "Temperature correction is a heuristic, not a statistically optimal choice."

---

## 14. Publication Readiness — 5.5 / 10

**What's there:** All files present. Tests pass. Chart generated. LinkedIn post written. Reproduction script works. Forbidden claims clean. READY TO PUBLISH flag from reproducibility script.

**Why not higher:** The model is ready for a "I built this for fun and learned a lot" LinkedIn post. It is NOT ready for a technical audience that will ask: "What's your out-of-sample champion prediction accuracy?" "How does this compare to bookmaker odds?" "What's your beta_elo confidence interval?" These questions have no answers in any current file.

**Publication tier:** Personal project / early-career portfolio. NOT industry-grade forecasting. NOT academic-publication-ready. NOT investment-grade.

**What raises it to 7.5:** Add one sentence: "Pre-WC2022, our model (retroactively applied) would have assigned Argentina X%. They won." Add bookmaker comparison table even if it shows we're worse. These two additions would make the honest-limitations argument bulletproof.

---

## Global Score Summary

| Dimension | Score |
|-----------|------:|
| 1. Data Quality | 6.0 |
| 2. Feature Engineering | 3.5 |
| 3. Model Specification | 6.0 |
| 4. Parameter Estimation | 3.5 |
| 5. Model Selection Rigor | 6.0 |
| 6. Calibration Quality | 3.0 |
| 7. Validation Methodology | 2.5 |
| 8. Uncertainty Quantification | 3.0 |
| 9. Code Quality | 7.0 |
| 10. Test Quality | 4.5 |
| 11. Reproducibility | 8.0 |
| 12. Documentation | 7.0 |
| 13. Claims Honesty | 7.5 |
| 14. Publication Readiness | 5.5 |
| **GLOBAL AVERAGE** | **5.25 / 10** |

---

## Grade interpretation

| Score | Industry equivalent |
|-------|---------------------|
| 8–10 | Publishable in a peer-reviewed journal or deployable in production at a quant fund |
| 6–8 | Credible personal research. Would survive a technical interview. Needs work before production. |
| **4–6** | **Solid foundations, serious validation gaps. Honest framing essential. This is us.** |
| 2–4 | Academic exercise. Public claims would require heavy caveating. |
| 0–2 | Prototype only. |

**Our score 5.25 / 10 is honest. The model is not garbage — it has real data, real MLE, real ablation. But the validation methodology (2.5), calibration correction (3.0), and uncertainty quantification (3.0) are below the bar for any serious forecasting claim. The strongest dimensions — reproducibility (8.0) and claims honesty (7.5) — are infrastructure, not statistics.**

---

## Priority improvements by ROI

1. **WC tournament-level backtest** (retroactive on WC2022): +0.5 to validation, +0.5 to publication readiness. 2–3 hours of work. Highest ROI.
2. **Expert coefficient MLE**: +1.0 to parameter estimation, +0.5 to feature engineering. 1–2 days. Would transform Expert model from opinion to data.
3. **Beta_elo bootstrap CI**: +0.5 to UQ, +0.3 to documentation. 2–3 hours. Shows you understand the difference between a point estimate and a range.
4. **Calibration correction (isotonic)**: +0.5 to calibration. 2–3 hours. Actually corrects the known 1.7pp bias.
5. **Bookmaker comparison**: +0.5 to validation, +0.5 to publication readiness. 4–6 hours. Puts the model in context. Even if we're worse, saying so is more credible than saying nothing.
