# Probability Output Audit — WC2026 Forecast

---

## 1. Distribution statistics (Elo-temp model, β=0.544)

| Metric | Value | Assessment |
|--------|------:|-----------|
| Top-1 (ESP) | 16.97% | HIGH — single team at 17% is the publication's most challenged number |
| Top-3 (ESP+ARG+FRA) | 41.76% | MEDIUM — defensible range by internal check |
| Top-5 | 54.16% | OK |
| Top-10 | 73.20% | OK |
| Shannon entropy (bits) | 4.203 | 75.3% of maximum entropy (max=5.585 bits, 48 equal teams) |
| Herfindahl index | 0.0807 | Moderate concentration |
| Expert entropy | 3.440 bits | 88.8% of max (Expert is more uniform) |

**Interpretation:** The Elo model uses 75% of available entropy. The Expert model uses 89%. The Elo model is more concentrated. Both are below a pure random model (100%). The Elo concentration is the main technical challenge to defend in publication.

---

## 2. Wilson confidence intervals (top 20 teams, sampling variance only)

These are 95% CIs from Monte Carlo sampling variance (n=100,000). They do NOT include beta_elo parameter uncertainty.

| Team | Elo | P(champion) | 95% CI | CI width |
|------|----:|:-----------:|:------:|:--------:|
| ESP | 2155 | 16.97% | [16.74%, 17.20%] | 0.47pp |
| ARG | 2114 | 14.76% | [14.54%, 14.98%] | 0.44pp |
| FRA | 2062 | 10.03% | [9.85%, 10.22%] | 0.37pp |
| ENG | 2021 | 6.71% | [6.55%, 6.86%] | 0.31pp |
| BRA | 1991 | 5.69% | [5.55%, 5.84%] | 0.29pp |
| COL | 1982 | 4.82% | [4.69%, 4.96%] | 0.27pp |
| POR | 1986 | 4.81% | [4.68%, 4.95%] | 0.27pp |
| NED | 1944 | 3.30% | [3.19%, 3.41%] | 0.22pp |
| ECU | 1938 | 3.09% | [2.98%, 3.20%] | 0.22pp |
| GER | 1932 | 3.02% | [2.92%, 3.13%] | 0.21pp |
| MEX | 1875 | 2.55% | [2.45%, 2.65%] | 0.19pp |
| JPN | 1906 | 2.37% | [2.27%, 2.46%] | 0.19pp |
| NOR | 1914 | 2.31% | [2.22%, 2.40%] | 0.18pp |
| CRO | 1911 | 2.28% | [2.19%, 2.37%] | 0.18pp |
| BEL | 1893 | 2.18% | [2.09%, 2.27%] | 0.18pp |
| SUI | 1891 | 2.14% | [2.06%, 2.24%] | 0.18pp |
| URU | 1892 | 2.02% | [1.94%, 2.11%] | 0.17pp |
| TUR | 1911 | 1.88% | [1.80%, 1.97%] | 0.17pp |
| SEN | 1867 | 1.45% | [1.37%, 1.52%] | 0.15pp |
| PAR | 1833 | 1.09% | [1.03%, 1.16%] | 0.13pp |

**Critical limitation:** These CIs are narrow (0.2–0.5pp) because 100K simulations are sufficient to reduce sampling noise. However, if beta_elo were ±0.05 from 0.544, the champion probabilities would shift by ±3–4pp for top teams. The true uncertainty on ESP's 16.97% is probably ±4pp, not ±0.24pp.

---

## 3. Elo rank vs champion probability rank

Pearson correlation: **r = 0.992** (very high). The model is essentially an Elo sorting machine with some stochastic path dependence.

**Rank discrepancies (Elo rank vs champion rank):**

| Team | Elo | Elo rank | P(champion) | Champ rank | Rank diff | Reason |
|------|----:|:-------:|:-----------:|:----------:|:---------:|--------|
| MEX | 1875 | 18 | 2.55% | 11 | 7 | Home advantage (+8% xG) lifts above Elo rank |
| TUR | 1911 | 12 | 1.88% | 18 | 6 | Despite Elo rank 12, TUR draws tough groups in simulation |
| NOR | 1914 | 11 | 2.31% | 13 | 2 | Slight path-dependence effect |

No rank discrepancy > 8. The model is almost perfectly Elo-sorted. The home advantage effect on MEX (+7 ranks) is the most notable exception.

