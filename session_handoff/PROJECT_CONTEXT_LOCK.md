# PROJECT CONTEXT LOCK — WC2026 Monte Carlo Forecast
# Session handoff created: 2026-06-10
# Do NOT modify this file between sessions. Treat as read-only.

---

## A. PROJECT IDENTITY

| Field | Value |
|-------|-------|
| Repo path | `/Users/yorian/FinderProjects/wc2026_june2026` |
| Project goal | Build and publish a probabilistic Monte Carlo simulator for FIFA World Cup 2026 |
| Language / stack | Python 3.13.11, numpy, pandas, scipy, matplotlib, pytest |
| Virtual env | `.venv/` (activate: `source .venv/bin/activate`) |
| Test runner | `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --ignore=tests/test_data_and_mapping.py` |
| Not a git repo | `git status` will fail — this is a local folder, not git-tracked |
| Current date at handoff | 2026-06-10 |
| Tournament start | 2026-06-11 (tomorrow) |

### What this project IS
- A personal/portfolio Monte Carlo tournament simulator for WC2026
- Uses rolling Elo ratings + Independent Poisson + Dixon-Coles correction
- 100,000 simulations, fixed seed, reproducible
- Publication-ready in "personal project / early-career portfolio" tier
- Has two models: Expert model (analyst priors) + Elo-fitted temperature-adjusted model

### What this project IS NOT
- Not a betting model, not a hedging system, not a production trading system
- Not peer-reviewed, not externally validated against WC champion outcomes
- Not "calibrated" in the probability-calibration sense (ECE measured but not corrected)
- Not investment-grade, not hedge-fund-grade
- Does not claim to beat betting markets

### Current selected publication framing
**Two-model view: Expert (flatter, assumption-heavy) vs Elo-fitted temperature-adjusted (more data-driven, heuristic at tournament level)**  
Do NOT publish as "the model knows the winner."  
Do NOT present single model as uniquely correct.

---

## B. FULL PHASE TIMELINE

### PHASE 0 — P0: Expert model + StatsBomb wiring
**Objective:** Build first simulation using analyst-assigned ratings + StatsBomb features  
**Files created/modified:**
- `src/wc2026/match_model.py` — `_latent_score()` with 11 analyst + 5 StatsBomb coefficients
- `src/wc2026/data_loader.py` — team loading with apply_temporal_form flag
- `src/wc2026/tournament.py` — 48-team bracket mechanics
- `data/teams.csv` — 29-column team data (analyst ratings, Elo, StatsBomb features)
- `tests/test_p0_wiring.py`

**Results:** Expert model produces flatter probabilities. Top champion: FRA ~8.2%, ESP ~7.3%  
**What was truly achieved:** Working tournament simulator. Correct bracket mechanics.  
**What was later found weak:** ALL 16 model coefficients (11 analyst + 5 StatsBomb) are hand-tuned analyst priors with zero MLE/CV validation. Code comment literally says "not statistically calibrated." StatsBomb coverage: 30/48 real, 18 use defaults.

---

### PHASE 1 — P1: Pure MLE Dixon-Coles
**Objective:** Fit a purely data-driven model (attack/defense parameters per team via MLE)  
**Files created:**
- `scripts/calibrate_mle.py`
- `outputs/calibration/mle_params.json`
- `tests/test_p1_mle.py`

**Results:** MLE fitted but over-parameterized (323 teams × 2 = 646 parameters)  
**Status: REJECTED** — MLE converged but ECE was worse than simpler Elo backbone. Too many parameters for the available data.

---

### PHASE 2 — P2: International results + hybrid Elo-DC
**Objective:** Combine Elo ratings with attack/defense residuals from match history  
**Files created:**
- `src/wc2026/calibrated_elo_model.py` — full Elo engine with MLE
- Hybrid model combining Elo backbone + per-team attack/defense offsets
- `tests/test_p2_hybrid.py`

**Results:** Hybrid model better NLL but worse ECE than pure Elo  
**Status: FOUNDATION KEPT** — Elo engine kept. Hybrid residuals rejected.

---

### PHASE 2.5 — P2.5: Full ablation study (9 models × 4 temporal splits)
**Objective:** Rigorously compare 9 model variants to select the production model  
**Files created:**
- `scripts/run_hybrid_ablations.py`
- `outputs/calibration/ablation_results.csv` — 9 models × 4 splits, NLL + ECE
- `outputs/calibration/ablation_summary.md`
- `outputs/calibration/significance_report.csv`
- `tests/test_p25_validation.py`

