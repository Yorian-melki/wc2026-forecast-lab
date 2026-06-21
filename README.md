# WC2026 Probabilistic Forecast Lab

A live probabilistic forecasting lab for the 2026 FIFA World Cup — Elo→Dixon-Coles Poisson,
an ML ensemble, multi-provider live xG/odds, tournament-level validation, and **uncertainty
intervals**.

**Not a prediction. A probability distribution with documented uncertainty.**

---

## What it is

- **Core model:** Calibrated Elo → Dixon-Coles bivariate Poisson scoreline model (β_elo = 0.544).
- **ML ensemble:** logistic 1X2 model reweights the Dixon-Coles W/D/L marginals at weight **0.20**
  (chosen by tournament-level walk-forward, not guesswork), preserving scoreline structure. Rollback flag.
- **xG live adjustment:** bounded ±8 Elo/match, live-conditioning only.
- **Live data:** TheStatsAPI (per-shot shotmap xG + odds), Highlightly (xG), API-Football (live/events/
  lineups), football-data.org (standings/scorers), with a provider-disagreement check.
- **Uncertainty:** champion probabilities are reported as **P5/P50/P95 intervals** (beta bootstrap).
- **Conservation verified:** Σ P(champion) = 1.000 across the 48 teams in every run.

## What it is not

- Not a predicted winner (the favorite sits near 19% — high entropy is correct in a 48-team field).
- Not a betting tool, not financial advice.
- Not a tournament-level *calibrated* forecaster — validation is on 4 World Cups (small sample).

---

## Validation (leak-free)

- **Match level:** ML beats Elo-only on held-out 2019–2022 (3,580 matches): Brier 0.508 vs 0.529,
  NLL 0.867 vs 0.900, ECE 0.008 vs 0.054.
- **Tournament level:** walk-forward on **WC2010 / 2014 / 2018 / 2022** with Elo + ML retrained per
  cutoff. ML weight cut from 0.50 → 0.20 after 0.50 was found to over-concentrate favorites.
- **Uncertainty:** intervals propagate beta *sampling* uncertainty (small — a documented **floor**,
  not total uncertainty).

## Current top 10 (champion, ML ensemble @0.20, 100k sims)

| # | Team | P(champion) | Interval (P5–P95) |
|---|------|---|---|
| 1 | Spain | 19.0% | 18.7–19.3% |
| 2 | Argentina | 15.7% | 15.7–16.1% |
| 3 | France | 10.8% | 10.4–10.9% |
| 4 | England | 7.1% | 7.0–7.1% |
| 5 | Brazil | 5.6% | — |
| 6 | Portugal | 4.9% | — |
| 7 | Colombia | 4.7% | — |
| 8 | Netherlands | 3.2% | — |

---

## Reproduce (offline — no API keys needed)

```bash
pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py          # smoke (<60s)
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py --full    # full (~25 min)
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q                                # 574 passed
streamlit run app.py
```

The forecast and all validation reproduce **fully offline** from committed data. API keys (see
`.env.example`) are only needed to refresh live provider data.

---

## Screenshots

<!-- TODO before publishing: add real screenshots -->
- `docs/img/dashboard_overview.png` — main forecast view _(placeholder)_
- `docs/img/champion_intervals.png` — P5/P50/P95 intervals _(placeholder)_
- `docs/img/data_quality.png` — provider status + reviewer caveats _(placeholder)_

## Honest limitations

- Validation sample = 4 World Cups (32-team); no EUROs/Copa yet.
- Intervals capture beta sampling uncertainty only; structural + temperature uncertainty unmodeled.
- xG providers share an upstream (not independent); no injury/squad modeling.
- Market odds used as a benchmark, not integrated.

Full detail: `outputs/audit/model_card_public.md` · reviewer audit: `outputs/audit/reviewer_attack_audit.md`.

## Data credits
martj42/international-football-results · StatsBomb Open Data · TheStatsAPI · Highlightly ·
API-Football · football-data.org · OpenFootball.

## Disclaimer
Statistical model for research and learning. Outputs are probabilities, not predictions. Not a
betting tool. No financial advice. Maturity self-assessed (6.4/10), not externally reviewed.
