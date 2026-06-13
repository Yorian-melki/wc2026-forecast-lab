# Done vs Fake Done — WC2026 Model

Brutal categorization. Each item in exactly one bucket.  
"Fake done" = the code exists, the file exists, but the work it claims to represent was not actually performed with statistical rigor.

---

## TRULY DONE

These items produce real statistical or engineering value. A quant could verify and rely on them.

### Data
- **49,450 match dataset collected** — martj42 source, competitive/friendly split, 10,555 competitive matches used for MLE. Verifiable.
- **Results.csv ingested and structured** — Proper ETL pipeline. Tournament filter documented.

### Parameter Estimation
- **beta_elo MLE (0.543593)** — scipy.minimize on negative log-likelihood of match outcomes given Elo differences. n=10,555. Documented. Reproducible. Real statistical work.
- **DC rho MLE (-0.021007)** — Small, plausible value. Fitted via MLE. Standard procedure (Dixon-Coles 1997).
- **log_base (0.226934) and base_xg (1.2547) MLE** — Same optimization. These three parameters (beta, rho, log_base) are the only parameters with genuine statistical backing.

### Model Architecture
- **Independent Poisson + Dixon-Coles** — Published methodology. Correct implementation. Draw probabilities adjusted for low-scoring bivariate correlation. Real.
- **Elo rating engine (rolling, competitive-only)** — Standard international football Elo. 49,450 matches ingested. k-factor reasonable for international play.
- **48-team WC2026 bracket** — Exact tournament structure: 12 groups of 4, best-3rd advancement, R32→R16→QF→SF→Final. Penalty shootout model wired. Correct.

### Model Selection
- **P2.5 ablation study** — 9 model variants (A random through I full hybrid), 4 temporal splits, NLL and ECE both measured on test sets. 10,500+ matches per split. This is real ablation work. The finding (Full Hybrid ECE +17% worse, 0/4 clear wins) is honest.
- **ECE as model selection criterion** — Correct choice. NLL can improve while calibration degrades. Using both metrics is methodologically sound.
- **Full Hybrid rejection** — Correct decision, correctly documented, defensible.

### Validation Infrastructure
- **4 temporal train/test splits** — No data leakage. Forward-in-time. Proper.
- **WC2022 match holdout (64 matches)** — Small but real. Used only for NLL comparison.

### Output Verification
- **Conservation laws** — Σ P(champion)=1.000, Σ P(finalist)=2.000, Σ P(SF)=4.000, Σ P(QF)=8.000, Σ P(group_survival)=32.000 — all verified, all pass. This proves simulation correctness.
- **100,000 Monte Carlo simulations with fixed seed** — Reproducible. Seed=20260609. Deterministic.

### Publication Package
- **MODEL_CARD** — Comprehensive, limitations disclosed, claims honest. Real value.
- **MODEL_FREEZE** — Parameters frozen, commands documented, hash verification. Real value.
- **Reproduction script** — End-to-end automation that actually works (READY TO PUBLISH output verified).
- **Forbidden claims verification** — 8 phrases, automated, tested. Real safeguard.
- **Historical reference reframing** — The "historical WC reference → internal sanity check" correction in model_selection_report.md was a real fix that eliminated a misleading claim.

### Testing
- **Conservation law tests** — Test that the simulation probability totals are correct. Real statistical invariant.
- **beta_elo freeze test** — Prevents accidental modification. Real guard.
- **Forbidden claims parametrized tests** — 8 phrases × 4 documents = 32 tests. Real publication guard.

---

## PARTIALLY DONE

These items are started and provide some value, but the work is incomplete. Do not claim full completion.

### Data
- **Temporal form (16/48 teams)** — `temporal_form.py` computes proper exponential decay scores (λ=0.030, half-life≈23 days) for teams in form_history.csv. This is real for 16 teams. But 32 teams use a static default (50.0) that comes from teams.csv analyst judgment, not temporal data. The model treats all 48 teams' form with the same coefficient, creating a systematic asymmetry: 16 teams have data-driven form, 32 have analyst prior. This should be disclosed.

- **StatsBomb features (30/48 teams)** — 30 teams have real ppda and shot_quality data. 18 teams use hand-coded default values. The 18 defaults were chosen by an analyst, not derived from data. Partially real.

- **Jet lag factor** — Wired for all 48 teams. But uses a single representative city (Dallas, UTC-5) for all NA venues. Actual WC2026 venues span UTC-4 (Atlanta, Miami, Boston) to UTC-7 (Los Angeles, San Francisco). The approximation is better than nothing but not per-venue.

### Validation
- **WC2022 holdout** — 64 WC matches tested. Real. But WC matches are structurally different from general competitive matches (higher stakes, different lineup management, more defensive play). The holdout validates the model in that distribution but not the WC-specific distribution.

- **Significance testing** — z-tests are run. The testing logic is correct. But the variance parameter (0.40) is hardcoded, not computed from the actual NLL distribution of the test set. The p-values are therefore approximate.