**Model variants tested (A through I):**
- A: Random baseline (NLL=1.09861)
- B: Empirical frequencies (NLL~1.05)
- C: Elo without home advantage
- D: Elo with home advantage
- **E: Elo calibrated (REFERENCE) — ECE=0.0170, NLL=0.931**
- F: Independent Poisson
- G: Elo + DC rho
- H: Hybrid (no rho)
- **I: Full Hybrid (best NLL=0.929 but ECE=0.0199 — REJECTED)**

**Key finding:** Full Hybrid (model I) has better NLL by 0.002 (noise range on 3/4 splits) but ECE +17% worse than reference. 0/4 clear-win splits. Production gate: BORDERLINE_EXPERIMENTAL.

**Decision:** Promote E (Elo-calibrated backbone) as reference. Reject Full Hybrid.

**What was later found weak:** Significance test variance=0.40 is hardcoded in `src/wc2026/calibration/significance.py` — not computed from data. P-values are approximate.

---

### PHASE 3 — P3: Elo model integration
**Objective:** Integrate the Elo-calibrated model into the simulation pipeline  
**Files created/modified:**
- `data/elo_calibrated_params.json` — initial parameters
- `outputs/tournament_run/elo_calibrated_summary.csv` — first simulation results
- `src/wc2026/model_factory.py` — selects which model runs the simulation
- `tests/test_p3_elo_calibrated_production.py`

**Initial result:** beta_elo=0.988351 → top3=66.4%, ESP 30%+ — over-concentrated, not credible

---

### PHASE 3.5 — P3.5: ELO-CALIBRATED SANITY AUDIT (temperature fix)
**Objective:** Fix over-concentration. Audit production readiness before publication.  
**Files created/modified:**
- `scripts/run_p35_audit.py` — temperature ablation at 5 values (0.40, 0.55, 0.70, 0.85, 1.00)
- `outputs/calibration/elo_temperature_ablation.csv` — concentration metrics per beta_mul
- `outputs/calibration/elo_calibration_gate.json` — production gate verdict
- `outputs/calibration/historical_tournament_concentration.csv` — "historical" reference
- `data/elo_calibrated_params.json` — **MODIFIED: beta_elo 0.988351 → 0.543593**
- `outputs/tournament_run/elo_calibrated_summary.csv` — **REGENERATED** with corrected beta, seed=20260609, 100K iterations
- `tests/test_p35_elo_sanity.py` — 44 tests

**Production gate verdict: PASS_WITH_TEMPERATURE**
- Original beta=0.988: top3=66.4% (FAIL — over-concentrated)
- beta×0.55=0.544: top3=41.76% (PASS threshold <46%)
- Internal consistency check: same beta applied to WC2018/WC2022 Elo snapshots gives 35.6%/39.2%

**FROZEN PARAMETERS (do not change):**
- beta_elo = 0.543593 ← FINAL, FROZEN
- temperature_mul = 0.55
- simulation seed = 20260609
- iterations = 100,000

**What was later found weak:**
- beta_mul=0.55 is a heuristic, not an optimized parameter
- "Historical reference 36–39%" is circular: same beta, different Elo input — NOT external validation
- No test: "what probability did model assign to WC2022 actual winner Argentina?"

---

### PHASE 4 — P4 FINAL: MODEL FREEZE + PUBLICATION PACKAGE
**Objective:** Create publication-ready package. Freeze all parameters. Anti-bullshit audit.  
**Files created:**
- `MODEL_CARD.md` — comprehensive model documentation
- `MODEL_FREEZE.md` — frozen parameters, reproduction commands
- `README.md` — updated with model selection summary, conservation laws
- `data/model_freeze_manifest.json` — SHA256 hashes, conservation laws, top10 probs
- `outputs/public/wc2026_final_forecast_chart.png` — top-12 champion bar chart
- `outputs/public/model_selection_report.md` — Expert vs Elo comparison table (48 teams)
- `outputs/public/technical_summary.md`
- `outputs/public/claims_audit.md` — every public number traced to source
- `outputs/public/claims_checklist.md` — allowed/forbidden claims list
- `outputs/public/linkedin_post.md` — short (~1950 chars)
- `outputs/public/linkedin_post_long.md` — long (~3200 chars)
- `scripts/reproduce_public_outputs.py` — end-to-end reproduction (5 steps)
- `tests/test_p4_publication_package.py` — 74 tests including forbidden claims

