# Final Model Probability Jump Audit

Generated: 2026-06-10  
Status: FINDING — historical reference claim partially misleading in model_selection_report.md

---

## 1. Mathematical explanation of the probability jump

### Why Expert gives FRA 8.2%, ESP 7.3% (nearly equal)

The Expert model uses analyst-assigned ratings (attack, defense, midfield, form, etc.) that are **manually compressed** toward the mean. An analyst rating scale of 1–10 for all 48 teams inherently bounds the maximum spread. The strongest teams might score 8.5/10 while the weakest score 4.0/10 — a ratio of 2.1x in expected goals.

**Key property:** Analyst ratings produce a soft ceiling on dominance. Spain (Elo 2155) and France (Elo 2062) — 93 Elo points apart — end up with nearly identical champion probabilities (7.3% vs 8.2%) because the analyst model partially levels out the historical performance gap.

### Why Elo-calibrated at β=0.988 gives ESP 30%, top-3 = 66%

Parameters: β_orig=0.988, log_base=0.2269.  
Spain (Elo 2155) vs median WC team (Elo ~1850), diff=305:

```
log_μ_ESP  = 0.2269 + 0.988 × (305/400) = 0.2269 + 0.7517 = 0.9786 → μ = 2.66
log_μ_med  = 0.2269 - 0.7517 = −0.5248 → μ = 0.59
xG ratio   = 2.66 / 0.59 = 4.51×
```

Spain vs weakest WC team (BIH, Elo 1595), diff=560:
```
log_μ_ESP  = 0.2269 + 0.988 × (560/400) = 1.609 → μ = 4.99
log_μ_BIH  = 0.2269 − 1.383 = −1.156 → μ = 0.31
P(ESP win 90min) ≈ 93.8%
```

**These are not credible football match probabilities.** No international team wins 94% of their matches. Over 7 tournament rounds, this extreme per-match advantage compounds: 0.77^6 (group avg win rate) ≈ 20% just from the knockout rounds, plus group-stage frequency → ~30% champion.

### Why Elo-calibrated at β=0.544 gives ESP 17%, top-3 = 42%

Spain vs median (diff=305):
```
log_μ_ESP = 0.2269 + 0.5436 × (305/400) = 0.2269 + 0.4145 = 0.6414 → μ = 1.90
log_μ_med = 0.2269 − 0.4145 = −0.1876 → μ = 0.83
xG ratio  = 1.90 / 0.83 = 2.29×  (vs 4.51× at original beta)
```

Spain vs weakest WC team:
```
μ_ESP ≈ 3.60 (clamped), μ_BIH ≈ 0.31, P(ESP win) ≈ 88%  [β=0.544 capped by xg max]
```

**Compounding over 6 knockout rounds:**

| Model | Per-KO match win prob (vs avg) | P(win all 6 KOs) |
|:------|:---:|:---:|
| Expert | ~55% | 2.8% |
| Elo original β=0.988 | ~72% | 13.4% |
| Elo temp β=0.544 | ~62% | 5.7% |

Then multiply by P(emerge from group, ~82–88%) to get champion probability:
- Expert: 0.85 × 2.8% ≈ **2.4%** (close to 7.3% actual — Expert also has group-stage path uncertainty)
- Elo temp: 0.88 × 5.7% ≈ **5.0%** (vs 17% actual — bracket effects and path dependence amplify)

The actual 17% for ESP emerges from bracket mechanics: Spain doesn't always face average opponents — it depends on group draws. The simulation captures this properly.

### Root cause summary

| Source of gap | Expert | Elo-temp | Elo-orig |
|:--------------|:------:|:--------:|:--------:|
| Per-match xG ratio: Spain vs median | ~1.7× | 2.29× | 4.51× |
| Analyst compression | YES (soft ceiling) | No | No |
| Top-team compounding benefit | Low | Moderate | Extreme |
| Champion ESP | 7.3% | 17.0% | ~30% |

---

## 2. xG ratio per team (β=0.988 vs β=0.544 vs median Elo 1850)

| Team | Elo | xG ratio β=0.988 | xG ratio β=0.544 | Expert% | Elo-T% | Δpp |
|:-----|:---:|:-----------------:|:-----------------:|:-------:|:------:|:---:|
| ESP | 2155 | **4.51×** | 2.29× | 7.32% | 16.97% | +9.65 |
| ARG | 2114 | **3.69×** | 2.05× | 7.82% | 14.76% | +6.94 |
| FRA | 2062 | **2.85×** | 1.78× | 8.19% | 10.03% | +1.84 |
| ENG | 2021 | 2.33× | 1.59× | 6.65% | 6.71% | +0.06 |
| BRA | 1991 | 2.01× | 1.47× | 6.59% | 5.69% | −0.90 |
| COL | 1982 | 1.92× | 1.43× | 3.70% | 4.82% | +1.12 |
| POR | 1986 | 1.96× | 1.45× | 4.93% | 4.81% | −0.12 |
| GER | 1932 | 1.50× | 1.25× | 4.50% | 3.02% | −1.48 |
| MAR | 1716 | 0.67× | 0.82× | 2.63% | 0.97% | −1.66 |
| USA | 1773 | 0.82× | 0.91× | 2.18% | 0.33% | −1.85 |