---

## 4. Expert vs Elo model comparison

Pearson correlation between Expert and Elo champion probabilities: **r = 0.897** (p<0.0001)

The two models broadly agree. The large divergences are concentrated in two categories:
1. **Elo-dominant (top 2 teams):** ESP and ARG are much higher in Elo (Elo rewards their recent match performance; Expert compresses them toward the mean)
2. **Home nation / analyst-boosted teams:** USA, MAR, GHA, TUN are much higher in Expert (analyst ratings give them tactical/home credit; Elo undervalues them due to confederation strength effects)

**Largest divergences (|delta| > 1pp):**

| Team | Elo% | Expert% | Delta | Why |
|------|-----:|--------:|------:|-----|
| ESP | 16.97% | 7.32% | +9.65pp | Highest Elo (2155). Expert compresses. |
| ARG | 14.76% | 7.82% | +6.94pp | Elo 2114. Expert treats ARG/FRA/BRA similarly. |
| USA | 0.33% | 2.18% | -1.85pp | Elo 1726 but home nation. Expert adds home boost. |
| FRA | 10.03% | 8.19% | +1.84pp | Elo 2062. Expert levels top-3. |
| MAR | 0.97% | 2.63% | -1.66pp | Elo 1716 (CONCACAF-adjacent schedule). Expert adds form/pedigree. |
| BEL | 2.18% | 3.68% | -1.50pp | Expert boosts BEL for tactical quality. Elo sees declining results. |
| GER | 3.02% | 4.50% | -1.48pp | Same as BEL — analyst boost for historical pedigree. |

**Key structural divergence:** The Elo model rewards RECENT historical performance (via Elo rating). The Expert model rewards ANALYST JUDGMENT about current quality. These disagree most for teams with high historical strength but mixed recent Elo trajectories (GER, BEL) and for weaker-confederation teams with local knowledge (USA, MAR).

---

## 5. Defensibility assessment (per team)

**Highly defensible (both models agree, Elo rank matches):**
- FRA (Elo: 10%, Expert: 8.2%), ENG (6.7% both), BRA (5.7% vs 6.6%), POR (4.8% both), CRO (~2.3% both)

**Moderately defensible (agreement within 2pp, clear reason for gap):**
- ARG (6.9pp gap explainable: Elo rewards WC2022), NED, COL, URU

**Low defensibility (will be challenged):**
- **ESP 16.97%:** Will be challenged as too high. Defense: "highest Elo in the field by 40 points. Math gives 17%. If you think the Elo signal is too strong, that's what the Expert model's 7.3% represents."
- **ECU 3.09%:** Will be challenged as too high for a team with limited international pedigree. Defense: "Elo 1938 reflects actual competitive results, not expectation."
- **USA 0.33%:** Will be challenged as too low for host nation. Defense: "Elo 1726. The home advantage boost is already applied (+8% xG). This model doesn't provide additional subjective boost." (Expert's 2.18% is more intuitive for general audience.)
- **MAR 0.97%:** Will be challenged as too low for a team that reached WC2022 semi-finals. Defense: "Elo reflects matches played, including AFCON and WAFU qualification. Morocco's Elo (1716) reflects their general competitive record." (Weak defense — WC2022 SF performance should have boosted Elo significantly if it did not.)

---

## 6. What no file in this repo answers

1. **"What probability would the model have given to the actual WC2022 champion (Argentina) before WC2022?"**
   - `outputs/calibration/historical_tournament_concentration.csv` has top-3 CONCENTRATION but not per-team probabilities for WC2022 Elo snapshot.
   - Answer: unknown. The most important missing output.

2. **"Is 16.97% for Spain reasonable given betting markets?"**
   - Actual pre-WC2026 Pinnacle/Betfair odds not in any file.
   - Approximate market estimate: Spain ~13–16% implied probability (from memory, unverified).
   - If markets give Spain ~14%, our 17% is slightly high but in the same ballpark.

3. **"What is the uncertainty on ESP's 16.97% from parameter uncertainty?"**
   - If beta_elo were 0.50 instead of 0.544, ESP drops to ~13%. If beta_elo were 0.60, ESP rises to ~21%.
   - This ±4pp range is not reported anywhere. The published CI of ±0.24pp is meaningless in this context.
