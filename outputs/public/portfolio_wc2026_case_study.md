# WC2026 Probabilistic Forecast Lab — Case Study

> A live probabilistic forecasting lab for the 2026 World Cup: multi-provider live data, real xG
> and shotmaps, bookmaker odds, an ML model validated leak-free, tournament-level Monte Carlo,
> and uncertainty intervals — built to survive a hostile review, not to look impressive.

## The problem
World Cup forecasts are usually punditry or black-box ensembles with confident-sounding numbers
and no traceability. I wanted the opposite: a forecast where **every number traces to a source**,
**every model choice is validated or rejected on evidence**, and **uncertainty is shown, not hidden**.

## Data stack
- **Historical:** martj42 international results — 49,450 matches (1872–2025) for rolling Elo, ML
  training, and tournament backtests.
- **Live (multi-provider):** TheStatsAPI (per-shot **shotmap xG** with x/y coordinates + bookmaker
  **odds**), Highlightly (team xG), API-Football (live score/events/lineups), football-data.org
  (standings/scorers). A **provider-disagreement system** cross-checks scores across sources.
- An honest finding baked in: Highlightly and TheStatsAPI xG are *identical* on 3/4 matches → they
  share an upstream, so I labeled them **not independent** instead of pretending to cross-validate.

## Model stack
- **Calibrated Elo → Dixon-Coles Poisson** scoreline model (survived an ablation that *rejected* a
  more complex hybrid on calibration grounds).
- **Bounded xG live adjustment** (±8 Elo/match) — conditioning, not retraining.
- **ML 1X2 ensemble:** a logistic model reweights the Dixon-Coles W/D/L marginals while preserving
  the scoreline distribution (so group tiebreakers and knockout penalties stay intact).
- **100,000-run Monte Carlo** over the exact 48-team bracket; champion probabilities sum to 1.000.

## Validation (the part that matters)
- **Match level, leak-free:** trained ≤2018, tested 2019–2022 (3,580 matches). ML beat the Elo
  baseline on Brier (0.508 vs 0.529), log-loss (0.867 vs 0.900), and calibration/ECE (0.008 vs 0.054).
- **Tournament level, walk-forward:** WC2010/2014/2018/2022, with the ML model **retrained per
  cutoff** so it never sees the tournament it's scored on. This surfaced the key result: a 0.50 ML
  weight **over-concentrated favorites** and hurt the 2018 upset, so I cut the weight to **0.20** by
  a worst-case-regret rule. I built a dynamic (gap-decaying) weight too — it halves tail regret but
  the aggregate gain is within noise, so I kept it as an option, not the default.

## Uncertainty handling
Champion probabilities are reported as **P5/P50/P95 intervals**, from a bootstrap of the Elo
temperature parameter. The honest punchline: that sampling uncertainty is *small* (10.5k matches
pin the parameter), so the intervals are narrow — and I label them a **floor**, explicitly
excluding the larger structural uncertainty. The lab refuses to make the forecast look more precise
than the evidence supports.

## Engineering
- Fully **reproducible offline** from committed data (one command; no API keys needed for the
  forecast). 558 automated tests. A no-overclaim test fails the build on banned marketing words.
- Auditable: model card, data lineage map, and a 20-point **hostile reviewer audit** that lists the
  project's own weaknesses with severity and remaining gaps.

## What's impressive
A solo, end-to-end probabilistic pipeline: live multi-source ingestion → real xG/shotmap/odds →
a model validated leak-free at *both* match and tournament level → Monte Carlo → uncertainty
intervals → an auditable, reproducible, deployment-ready lab.

## What remains limited (stated plainly)
Only 4 tournaments validated; intervals cover parameter sampling, not structural uncertainty; xG
sources aren't independent; no injury modeling; market odds are a benchmark, not an input. Maturity
is self-assessed at 6.4/10.

## Why it matters / what it says about my profile
This is the discipline a quant/data role actually requires: not a flashy model, but **measured
claims, leak-free validation, evidence-driven decisions (including rejecting my own more-complex
model), honest uncertainty, and reproducibility under review.** It is a forecasting lab, not a
dashboard.