Germany (Elo 1932) gets a negative delta because the Expert model boosts it via analyst tactical rating, while Elo at β=0.544 gives only 1.25× ratio vs median — no particular advantage.

Morocco and USA are penalized heavily by Elo (both have recent Elo below 1800) even though the Expert model gives them above-average probability via tactical/form priors.

---

## 3. CRITICAL: "Historical WC reference 36–39%" — traceability audit

### What the claim is

Several documents state that top-3 concentration of 36–39% is a "historical WC reference" validating our β=0.55 correction.

### What the claim actually is

**Source file:** `outputs/calibration/historical_tournament_concentration.csv`  
**Method:** Pre-WC2018 and pre-WC2022 Elo ratings extracted from rolling Elo engine (martj42 data). Then run through **our WC2026 48-team bracket simulator** with β×0.55.

| Tournament | β_mul | Top-3 from our simulation |
|:-----------|:-----:|:-------------------------:|
| WC2018 Elo snapshot | 0.55 | **35.58%** |
| WC2022 Elo snapshot | 0.55 | **39.20%** |

### What this proves and does NOT prove

**Proves:**
- Our model, when applied to different Elo snapshots, produces similar concentration levels (~36–39%) with the same β=0.55
- The correction is internally self-consistent

**Does NOT prove:**
- That 36–39% is what any external forecaster estimated pre-WC2018 or WC2022
- That actual WC champion concentrations from betting markets are 36–39%
- That β=0.544 is the "correct" temperature (we chose it to get this range, then validated it with the same model — circular)
- Any comparison to academic forecasting literature (FiveThirtyEight, Goldman Sachs, etc.)

### Actual pre-tournament betting market estimates (not in any file)

For reference (NOT from our data):
- WC2018 betting markets: Brazil ~10–12%, Germany ~13–15%, France ~9–11% — top-3 cumulative ~32–38%
- WC2022 betting markets: Brazil ~14–16%, Argentina ~10–12%, France ~11–13% — top-3 cumulative ~35–41%

**These are from memory and not verified in any file. Do NOT use them publicly without a verifiable source.**

### Verdict

The claim "historical WC reference 36–39%" is **misleading** if understood as external data. It should always be framed as:

> "Internal sanity check: applying our corrected model (β=0.544) to pre-WC2018 and pre-WC2022 Elo snapshots yields top-3 concentrations of 35.6% and 39.2% respectively. This is internally consistent but is not an external calibration."

**Two lines in model_selection_report.md contain the misleading framing. Fixed in this audit.**

---

## 4. Concentration comparison — all three models

| Model | Top-1 | Top-3 | Top-5 | Top-10 | Entropy (bits) | Max entropy |
|:------|:-----:|:-----:|:-----:|:------:|:--------------:|:-----------:|
| Expert | 8.19% | 23.33% | 36.56% | 56.30% | 3.440 | 3.871 |
| Elo original (β=0.988) | ~30.5%* | ~67.2%* | ~78.9%* | ~91.2%* | ~2.17* | 3.871 |
| **Elo temp (β=0.544)** | **16.97%** | **41.76%** | **54.16%** | **73.20%** | **2.913** | 3.871 |

*From 15K temperature ablation simulation (aggregate only — per-team probabilities at β=0.988 were not saved).

**Entropy reference:**
- Max entropy (48 teams equally likely): 3.871 bits
- Expert uses 88.8% of available entropy
- Elo-temp uses 75.2% of available entropy
- Elo-orig uses ~56% of available entropy

---

## 5. Brutal assessment

### Was the Expert model too flat?

**YES, probably.** Spain (Elo 2155) has nearly the same champion probability as France (Elo 2062) and Germany (Elo 1932). The gap between Spain and Germany is 223 Elo points — equivalent historically to ~65% win probability in a direct matchup. Yet the Expert assigns them 7.3% vs 4.5% champion probability, only a 1.6× ratio. This is consistent with strong analyst leveling but inconsistent with the Elo signal.

The Expert model puts Brazil (1991) at the same probability as Argentina (2114 Elo, WC2022 champion). Argentina is 123 Elo points ahead of Brazil — a meaningful gap. Expert gives ARG 7.8% and BRA 6.6% (1.2× ratio). The Elo model gives ARG 14.8% and BRA 5.7% (2.6× ratio). The truth is probably between these.