### Documentation
- **StatsBomb 30/48 disclosure** — Present in MODEL_CARD. Not visible in chart or LinkedIn post. A general audience will not see it.
- **Temperature correction framing** — "Internally consistent, not externally validated" is present and honest. But the word "heuristic" does not appear. The choice of 0.55 is presented as "validated by concentration target" which implies objective criteria, not human judgment.

### Calibration
- **Reliability diagram** — `outputs/calibration/calibration_curve.png` exists. It was generated during P2.5. It is not referenced or included in any public document.

---

## FAKE DONE

These items have files, code, or labels that imply statistical work was done. The underlying statistical work was not done. Using these as evidence of rigor is misleading.

### Expert model coefficients (11 + 5 = 16 parameters)

**What exists:** A `_latent_score()` function in expert_model.py with values like `attack: 0.060`, `midfield: 0.030`, `ppda: 0.030`, `shot_quality: 5.000`, `press_intensity: 0.400`.

**What was actually done:** An analyst (the developer) assigned these values based on intuition about which features matter and by how much.

**What the code says:** `# Analyst-prior attributes (0-100 scale; not statistically calibrated)` and `# Coefficients are analyst priors — not calibrated via MLE`

**Why it's fake done:** These are not model parameters. They are opinions. Publishing the Expert model as a "model" implies they were estimated from data. They were not. The Expert model is a simulation of what someone thinks the world looks like. It may even be correct, but there is zero statistical backing.

**The danger:** If someone asks "what's the 95% CI on your shot_quality coefficient?" the answer is "there is no CI because it was never estimated." That breaks any claim of statistical validity.

---

### Temperature correction (beta_mul = 0.55)

**What exists:** `beta_elo = 0.988351 × 0.55 = 0.543593`. Documented. Tested. Frozen.

**What was actually done:** Ran temperature ablation at 5 values (0.40, 0.55, 0.70, 0.85, 1.00). Observed that 0.55 brings top-3 concentration to ~42%. Judged 42% to look "reasonable." Chose 0.55.

**Why it's fake done:** There is no optimization criterion for 42%. No historical WC data says "pre-tournament top-3 concentration should be 36-42%." The validation — running the same corrected model on WC2018/2022 Elo snapshots — is circular: of course it gives the same concentration, it's the same beta. The "validation" proves consistency, not correctness.

**The honest statement:** "We chose beta_mul=0.55 because it produced a concentration level that appeared plausible to the developer. We then confirmed this is internally consistent by running the same model on past Elo snapshots. We did not optimize this parameter or validate it against actual WC champion outcomes."

---

### Historical WC validation (36–39% concentration)

**What exists:** `outputs/calibration/historical_tournament_concentration.csv` showing 35.58% (WC2018 Elo snapshot) and 39.20% (WC2022 Elo snapshot).

**What was actually done:** Ran our WC2026 simulator with beta=0.544 on Elo ratings as of pre-WC2018 and pre-WC2022. Observed top-3 concentrations of 35.6% and 39.2%.

**Why it's fake done:** This is circular validation. We used the same beta=0.544 that we chose to get ~42%, applied it to different Elo inputs, and got similar concentrations. This proves the model is self-consistent. It does not prove anything about whether 42% is the right concentration. It does NOT test whether our model would have assigned a high probability to France (WC2018 winner) or Argentina (WC2022 winner).

**Fixed in P4 clarification:** The misleading framing in model_selection_report.md was corrected to say "internal sanity check." The underlying circularity remains — only the labeling was fixed.

---

### Statistical significance of model improvements

**What exists:** `outputs/calibration/significance_report.csv` with z-scores and p-values comparing models E (reference) vs I (Full Hybrid).

**What was actually done:** z = (NLL_E - NLL_I) / sqrt(variance / n) with variance=0.40 hardcoded.

**Why it's fake done:** The variance of NLL differences depends on the distribution of the test set outcomes. Setting variance=0.40 without computing it from data is an assumption. With different data distributions, the "true" variance could be 0.25 or 0.60, changing the p-values significantly. The significance report looks rigorous but the key input is not data-derived.

**Note:** The finding (Full Hybrid not significantly better than Elo reference) likely holds qualitatively. The fake-done label is about methodology, not conclusion.

---

### "350 tests — full statistical validation"

**What exists:** 350 passing tests in 14.86s across 19 test files.

**What was actually done:** ~200 tests verify: files exist, CSV has expected columns, JSON has expected keys, probabilities sum to 1, conservation laws pass. These are infrastructure guards.

**Why it's partially fake done:** The 350 tests do not collectively validate the statistical claims of the publication. They validate: "the simulation ran, produced numbers that sum correctly, and didn't accidentally include forbidden phrases." They do not validate: "the champion probabilities are calibrated," "the model is better than a naive benchmark for WC outcomes," or "the temperature correction produces plausible champion estimates."

Calling this "full statistical validation" (which is implied by 350 passing tests) is an overstatement.
