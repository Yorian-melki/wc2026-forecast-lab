# WC2026 Probabilistic Forecast Lab (public)

A live probabilistic forecasting lab for the 2026 FIFA World Cup. Probability distribution +
uncertainty intervals — not a prediction.

## Stack
- **Data:** martj42 (49,450 matches) · TheStatsAPI (shotmap xG + odds) · Highlightly · API-Football ·
  football-data.org · OpenFootball.
- **Model:** Calibrated Elo → Dixon-Coles Poisson + bounded xG adjustment + ML 1X2 ensemble (weight
  0.20) → 100k Monte Carlo over the 48-team bracket.
- **Validation:** leak-free match-level (Brier 0.508 vs 0.529) and tournament-level walk-forward
  (WC2010/14/18/22). Champion P5/P50/P95 intervals.

## Run it
```bash
pip install -r requirements.txt
PYTHONPATH=src python scripts/rebuild_publication_forecast.py     # smoke
PYTHONPATH=src python -m pytest tests/ -q                          # 558 tests
streamlit run app.py
```
Reproduces offline; no API keys needed for the forecast.

## Honest limits
4 tournaments validated; intervals are a sampling-only floor; xG sources not independent; no injury
modeling; market odds are a benchmark, not an input. Maturity self-assessed 6.4/10.

## Read more
- Model card: `outputs/audit/model_card_public.md`
- Reviewer audit: `outputs/audit/reviewer_attack_audit.md`
- Case study: `outputs/public/portfolio_wc2026_case_study.md`

Statistical model for research. Outputs are probabilities, not predictions. Not betting advice.
