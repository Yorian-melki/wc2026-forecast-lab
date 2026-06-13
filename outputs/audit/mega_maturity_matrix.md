# Mega Maturity Matrix — WC2026 Model Audit

**Standard:** What a quant lab or probabilist team with 10+ years of forecasting budget would demand.  
**Scoring:** Pessimistic. 50% on any item means "half the work was done, half was assumed."  
**Status codes:** DONE / PARTIAL / FAKE_DONE / NOT_DONE  
FAKE_DONE = exists in code but provides no statistical validity; creates false confidence.

---

## DATA (items 1–7)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 1 | Raw data collection (49,450 matches) | DONE | 95% | LOW | Acceptable. martj42 is a known community dataset. |
| 2 | Data deduplication audit | PARTIAL | 30% | MEDIUM | Friendly/competitive split done. No row-level duplicate check confirmed. |
| 3 | Friendly match exclusion for MLE | DONE | 80% | LOW | Competitive-only filter documented, 10,555 matches. |
| 4 | StatsBomb feature coverage | PARTIAL | 62% | MEDIUM | 30/48 teams real. **18 teams use hand-coded defaults.** Not disclosed in chart or LinkedIn. |
| 5 | Temporal form history coverage | PARTIAL | 33% | MEDIUM | **16/48 teams** have form_history.csv. 32 use static default 50.0. |
| 6 | Data freshness / snapshot date | DONE | 85% | LOW | snapshot_date=2026-04-04 in config.json. |
| 7 | Pre-tournament update procedure | NOT_DONE | 0% | MEDIUM | No documented procedure for updating Elo or form from snapshot to tournament start. |

---

## FEATURE ENGINEERING (items 8–14)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 8 | Elo ratings (rolling MLE) | DONE | 85% | LOW | Standard. MLE documented. k-factor specified. |
| 9 | Temporal form / recency weighting | **FAKE_DONE** | **10%** | **HIGH** | `temporal_form.py` exists with decay λ=0.030. **Wired for 16/48 teams only.** 32 teams use static analyst rating. The form coefficient 0.008 in match_model is an analyst prior, not temporal-decay-derived. Two systems partially disconnected. |
| 10 | Jet lag factor | PARTIAL | 40% | MEDIUM | `compute_jet_lag()` wired for all 48 teams. But uses single NA venue (Dallas UTC-5). Actual venues span UTC-4 to UTC-7. No empirical validation of performance_factor. |
| 11 | Home advantage (USA/MEX/CAN) | PARTIAL | 50% | MEDIUM | +8% xG hard-coded. No regression on actual host-nation WC results. No CI. |
| 12 | Expert analyst ratings | **FAKE_DONE** | **0%** | **HIGH** | Code comment: *"not statistically calibrated"*. Zero MLE. Zero CV. Human prior dressed as model feature. |
| 13 | StatsBomb ppda/shot_quality | **FAKE_DONE** | **20%** | **HIGH** | Coefficients (ppda=0.030, shot_quality=5.000) are analyst priors. Applied to 30 real teams and 18 defaults. No regression backing. |
| 14 | Penalty model | PARTIAL | 40% | LOW | Computed from analyst ratings — same caveat as above. |

---

## MODEL SPECIFICATION (items 15–18)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 15 | Independent Poisson match model | DONE | 90% | LOW | Standard. Well-understood in sports analytics. |
| 16 | Dixon-Coles low-score correction | DONE | 80% | LOW | rho=-0.021 MLE-fitted. Correct implementation. |
| 17 | 48-team WC bracket mechanics | DONE | 95% | LOW | Exact structure including best-3rd tiebreak. |
| 18 | Home advantage specification | PARTIAL | 40% | MEDIUM | xG multiplier at group stage only. No stadium-specific or neutral-venue KO adjustment. |

---

## PARAMETER ESTIMATION (items 19–24)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 19 | beta_elo MLE | DONE | 80% | LOW | MLE on 10,555 matches. Documented. |
| 20 | DC rho MLE | DONE | 80% | LOW | rho=-0.021. Plausible and small. |
| 21 | log_base / base_xg MLE | DONE | 75% | LOW | From same MLE. Reasonable. |
| 22 | Expert model coefficients | **FAKE_DONE** | **0%** | **HIGH** | "Analyst priors — not calibrated via MLE." Source says it. |
| 23 | Temperature correction selection | **FAKE_DONE** | **15%** | **HIGH** | beta_mul=0.55 chosen so top3≈42%. No optimization criterion. No out-of-sample test. Heuristic. |
| 24 | CI on beta_elo | NOT_DONE | 0% | HIGH | No bootstrap, no Fisher CI. We do not know the uncertainty on beta_elo. Probabilities inherit invisible uncertainty. |

---

## MODEL SELECTION (items 25–30)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 25 | Ablation study design | DONE | 85% | LOW | 9 models × 4 temporal splits. Well-designed. |
| 26 | NLL comparison | DONE | 80% | LOW | Differences small (0.002) and correctly interpreted. |
| 27 | ECE comparison | DONE | 80% | LOW | ECE shows Full Hybrid worse (+17%). Key finding. |
| 28 | Statistical significance testing | PARTIAL | 40% | **HIGH** | z-tests done but **variance hardcoded at 0.40**. Significance claims are approximate at best. |
| 29 | **WC tournament-level champion prediction backtest** | **NOT_DONE** | **0%** | **HIGH** | **MOST IMPORTANT MISSING TEST.** Given pre-WC2018 Elo + beta=0.544, what probability did our model assign to France (actual winner)? We don't know. This is the only test that truly validates tournament champion probability. |
| 30 | External forecast comparison | NOT_DONE | 0% | HIGH | No comparison to FiveThirtyEight, Goldman Sachs, Gracenote, or bookmaker odds. |