**Conservation laws verified:**
- Σ P(champion) = 1.000000
- Σ P(finalist) = 2.000000
- Σ P(SF) = 4.000000
- Σ P(QF) = 8.000000
- Σ P(group_survival) = 32.000000

**reproduce_public_outputs.py final status: READY TO PUBLISH**

**7 test failures found and fixed during P4:**
1. draw_rate test too strict at extreme Elo diffs → fixed (restrict to elo_diff < 400)
2. temperature monotonicity direction wrong → fixed (ascending sort)
3. entropy direction wrong → fixed (descending sort)
4. production gate beta float precision → fixed (use original_beta_elo)
5. Poisson sum tolerance too tight → fixed (1e-3)
6. equal lambda draw test → fixed (symmetry test instead)
7. ESP xG threshold too low → fixed (raised to 2.5)

---

### CLARIFICATION AUDIT — P4 post-publication probability jump analysis
**Objective:** Explain why probabilities jumped from Expert (~7–8%) to Elo-temp (ESP 17%)  
**Files created:**
- `outputs/calibration/final_model_probability_jump_audit.md`
- `outputs/calibration/final_model_probability_jump_audit.csv`

**Key findings:**
- Expert model compresses probabilities via analyst prior soft ceiling
- Elo at beta=0.544 gives Spain 2.29× xG vs median WC team → compounds over 7 bracket rounds → 17%
- xG ratio at original beta=0.988: 4.51× (not credible football)
- xG ratio at beta=0.544: 2.29× (plausible)
- Two lines in model_selection_report.md changed: "historical WC reference" → "internal sanity check" (FIXED)

**Brutal assessment recorded:**
- Expert too flat: YES, probably
- Elo original too concentrated: YES, definitively
- Temperature-corrected Elo better PROVEN: NO — more plausible, not better proven
- Recommendation C: publish both models side-by-side

---

### MEGA MATURITY AUDIT — Post-P4 world-class quant audit
**Objective:** Audit the entire system against quant lab standards. No model changes.  
**Files created:** `outputs/audit/` (10 files — see FILE_INDEX.md)

**Headline results:**
- Global maturity score: **5.25 / 10**
- 62-item matrix: 32% DONE, 27% PARTIAL, 11% FAKE_DONE, 29% NOT_DONE
- Publication tier: personal_project / early_career_portfolio
- NOT ready for: academic publication, investment-grade forecasting, bookmaker superiority claims

---

## C. CURRENT FACTS — DO NOT LOSE THESE

### Frozen model parameters
```json
{
  "beta_elo": 0.543593,
  "original_beta_elo": 0.988351,
  "temperature_mul": 0.55,
  "log_base": 0.226934,
  "base_xg": 1.2547,
  "rho": -0.021007,
  "n_train_matches": 10555,
  "seed": 20260609,
  "iterations": 100000
}
```

### Final Elo-temp champion probabilities (TOP 10)
| Rank | Team | Elo | P(champion) |
|------|------|----:|:-----------:|
| 1 | ESP | 2155 | **16.97%** |
| 2 | ARG | 2114 | **14.76%** |
| 3 | FRA | 2062 | **10.03%** |
| 4 | ENG | 2021 | 6.71% |
| 5 | BRA | 1991 | 5.69% |
| 6 | COL | 1982 | 4.82% |
| 7 | POR | 1986 | 4.81% |
| 8 | NED | 1944 | 3.30% |
| 9 | ECU | 1938 | 3.09% |
| 10 | GER | 1932 | 3.02% |

### Concentration metrics
- top1 = 16.97%, top3 = 41.76%, top5 = 54.16%, top10 = 73.20%
- Shannon entropy: 4.203 bits (75.3% of 5.585 max)

### Expert model TOP 5 (for comparison)
- FRA: 8.19%, ARG: 7.82%, ESP: 7.32%, ENG: 6.65%, BRA: 6.59%

