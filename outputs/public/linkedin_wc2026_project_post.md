# LinkedIn post — WC2026 Forecast Lab

I built a probabilistic forecasting lab for the 2026 World Cup. Not a "who wins" prediction — a
probability distribution with documented uncertainty.

What's under the hood:
→ Live multi-provider data: per-shot **shotmap xG** + bookmaker odds (TheStatsAPI), team xG
(Highlightly), live events/lineups (API-Football), standings (football-data.org), with a
cross-provider disagreement check.
→ A Calibrated Elo → Dixon-Coles Poisson model + an ML 1X2 ensemble, run through 100,000 Monte
Carlo simulations of the full 48-team bracket.

The part I'm proud of is the discipline, not the model:
• **Leak-free validation** — the ML model beat the Elo baseline on held-out 2019–2022 data (Brier
0.508 vs 0.529), then was tested at tournament level on four past World Cups with the model retrained
before each one.
• **I cut my own ML weight from 0.50 to 0.20** when the validation showed the higher weight
over-concentrated favorites and would have hurt the 2018 France upset.
• **Uncertainty is shown, not hidden** — champion probabilities are intervals, and I explicitly
label them a floor (they cover parameter sampling, not structural uncertainty).
• Fully reproducible offline, 558 automated tests, and a 20-point audit where I attack my own
project and list what's still weak.

Current distribution: Spain ~19%, Argentina ~16%, France ~11%. In a 48-team field, high entropy is
the correct answer — anyone quoting a confident single winner is overfitting a narrative.

This is what honest quantitative work looks like: measured claims, validation before belief, and
uncertainty you can audit.

#DataScience #Quant #Forecasting #MachineLearning #Football