### Was the Elo original too concentrated?

**YES, definitively.** xG ratio of 4.51× between Spain and the median WC team is not football — it's a certainty machine. P(Spain win vs BIH) = 93.8% is off the scale of credible football forecasting. The competitive-only training data caused the optimizer to find a β that makes the Elo signal look maximally predictive in competitive matches, but this over-amplifies when applied to WC draws.

### Is the temperature-corrected Elo better PROVEN or just more PLAUSIBLE?

**More plausible. Not better proven.**

This is the most important finding of this audit. β=0.544 was chosen to bring top-3 to ~42%. The "validation" was running the same model on WC2018/2022 Elo snapshots — which used the same β=0.544 — and getting 35.6% / 39.2%. This is a circular internal consistency check, not an external validation.

**There is no test in this codebase that answers:** "Had we used this model before WC2018, what probability would we have given to the actual winner (France)?" Or more usefully: "What beta_elo best predicts WC champion outcomes when tested on WC2014, WC2018, WC2022?"

That test was not performed. Without it, β=0.544 is a judgment call made by a developer looking at numbers and deciding they "look reasonable."

**This is a known limitation, not a hidden failure.** The model disclosure in MODEL_CARD.md already says "Temperature correction validated internally only, not against external market data." But it should be front-and-center in any publication.

### What should be published?

**Recommendation: C — Expert vs Elo side-by-side, with honest framing.**

Rationale:
- Expert: uses analyst priors that compress probabilities. More "human" but not data-validated.
- Elo-temp: uses historical match data but with a heuristic temperature correction. More "quant" but circularly validated.
- Neither model was externally validated against actual WC outcomes.
- Publishing both honestly is more credible than claiming either is "correct."

**If forced to publish only one:** Elo-temp, with explicit disclosure that β was tuned to produce reasonable-looking numbers, not optimized on out-of-sample WC predictions.

**Do NOT claim Elo-temp is the "final model" without the above caveat.**

---

## 6. Public document safety

| Document | Finding | Action required |
|:---------|:--------|:----------------|
| `model_selection_report.md` line 68 | "historical WC reference: 36%" — misleading | FIXED in this audit |
| `model_selection_report.md` line 126 | "Historical WC backtest confirms" — misleading | FIXED in this audit |
| `MODEL_CARD.md` | Says "Not fitted on external calibration data — validated by internal sanity check" | OK — honest |
| `claims_audit.md` | Correctly flags as internal simulation | OK |
| `technical_summary.md` | Says "Pre-tournament Elo simulations...consistent" | OK — honest framing |
| `README.md` | "Temperature correction validated internally only" | OK |
| `elo_calibration_gate.json` | `historical_top3_reference: 0.36` (hard-coded, no source) | NOTED — not public-facing |

---

## 7. Final answers

**Exact reason for probability jump (Expert → Elo-temp):**
The Expert model compresses probabilities via analyst priors. The Elo model at β=0.544 gives Spain a 2.29× xG ratio vs the median WC team, and this advantage compounds over 6–7 bracket rounds. The jump from 7.3% to 17.0% for Spain is mathematically correct given the β=0.544 parameter — the question is whether β=0.544 is the right value, not whether the math is wrong.

**Exact evidence for top-3=42% being "acceptable":**
- Internal consistency: our model applied to WC2018/WC2022 Elo snapshots gives 35.6–39.2% with same β
- Qualitative: Spain at 17% is plausible given their Elo dominance post-2020; having 3 teams together at ~42% is consistent with typical WC forecast diversity
- What's NOT available: external calibration against actual WC champion probabilities; out-of-sample accuracy test on WC2014/2018/2022

**Is the current publication package safe?**
CONDITIONALLY. Two lines in `model_selection_report.md` used misleading "historical reference" framing — fixed in this audit. After this fix, all public documents correctly label the historical check as internal. The package is safe IF:
1. The chart shows BOTH models (Expert vs Elo-temp) with honest framing
2. The limitation "temperature correction validated internally only" is visible
3. The word "final model" in MODEL_FREEZE.md is understood as "selected for publication, not proven optimal"

**Whether the final chart should show Elo only or Expert vs Elo comparison:**
Expert vs Elo comparison chart (`outputs/public/wc2026_model_comparison_chart.png`) is more honest. Single-model chart (`wc2026_final_forecast_chart.png`) is cleaner but implies a confidence in Elo-temp that is not fully justified. If publishing to a technical audience: show both. If publishing to general audience: show Elo-temp only but lead with the full limitation disclosure.

**ready_to_publish: CONDITIONAL — after reviewing the two fixed lines in model_selection_report.md.**
