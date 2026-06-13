# Public Claims Checklist — WC2026 Forecast

Use this before any publication, LinkedIn post, or public communication.

---

## ✓ Allowed claims

Check each before use. Source file listed for verification.

| Claim | Source | Status |
|:------|:------:|:------:|
| "I ingested 49,450 international football match records" | `results.csv` row count | ✓ EXACT |
| "I used 10,555 competitive matches for Elo calibration" | `elo_calibrated_params.json → n_train_matches` | ✓ EXACT |
| "I benchmarked simpler and more complex model variants" | `outputs/calibration/ablation_results.csv` | ✓ VERIFIED |
| "I rejected the pure MLE model because it failed holdout validation" | P1 ablation results | ✓ VERIFIED |
| "I rejected the Full Hybrid — ECE degraded 17% (0.0199 vs 0.0170)" | `outputs/calibration/production_gate_v2.json` | ✓ EXACT |
| "Full Hybrid: 0 clear-win splits across 4 temporal holdouts" | `outputs/calibration/significance_report.csv` | ✓ EXACT |
| "I detected and corrected tournament-level over-concentration (top-3: 66% → 42%)" | `outputs/calibration/elo_temperature_ablation.csv` | ✓ EXACT |
| "I ran 100,000 Monte Carlo simulations through the WC2026 bracket" | `simulate_models.py --iterations 100000` | ✓ EXACT |
| "The model outputs probabilities, not certainties" | methodology | ✓ FACTUAL |
| "Exact 48-team WC2026 bracket mechanics" | `src/wc2026/bracket.py` | ✓ VERIFIED |
| "Conservation law verified: Σ P(champion) = 1.000" | `elo_calibrated_summary.csv` | ✓ EXACT |
| "Elo-calibrated baseline beat Full Hybrid on calibration quality" | ECE comparison | ✓ EXACT |

---

## ✗ Forbidden claims

Do NOT use any of these, ever.

| Forbidden claim | Why |
|:---------------|:----|
| "AI predicts the World Cup winner" | outputs are probability distributions |
| "hedge-fund-grade model" | no institutional validation exists |
| "fully calibrated" | temperature correction is heuristic, not peer-validated |
| "beats betting markets" | zero market comparison was made |
| "guaranteed edge" | no edge analysis was performed |
| "production betting model" | explicitly rejected from project scope |
| "sure prediction" or "will win" | probabilistic model, not deterministic |
| "peer-reviewed methodology" | no external review conducted |
| "historical market data confirms" | our historical check used internal simulation, not market data |
| "statistically significant improvement over bookmakers" | no such test performed |

---

## Framing guide

### Model description
✓ "A Poisson tournament simulator calibrated on 10,555 competitive international matches"  
✗ "An AI that predicts football matches"

### Concentration correction
✓ "I detected and corrected a known over-concentration issue in the Elo signal amplification"  
✗ "The model is now perfectly calibrated"

### Historical validation
✓ "Our pre-tournament Elo simulations for WC2018 and WC2022 show similar concentration levels after correction (35–39%)"  
✗ "Validated against betting market data"

### Probabilities
✓ "Spain leads at 17% — a 48-team tournament has inherently high entropy"  
✗ "Spain will win"
