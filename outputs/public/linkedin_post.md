# LinkedIn Post — WC2026 Forecast

## Short version (≈ 1,950 characters)

---

I built a World Cup 2026 simulator. Then I rejected the most complex model I built.

Here's what that taught me.

**What I built:**
A Monte Carlo simulator for the 48-team WC2026 bracket — 100,000 independent runs through every group match, R32, quarterfinal, semifinal, and final. The model is calibrated on 49,450 international football results going back to 1872.

**What failed:**

The "smart" version — a full hybrid combining Elo ratings with per-team attack/defense residuals fitted via Dixon-Coles maximum likelihood — degraded calibration quality by 17% versus the simpler baseline. It showed zero statistically significant improvements across 4 temporal holdouts.

646 extra parameters. More noise. Less trust.

I also had to correct a subtler issue: the Elo sensitivity parameter (β) fitted on competitive matches only was 0.988 — nearly double the typical value in mixed datasets. It was producing Spain vs. median team expected goals of 3.15 vs. 0.50. Top-3 champion concentration hit 66%. That's not a model — it's a determinism machine.

After temperature correction (β → 0.544), top-3 drops to 42%. Consistent with WC2018/WC2022 pre-tournament Elo snapshots.

**What survived:**

Elo + calibrated draw rate + Dixon-Coles low-score correction. The simplest model that actually holds up under ablation testing.

**Final probabilities (top 5):**
→ Spain: 17.0%
→ Argentina: 14.8%
→ France: 10.0%
→ England: 6.7%
→ Brazil: 5.7%

In a 48-team tournament, the leader is at 17%. That's the point.

**What I learned:**

Model selection is mostly about what you reject, not what you keep. Complexity without robust out-of-sample validation is just overfitting in a nicer suit.

This is a probabilistic simulator, not a prediction. It won't tell you who wins. It tells you how much uncertainty exists — and that's the honest version.

---

*10,555 competitive matches calibrated. 100,000 simulations run. Full methodology and code available.*

---

## Hashtags (optional)

#MachineLearning #Statistics #Football #WC2026 #DataScience #ModelValidation #MonteCarlo
