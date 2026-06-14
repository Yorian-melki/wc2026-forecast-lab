# Model Card — WC2026 Probabilistic Forecast Lab

**Version:** publication-grade (2026-06-14) · **Maturity (self-assessed):** 6.93/10 · **Tests:** 571 passing

## Purpose
Produce an auditable probability distribution over the 2026 FIFA World Cup champion (and every
stage), with explicit uncertainty and a documented provenance for every number. It is a
forecasting **lab**, not a single prediction.

## Intended use
- Research / education on probabilistic sports forecasting and calibration.
- A portfolio artifact demonstrating data engineering, validation, and honest uncertainty.
- A baseline to compare against market odds.

## NOT intended for
- Betting or financial decisions (probabilities are not edges; no staking logic).
- Claiming a "predicted winner" — the output is a distribution; the favorite sits near 19%.
- Tournament-level calibrated guarantees — validation is on 4 World Cups (small sample).

## Model components
1. **Core:** Calibrated Elo → Dixon-Coles bivariate Poisson scoreline model.
   `log μ = log_base ± beta_elo·(Elo_diff)/400`, beta_elo = 0.5436 (= 0.988 MLE × 0.55 temperature).
2. **xG live adjustment:** bounded ±8 Elo/match correction from (xG margin − score margin);
   live-conditioning only, never modifies beta_elo.
3. **ML 1X2 ensemble:** multinomial logistic on (Elo diff, neutral), reweights the Dixon-Coles
   W/D/L marginals at **weight 0.20** while preserving scoreline structure. Rollback flag in config.
   A dynamic (gap-decaying) weight mode exists but is not the default.
4. **Monte Carlo:** 100,000 bracket simulations; champion probabilities sum to 1.000.

## Data sources
- **martj42 international results** (49,450 matches, 1872–2025) — Elo, ML training, validation. Offline.
- **TheStatsAPI** — per-shot shotmap xG, bookmaker odds, stats (live).
- **Highlightly / API-Football / football-data.org** — xG / live events / standings (live).
- **OpenFootball** — fallback scores.

## Validation summary
- **Match level (ML):** leak-free held-out 2019–2022, 3,580 matches. ML beats Elo-only on Brier
  (0.508 vs 0.529), NLL (0.867 vs 0.900), ECE (0.008 vs 0.054).
- **Tournament level:** leak-free walk-forward on **WC2010/2014/2018/2022** (Elo + ML retrained
  per cutoff). ML weight 0.20 chosen by a worst-case-regret rule after 0.50 was found to
  over-concentrate favorites (hurt the WC2018 upset).
- **Uncertainty:** beta_elo bootstrap → champion P5/P50/P95 intervals.

## Uncertainty meaning (read this)
The published intervals propagate **beta_elo sampling uncertainty only** — which is *small*
(the 10.5k-match dataset pins beta tightly; ESP ≈ 18.7–19.3%). They are a **floor**, NOT total
forecast uncertainty. They **exclude** the dominant sources: the temperature calibration choice
(0.55), model-structure error, and single-tournament variance. Champion probabilities are not
point-precise; treat ±a few points as the real practical uncertainty.

## Known limitations
- 4-tournament validation sample (all 32-team WCs); no EUROs/Copa yet.
- Structural / temperature uncertainty unquantified.
- xG providers (Highlightly, TheStatsAPI) share an upstream → not independent.
- No injury, suspension, or squad-depth modeling.
- Elo frozen at cutoff (no intra-tournament form re-fit beyond live score conditioning).
- Market odds used as a benchmark only, not integrated.

## Failure modes
- **Upset tournaments:** the ML ensemble mildly favors favorites; an upset champion lowers scores.
- **Provider drift / outage:** live xG/odds can change or break (mitigated by a disagreement system).
- **Name mismatch:** historical validation rejects teams without resolved Elo; WC2026 map is curated.

## Ethical / communication caveats
Outputs are probabilities for research, not predictions and not betting advice. The project avoids
marketing superlatives and overclaiming by policy (enforced by a no-overclaim test). The maturity
score is self-assessed and not externally reviewed.

## What would improve it next
Structural-uncertainty quantification (model-form ensemble + temperature posterior) for honest
wider intervals; a flexible-bracket harness to validate on EUROs/Copa; an independent xG source.
