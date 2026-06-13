# WC2026 Probabilistic Forecast Lab — Short

A live probabilistic forecasting lab for the 2026 World Cup. Multi-provider live data (TheStatsAPI
shotmap xG + odds, Highlightly, API-Football, football-data.org), a Calibrated Elo → Dixon-Coles
Poisson core, and an ML 1X2 ensemble wired into a 100k-run Monte Carlo of the 48-team bracket.

What makes it defensible:
- **Leak-free validation** at match level (ML Brier 0.508 vs 0.529 Elo, held-out 2019–2022) and
  **tournament level** (walk-forward on WC2010/14/18/22, ML retrained per cutoff).
- Evidence over ego: the ML weight was **cut 0.50 → 0.20** because the higher weight over-concentrated
  favorites and hurt the 2018 upset.
- **Uncertainty shown, not hidden:** champion probabilities are P5/P50/P95 intervals, explicitly
  labeled a floor (sampling uncertainty only).
- Reproducible offline, 558 tests, a public model card, and a 20-point self-hostile reviewer audit.

Top of the distribution: Spain ≈19%, Argentina ≈16%, France ≈11% — high entropy is correct for a
48-team field. It's a probability distribution, not a prediction.