---

## CALIBRATION (items 31–34)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 31 | ECE measurement | DONE | 80% | LOW | ECE=0.017 on test sets. Measured correctly. |
| 32 | Reliability diagram | PARTIAL | 50% | MEDIUM | calibration_curve.png exists. Not in public docs. |
| 33 | Calibration correction (isotonic/Platt) | NOT_DONE | 0% | MEDIUM | ECE measured, not corrected. We know probabilities are off by ~1.7pp avg and did nothing about it. |
| 34 | Tournament-level probability calibration | NOT_DONE | 0% | HIGH | Match-level ECE ≠ champion probability calibration. Compounding over 7 rounds amplifies any per-match bias. Not tested. |

---

## VALIDATION (items 35–39)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 35 | Temporal cross-validation (match-level) | DONE | 80% | LOW | 4 temporal splits, no leakage. Clean. |
| 36 | WC tournament holdout (2022) | PARTIAL | 50% | MEDIUM | 64 WC matches. Small sample. WC matches structurally different from training data. |
| 37 | Bootstrap parameter uncertainty | NOT_DONE | 0% | HIGH | No bootstrap on MLE parameters. Point estimates presented as truth. |
| 38 | Historical WC champion backtest | **FAKE_DONE** | **5%** | **HIGH** | Originally "historical WC reference". Now correctly labeled "internal sanity check" after P4 clarification audit. But the test itself is circular: runs same beta=0.544 on WC2018/2022 Elo snapshots. Does not test whether France was assigned high probability pre-WC2018. |
| 39 | Sensitivity analysis on key parameters | NOT_DONE | 0% | MEDIUM | No table: "if beta_elo=0.50 vs 0.60, champion probs change by X%." Missing. |

---

## UNCERTAINTY QUANTIFICATION (items 40–42)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 40 | Wilson CIs on champion probs | PARTIAL | 60% | LOW | Wilson CIs from Monte Carlo sampling variance only. Does not include parameter uncertainty. |
| 41 | Ensemble / model averaging | NOT_DONE | 0% | MEDIUM | Expert and Elo run separately. No formal ensemble. |
| 42 | Scenario analysis (injuries, etc.) | NOT_DONE | 0% | LOW | Expected in production forecasting. Not present. |

---

## CODE QUALITY (items 43–45)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 43 | Architecture and modularity | DONE | 80% | LOW | Clean structure. Lazy init. Good. |
| 44 | Hardcoded magic constants | PARTIAL | 50% | MEDIUM | config.json rho=0.08 vs MLE rho=0.021. Which is used? |
| 45 | Significance variance hardcoded | PARTIAL | 30% | HIGH | significance.py variance=0.40 hardcoded. Affects all significance claims. |

---

## TESTING (items 46–49)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 46 | Total test count (350 passing) | DONE | 85% | LOW | 350 passing in 14.86s. Infrastructure solid. |
| 47 | Statistical invariant tests | PARTIAL | 40% | MEDIUM | Conservation laws tested well. Calibration not tested post-simulation. |
| 48 | Existence/schema tests | DONE | 95% | LOW | These are CI safeguards, not validity tests. |
| 49 | Missing critical tests | NOT_DONE | 0% | HIGH | No test for: WC holdout champion accuracy, beta_elo bootstrap CI, sensitivity to beta_mul±0.05, form_history 16-team coverage assertion. |

---

## DOCUMENTATION (items 50–54)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 50 | MODEL_CARD | DONE | 90% | LOW | Comprehensive. Limitations honest. |
| 51 | MODEL_FREEZE | DONE | 90% | LOW | Parameters frozen. Commands correct. |
| 52 | README | DONE | 85% | LOW | Complete and accurate. |
| 53 | StatsBomb coverage disclosure | PARTIAL | 50% | MEDIUM | 30/48 in MODEL_CARD. Not visible in chart or LinkedIn post. |
| 54 | Temperature correction framing | PARTIAL | 65% | MEDIUM | Disclosed but not labeled "heuristic". Implies more rigor than exists. |

---

## PUBLICATION (items 55–59)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 55 | Forbidden claims verified | DONE | 95% | LOW | 8 phrases checked. Automated in reproduce script. |
| 56 | Chart accuracy | DONE | 85% | LOW | Correct probabilities. Honest footer. |
| 57 | LinkedIn post accuracy | DONE | 80% | LOW | Numbers correct. No overclaims. |
| 58 | Betting market comparison | NOT_DONE | 0% | HIGH | No comparison to actual odds. Cannot claim competitive or inferior. |
| 59 | Academic citations | NOT_DONE | 0% | LOW | Maher (1982), Dixon-Coles (1997) not cited. Expected in technical writeup. |

---

## REPRODUCIBILITY (items 60–62)

| # | Item | Status | Completion% | Public Risk | What quant labs say |
|---|------|--------|:-----------:|:-----------:|---------------------|
| 60 | Seed fixed and documented | DONE | 100% | LOW | seed=20260609. |
| 61 | Parameter hash verification | DONE | 90% | LOW | SHA256 (first 16 chars) in manifest. |
| 62 | End-to-end reproduction script | DONE | 90% | LOW | reproduce_public_outputs.py. 5 steps. Works. |

---

## Summary counts

| Status | Count | % of total |
|--------|------:|----------:|
| DONE | 20 | 32% |
| PARTIAL | 17 | 27% |
| FAKE_DONE | 7 | 11% |
| NOT_DONE | 18 | 29% |

**Headline: 32% truly done. 40% of remaining items carry HIGH public risk if called out.**
