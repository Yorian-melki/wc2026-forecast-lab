# LinkedIn Post — Long Version (≈ 3,200 characters)

---

I built a World Cup 2026 simulator. Then I rejected the most complex model I built.

This is the long version.

---

**The project**

A Monte Carlo simulator for the 48-team WC2026 bracket. Each of 100,000 simulations plays every match — group stage through final — using Poisson-distributed goal scoring calibrated on Elo rating differences. Bracket mechanics are exact: 12 groups, best third-place rules, R32 through Final, extra time, penalties.

Data: 49,450 international football results (martj42 dataset, 1872–2025). Calibration: 10,555 competitive matches, 2010–2025.

---

**P1: Why pure Dixon-Coles MLE failed**

Dixon-Coles is a classic football model — per-team attack/defense parameters, maximum likelihood, low-score correction. I implemented it correctly. It still didn't beat the Elo baseline on holdout NLL.

The reason is sample size. National team data is thin. Most countries play 8–12 competitive matches per year. Fitting per-team parameters on that is regularization in disguise — you're mostly fitting noise.

---

**P2.5: Why the Full Hybrid failed**

The "smart" version combined Elo with per-team residuals (646 parameters) fitted on rolling temporal splits. Ablation across 4 holdout windows showed:

- Expected Calibration Error (ECE): 0.0199 vs 0.0170 for the simpler model — **17% worse**
- Significant improvement on 0 of 4 splits
- Marginal improvement on 1 of 4 (z = 1.09, not enough)
- Per-team residuals showed no consistent signal beyond Elo

The biggest single model improvement in the entire ablation? Home advantage. Not the DC correction. Not the residuals.

Production gate: BORDERLINE_EXPERIMENTAL. Model rejected.

---

**P3.5: The over-concentration bug**

The selected model still had a problem. beta_elo = 0.988 — fitted on competitive-only data — was too high. Competitive matches are more Elo-predictable than the full WC draw (which includes rank-5 vs rank-45 mismatches).

Result: Spain vs. median team → 3.15 vs. 0.50 expected goals. Top-3 champion concentration: 66.4%. That's not a probability distribution, it's three teams and 45 passengers.

Temperature multiplier 0.55 applied: beta_elo → 0.544. Top-3 drops to 41.8%. Pre-tournament Elo simulations for WC2018 and WC2022 teams give 35–39% at the same correction — consistent.

---

**Final probabilities (top 10):**

| Spain | 17.0% |
| Argentina | 14.8% |
| France | 10.0% |
| England | 6.7% |
| Brazil | 5.7% |
| Colombia | 4.8% |
| Portugal | 4.8% |
| Netherlands | 3.3% |
| Ecuador | 3.1% |
| Germany | 3.0% |

Σ = 1.000 (conservation law holds).

---

**What this isn't:**
Not a betting tool. Not a prediction. Not "AI tells you the winner." It's a probability distribution over 48 teams in a 7-round single-elimination bracket, built from match history, not hype.

The honest version of quantitative sports forecasting is mostly about what you can't claim — and being precise about the gap between "likely" and "certain."

---

*Full methodology, ablation results, and code available on request.*

#Statistics #Football #WC2026 #DataScience #ModelSelection #MonteCarlo #QuantitativeResearch
