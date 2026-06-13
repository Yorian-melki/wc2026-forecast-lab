# WC2026 Forecast — Model Selection Report

Generated: 2026-06-10 (P3.5 temperature-corrected)

---

## What was tested

Two models were run through 100,000 Monte Carlo simulations of the 48-team WC2026 bracket.

**Expert model** (P0): Uses analyst-assigned ratings (attack, defense, midfield, etc.) plus StatsBomb-derived pressing/shot-quality metrics for 30 of 48 teams.

**Elo-calibrated model** (P3): Uses rolling Elo ratings fitted on 31,975 international matches (martj42, 1872–2026). Poisson expected goals derived directly from Elo difference. No per-team analyst judgment.

A third model — Full Hybrid Elo-Dixon-Coles with per-team attack/defense residuals — was built and tested in P2.5 but **rejected**.

---

## Why the Full Hybrid was rejected

The P2.5 ablation study (9 model variants, 4 temporal splits, 10,500+ competitive matches per split) showed:

| Finding | Detail |
|:--------|:-------|
| Average NLL improvement vs reference | -0.002 (in noise range on 3/4 splits) |
| Expected Calibration Error | **+17% worse** than Elo-calibrated baseline |
| Significance: clear_win splits | **0 of 4** |
| Significance: marginal_win splits | 1 of 4 (z=1.09) |
| P2.5 production gate | **BORDERLINE_EXPERIMENTAL** |

The residual attack/defense parameters — 323 teams × 2 = 646 additional parameters — fitted on noisy historical data add overconfidence rather than signal. The model is marginally better in NLL but measurably worse in calibration.

**Rule applied: promote the most robust model, not the most complex.**

---

## Why Elo-calibrated was promoted

| Property | Elo-calibrated | Expert |
|:---------|:-------------:|:------:|
| Grounded in match data | **49,450 matches** | Analyst judgment |
| ECE (calibration error) | **0.0170 avg** | Not independently measured |
| Verifiable inputs | Public Elo ratings | Private analyst priors |
| Home nation advantage | Preserved (USA/MEX/CAN) | Preserved |
| Penalty/discipline logic | Identical | Reference |
| p(champion) variance | Higher (Elo-concentrated) | Lower (analyst-leveled) |

---

## What each model adds

### Expert model adds:
- Tactical differentiation (pressing, shot quality, set-pieces)
- Real StatsBomb data for 30/48 teams
- Form (temporal + analyst), health, depth, coach quality
- More evenly distributed uncertainty (more draws in top group)

### Elo-calibrated model adds:
- Statistically fitted expected goals (Independent Poisson + DC rho=-0.021)
- Direct connection to 50+ years of match history
- No subjective scaling — every coefficient is data-fitted
- Better ECE: probability distributions are more trustworthy

---

## Champion probability comparison (top 15, by Expert rank)

*Elo-calibrated model: P3.5 temperature-corrected (beta_elo=0.5436, was 0.988). Original beta over-concentrated (top3=66%); corrected to 42%. Internal sanity check: applying β=0.544 to pre-WC2018/WC2022 Elo snapshots gives 35.6–39.2% — internally consistent, not externally validated.*

| Rank | Team | Expert P(champion) | Elo P(champion) | Δ |
|:----:|:-----|:-----------------:|:---------------:|:-:|
| 1 | FRA | 8.19% | 10.03% | +1.84pp |
| 2 | ARG | 7.82% | 14.76% | +6.94pp |
| 3 | ESP | 7.32% | 16.97% | +9.65pp |
| 4 | ENG | 6.65% | 6.71% | +0.06pp |
| 5 | BRA | 6.59% | 5.69% | -0.90pp |
| 6 | POR | 4.93% | 4.81% | -0.12pp |
| 7 | GER | 4.50% | 3.02% | -1.48pp |
| 8 | COL | 3.70% | 4.82% | +1.12pp |
| 9 | BEL | 3.68% | 2.18% | -1.50pp |
| 10 | JPN | 2.94% | 2.37% | -0.57pp |
| 11 | CRO | 2.66% | 2.28% | -0.38pp |
| 12 | MAR | 2.63% | 0.97% | -1.66pp |
| 13 | MEX | 2.58% | 2.55% | -0.03pp |
| 14 | NED | 2.37% | 3.30% | +0.92pp |
| 15 | CAN | 2.34% | 1.03% | -1.31pp |

