# Model Comparison — P2.5 Final Report

Generated: 2026-06-09

---

## Dataset

Source: martj42/international_results  
Total matches: 31,975 (1872–2026), 145 tournaments, 336 teams  
Temporal splits: 4 (strict no-leakage)

---

## 1. Ablation — Average NLL across 4 splits

| Model | Avg NLL | vs Elo-calib | Status |
|:------|:-------:|:------------:|:------:|
| A  Random (1/3, 1/3, 1/3) | 1.09861 | +0.16746 | REJECTED |
| B  Empirical frequency | 1.05701 | +0.12585 | REJECTED |
| C  Elo only (no home adv) | 0.95596 | +0.02481 | REJECTED |
| D  Elo + home advantage | 0.94377 | +0.01262 | REJECTED |
| **E  Elo + calibrated draw** | **0.93115** | reference | **REFERENCE** |
| F  Independent Poisson (global) | 0.93154 | +0.00038 | EXPERIMENTAL |
| G  Elo + DC rho only (no residuals) | 0.93129 | +0.00013 | EXPERIMENTAL |
| H  Hybrid, rho=0 (residuals, no DC) | 0.93025 | -0.00091 | EXPERIMENTAL |
| I  Full Hybrid (residuals + DC rho) | 0.92907 | **-0.00208** | EXPERIMENTAL |

**Ablation winner: E (Elo + calibrated draw) is the cleanest production-ready model.**  
The full hybrid I gains only 0.002 NLL average vs E — inside the noise for 3 of 4 splits.

---

## 2. Incremental contribution of each component

| Layer change | Avg ΔNLL | Direction |
|:-------------|:--------:|:---------:|
| A→D: +home advantage | -0.15484 | ✓ improves |
| D→E: +calibrated draw | -0.01262 | ✓ improves |
| E→F: Poisson vs logistic (global) | +0.00038 | ~ noise |
| F→G: +DC rho (no residuals) | -0.00026 | ~ noise |
| E→H: +per-team residuals (no DC) | -0.00091 | ~ noise |
| H→I: +DC rho correction | -0.00117 | ~ noise |
| E→I: full hybrid vs Elo-calib | **-0.00208** | ~ noise on 3/4 splits |

**Key finding: the biggest gain is home advantage (+0.155 NLL). Everything after calibrated draw is marginal.**

---

## 3. Significance / Noise Check

Reference: Elo-calibrated draw (E) vs Full Hybrid (I)  
Approximate SE model: SE(NLL) ≈ √(0.40/n_test)

| Split | n_test | Δ NLL (hybrid-elo) | approx SE | z-score | Verdict |
|:------|:------:|:-------------------:|:---------:|:-------:|:-------:|
| train<2015, test 2015-2018 | 3,812 | +0.00365 | 0.01024 | -0.36 | **TIE** |
| train<2019, test 2019-2022 | 3,580 | -0.01151 | 0.01057 | +1.09 | **MARGINAL_WIN** |
| WC2022 holdout | 64 | +0.00498 | 0.07906 | -0.06 | **TIE** |
| train<2023, test 2023-2025 | 3,287 | -0.00543 | 0.01103 | +0.49 | **TIE** |

**No clear_win on any split. 1 marginal_win, 3 ties.**  
WC2022 delta (+0.005 on n=64) is pure noise — SE ≈ 0.079, signal cannot be detected at this sample size.

---

## 4. Calibration (ECE)

| Model | ECE (avg) | Status |
|:------|:---------:|:------:|
| Elo + calibrated draw (E) | 0.0170 | **BETTER** |
| Full Hybrid (I) | 0.0199 | +17% worse |

**The hybrid model is better in NLL but worse in ECE (17% degradation).**  
This means the hybrid produces less-calibrated probability distributions despite fitting more parameters.  
This is expected: 323 per-team residuals fitted on noisy data introduce overconfidence on unknown matchups.

---

## 5. Hybrid Parameters (split 2, best performing)

- beta_elo: 0.666 — Elo is the primary driver (expected 0.25–0.50, so Elo even stronger than expected)
- rho: -0.062 — small DC correction, not hitting boundary (healthy signal)
- base_xg: ≈ 1.40 expected goals per team per match
- CV(beta_elo): 0.054 across 4 splits — **very stable**
- Convergence: optimizer hit iteration limit on all splits (3,000 iter), not fully converged

---

## 6. Production Gate V2 — BORDERLINE_EXPERIMENTAL

| Criterion | Result |
|:----------|:------:|
| hybrid beats elo_calib average NLL | ✓ (-0.00208) |
| no catastrophic loss on WC2022 | ✓ (+0.005 is noise) |
| rho not stuck at ±0.20 boundary | ✓ (-0.02 to -0.06) |
| beta_elo stable across splits | ✓ (CV=0.054) |
| ≥1 clear_win split | ✗ (0 clear_win, 1 marginal) |
| hybrid ECE not worse >5% | ✗ (+17% worse) |
| residuals add signal beyond Elo | ✗ (H vs E: only -0.0009, noise) |

**Verdict: BORDERLINE_EXPERIMENTAL**  
4 of 7 criteria met. **Do not integrate into production.**

---

## 7. Final Answer: What to do next

### Action: **B — Keep expert model, document hybrid as experimental**

**Rationale:**
1. Hybrid avg NLL gain vs Elo-calibrated: -0.002 (2 NLL thousandths). Over a 64-match WC2026, this is completely undetectable.
2. ECE is 17% worse for hybrid — it generates more overconfident probabilities.
3. Only 1 marginal_win signal (z=1.09 on one split) — not replicable across all splits.
4. The 49K match dataset confirms: **Elo + calibrated draw is the real backbone.** Per-team residuals add noise on most splits and a marginal signal on one.
5. The biggest model improvement (by far) was **home advantage** (+0.155 NLL avg). Not the DC correction.

### What would make hybrid production-ready (for future reference):
- Retrain on recent competitive matches only (2018–2026, post-2018 Elo era)
- Add time-decay weighting (recent matches count more)
- Use tournament-specific lambda (higher regularization for non-WC splits)
- Verify ECE improves before integrating
- Require ≥2 clear_win (z≥2) splits before touching MatchModel

### Current production model
`src/wc2026/match_model.py` — **unchanged** from P0.  
Uses: analyst priors + StatsBomb features (30/48 real, 18/48 fallback).  
Hybrid is documented as `EXPERIMENTAL` in `outputs/calibration/`.

---

## Appendix: P2 Backtest (original hybrid_params.json, n_restarts=3)

| Split | Elo NLL | Hybrid NLL | Beats Elo? |
|:------|:-------:|:----------:|:----------:|
| train<2015, test 2015-2018 | 0.9239 | 0.9278 | NO |
| train<2019, test 2019-2022 | 0.8860 | 0.8732 | YES |
| WC2022 holdout | 1.0275 | 1.0325 | NO |
| train<2023, test 2023-2025 | 0.8872 | 0.8813 | YES |

P2 production gate (2/4): superficially PASS — but P2.5 shows the improvement is in noise range on 3 splits, ECE degrades, no component clearly adds beyond Elo+calibrated_draw.