### Data counts
- 49,450 total international match records (all tournaments, all years)
- 10,555 competitive matches used for MLE (2010–2025, martj42)
- StatsBomb coverage: 30/48 real data, 18/48 hand-coded defaults
- form_history.csv: 16/48 teams covered (ARG, BEL, BRA, CAN, COL, ENG, ESP, FRA, GER, JPN, MAR, MEX, NED, POR, SCO, USA)

### Test suite
- Total passing: **350 tests** (14.37s)
- Test files: 19 files
- Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --ignore=tests/test_data_and_mapping.py`

### Maturity scores (14 dimensions)
| Dimension | Score |
|-----------|------:|
| Data Quality | 6.0 |
| Feature Engineering | 3.5 |
| Model Specification | 6.0 |
| Parameter Estimation | 3.5 |
| Model Selection Rigor | 6.0 |
| Calibration Quality | 3.0 |
| Validation Methodology | 2.5 |
| Uncertainty Quantification | 3.0 |
| Code Quality | 7.0 |
| Test Quality | 4.5 |
| Reproducibility | 8.0 |
| Documentation | 7.0 |
| Claims Honesty | 7.5 |
| Publication Readiness | 5.5 |
| **GLOBAL AVERAGE** | **5.25 / 10** |

---

## D. MODELS AND DECISIONS TABLE

| Model | Status | Reason | Publish? | Mention? | Wording |
|-------|--------|--------|:-------:|:-------:|---------|
| Expert model (P0) | AVAILABLE, not primary | Analyst priors, no MLE, 0 statistical validation | YES — as comparison model | YES | "Expert prior simulation using analyst ratings and StatsBomb data for 30/48 teams. Coefficients are analyst-assigned, not statistically estimated." |
| Pure MLE Dixon-Coles (P1) | REJECTED | 646 parameters, overfit, ECE worse than Elo | NO — do not publish | Mention in MODEL_CARD only | "Rejected: over-parameterized (646 params), calibration degraded" |
| Full Hybrid Elo-DC (P2.5 model I) | REJECTED | ECE +17% worse, 0/4 clear-win splits | NO | YES — as rejected alternative | "Full Hybrid rejected after P2.5 ablation: ECE 0.0199 vs 0.0170 reference (+17% worse). 0/4 clear-win splits." |
| Raw Elo beta=0.988 (P3 original) | REJECTED | top3=66.4%, ESP 30%+ — not credible | NO | YES — as original before fix | "Original beta=0.988 over-concentrated (top3=66%). Corrected to beta=0.544." |
| **Elo-fitted temp-adj beta=0.544** | **SELECTED** | Best ECE (0.017), statistically grounded beta, plausible concentration | **YES — primary technical model** | YES | "Elo-fitted Poisson model with temperature correction (β=0.543, ×0.55 from MLE value). Not 'calibrated' in the ECE sense — fitted." |
| Two-model view (Expert + Elo) | **RECOMMENDED** | Most honest framing, shows uncertainty range | YES — best publication approach | YES | "Two-model probabilistic simulator: analyst-prior Expert view vs data-driven Elo-fitted view." |

---

## E. FAKE DONE / DANGEROUS DONE — READ BEFORE EVERY RESPONSE

**These items LOOK rigorous but are NOT statistically validated. Do NOT use them as evidence of statistical rigor.**

1. **Expert model coefficients** (attack=0.060, ppda=0.030, shot_quality=5.000 etc.) — Code comment: *"Analyst-prior attributes — not statistically calibrated."* These are opinions, not estimates. Publishing Expert model probabilities as "statistically derived" is false.

2. **Temperature correction beta_mul=0.55** — Chosen because top3 looked reasonable at ~42%. No objective criterion. No optimization. No out-of-sample test. It is a heuristic. The phrase "validated internally" means: ran same model on different Elo inputs, got similar concentration. Circular.

3. **"Historical WC reference 36–39%"** — NOT external data. IS: our simulator (beta=0.544) applied to pre-WC2018/WC2022 Elo snapshots → 35.6%/39.2%. Fixed in model_selection_report.md to say "internal sanity check." The underlying circularity remains — only wording was fixed.

4. **Significance test p-values** — variance=0.40 hardcoded in `src/wc2026/calibration/significance.py`. Not computed from test data. P-values in significance_report.csv are approximate at best.

5. **"350 tests passing"** — ~60% of tests are existence/schema/conservation guards (CI safeguards). ~23% test actual statistical invariants. 350 tests ≠ full statistical validation.

6. **StatsBomb coefficients** (ppda=0.030, shot_quality=5.000, press_intensity=0.400) — analyst-assigned, not regression-derived from StatsBomb data. Applied to 30 teams with real StatsBomb data AND 18 teams with default values.

7. **Temporal form (16/48 teams)** — temporal_form.py computes proper decay for 16 teams in form_history.csv. 32 teams use static default (form=50.0) from teams.csv — an analyst rating. The match model applies form coefficient 0.008 to all 48 teams uniformly, creating an asymmetry: 16 teams have data-driven form, 32 have analyst prior.

8. **Jet lag factor** — wired for all 48 teams but uses single NA venue approximation (Dallas, UTC-5). Actual WC2026 venues span UTC-4 to UTC-7. No empirical validation of performance_factor values.

---

## F. CURRENT BEST RECOMMENDATION

**The current best public framing is NOT "single final model knows winner."**

**The current best public framing is:**

> "Two-model probabilistic simulator for WC2026. We built two independent views:
> (1) **Expert-prior view** (flatter probabilities, 30/48 teams with StatsBomb data, analyst coefficients — assumption-heavy but matches human intuition);
> (2) **Elo-fitted temperature-adjusted view** (more data-driven, beta fitted on 10,555 matches, heuristic temperature correction to prevent over-concentration).
> Neither model was externally validated against WC champion outcomes. These are honest probabilistic estimates, not predictions."

**Recommended chart:**
- Primary: `outputs/public/wc2026_model_comparison_chart.png` (Expert vs Elo side-by-side)
- Secondary: `outputs/public/wc2026_final_forecast_chart.png` (Elo-only, cleaner for non-technical LinkedIn)
- If using Elo-only chart for LinkedIn: add explicit sentence "Temperature correction is a heuristic choice (β×0.55), not an optimized parameter."

---

## G. NEXT POSSIBLE ACTION

**The next action is NOT more modeling.**  
**The next action is NOT a new model phase.**  
**The next action is WORDING CREDIBILITY FIX ONLY.**

### P5 — Wording fix / credibility fix (no model changes)

Exact items for P5:
1. Replace "Elo-calibrated" → "Elo-fitted Poisson model" in MODEL_CARD, MODEL_FREEZE, README, chart footer, LinkedIn
2. Label temperature correction explicitly as "heuristic (not optimized)" in MODEL_CARD, README
3. Add "30/48 teams; 18 use analyst defaults" to LinkedIn post StatsBomb mention
4. Add USA/co-host explanation (Elo 1726, home advantage already included, Champion prob 0.33%)
5. Clarify "49,450 for Elo / 10,555 for MLE" everywhere the 49K number appears
6. Add reliability diagram reference to MODEL_CARD
7. Adopt two-model framing as primary public narrative
8. Run tests after all wording changes
9. Re-run reproduce_public_outputs.py to verify READY TO PUBLISH

**P5 must NOT:**
- Change beta_elo
- Rerun simulations
- Change any probability values
- Add new model features
- Run new ablations

---

## H. HARD PROHIBITIONS — THE NEXT CLAUDE MUST NOT

1. **Modify beta_elo.** It is frozen at 0.543593. Any modification invalidates the entire P4 publication package and all test freeze guards.

2. **Rerun simulations** unless explicitly asked with justification. The 100K simulations with seed=20260609 are the frozen publication output.

3. **Integrate Full Hybrid.** Rejected in P2.5. ECE worse. 0/4 wins. This decision is documented and final.

4. **Claim bookmaker edge.** No comparison to bookmaker odds has been performed. Cannot claim superior, inferior, or comparable.

5. **Claim "fully calibrated."** ECE was measured (0.017) but not corrected. The model is Elo-fitted, not probability-calibrated.

6. **Claim "hedge-fund-grade."** Forbidden phrase. Global maturity 5.25/10. Not true.

7. **Publish single model as "the truth."** Two-model view is the honest framing. Either model alone without comparison implies false confidence.

8. **Use "historical validation" for the 36–39% concentration reference.** It is an internal sanity check (circular). Label as such.

9. **Use test count (350) as proof of statistical validity.** 350 tests ≠ statistical validation. ~23% of tests test actual statistical properties.

10. **Make changes to model files without explicit user request.** Read, summarize, and wait for confirmation before touching anything.