**Largest divergences explained:**
- **Spain +9.7pp**: Elo 2155, highest in WC2026, reflects Euro 2024 + Nations League wins. Expert model levels top-6 more evenly.
- **Argentina +6.9pp**: Elo 2114 after WC2022 + Copa América 2024. Expert rates France and Brazil comparably.
- **Germany -1.5pp, Belgium -1.5pp**: Expert model boosts for tactical quality; Elo reflects mixed recent results.
- **USA -1.9pp, CAN/MAR -1.3–1.7pp**: Expert model includes home advantage boost; Elo ratings modest for these teams.

---

## What both models share

Both models use:
- Exact 48-team WC2026 bracket mechanics (R32 → R16 → QF → SF → Final)
- Dixon-Coles correction for low-scoring draws
- Penalty win probability (based on specialist and goalkeeper ratings)
- Jet lag factors (European teams playing in North America, UTC-5)
- Host-nation home advantage (USA, MEX, CAN: +8% xG boost)
- 100,000 Monte Carlo simulations
- Conservation law verified: Σ P(champion) = 1.000000

---

## Forecast model vs tournament simulator distinction

A **forecast model** predicts match outcomes. An **Elo-calibrated backbone** is a forecast model: it assigns win/draw/loss probabilities based on statistically-fitted parameters.

A **tournament simulator** applies a match model repeatedly through the bracket. This adds uncertainty from:
- Path dependency (who you meet in the R16/QF)
- Group stage uncertainty (any 3rd-place team can qualify)
- Extra time and penalties

These two are combined here. The champion probability is not a direct forecast — it is the result of 100,000 simulated bracket progressions.

---

## Limitations

1. Elo ratings freeze at the last recorded match. Teams with strong pre-tournament form (training camp wins, recent friendlies) are not captured.
2. The calibrated Elo model ignores tactical asymmetry — a team that defends well against press-heavy opponents looks identical to one that does not.
3. beta_elo originally 0.988 (fitted on competitive matches only) produced over-concentrated probabilities (top3=66%). **P3.5 temperature correction applied: beta_elo=0.544 (×0.55).** Post-correction: top3=42%, top1=17%. Internal consistency check: running the same corrected model on pre-WC2018 and pre-WC2022 Elo snapshots gives top-3 concentrations of 35.6% and 39.2% respectively. This is circular validation (same β, different Elo inputs) — not an external calibration against betting markets or WC outcomes.
4. Both models treat groups as independent. Cross-group bracket path correlations are not modeled.
5. Injuries during the tournament are not tracked in simulation.

---

## Claims allowed / forbidden

### Allowed:
- "49,450 international matches ingested in the rolling Elo engine"
- "Elo-calibrated baseline beat more complex hybrid variants on calibration (ECE -17% for Full Hybrid)"
- "Full Hybrid rejected after P2.5 ablation: BORDERLINE_EXPERIMENTAL gate, ECE degraded 17%"
- "100,000 Monte Carlo tournament simulations per model"
- "Exact 48-team WC2026 bracket mechanics"
- "Conservation law verified: Σ P(champion) = 1"
- "Calibrated on competitive international matches 2010–2025"

### Forbidden:
- "hedge-fund-grade"
- "fully calibrated"
- "AI predicts winner"
- "beats betting markets"
- "production betting model"
- "guaranteed edge"
- "statistically significant improvement over bookmakers"
- "peer-reviewed methodology"

---

## Recommended model for publication

**Expert model** for narrative communication (balanced probabilities, tactical richness, more credible to general audience).

**Elo-calibrated model** for methodological transparency (all claims backed by 49K match dataset, no unverifiable analyst judgment).

Publish both with honest framing of limitations. Neither should be presented as a betting tool.
