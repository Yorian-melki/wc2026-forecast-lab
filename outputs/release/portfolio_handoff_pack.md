# Portfolio Handoff Pack — WC2026

Drop-in content for `yorian-melki.com/projets/wc2026`. No secrets, no inflated claims.

## Project metadata
- **Title:** WC2026 Probabilistic Forecast Lab
- **Slug:** `/projets/wc2026`
- **One-liner:** A live probabilistic World Cup forecast — distribution + uncertainty intervals, validated leak-free.
- **Tags:** quant, data science, forecasting, Monte Carlo, ML validation, xG, APIs
- **Status:** demo-ready (case study); live app pending host
- **Repo:** (GitHub, public) · **Live app:** wc2026.yorian-melki.com (future)
- **Stack:** Python · Streamlit · scikit-learn · numpy/pandas/scipy · 5 sports-data APIs
- **Metrics to show:** 571 tests · 49,450 training matches · 4 World Cups validated · maturity 6.9/10 (self-assessed)

## Short teaser (hero)
> Most World Cup "predictions" are confident guesses. This is a probability distribution you can
> audit: live xG and odds from 5 providers, an ML model validated on four past World Cups
> (retrained before each so it never cheats), 100k Monte Carlo runs, and champion probabilities
> shown as **intervals** — with the limitations stated up front.

## Page body (markdown-ready)
Pulls from `outputs/public/portfolio_wc2026_case_study.md`. Suggested sections:
1. Problem → 2. Data stack → 3. Model stack → 4. Validation (leak-free, match + tournament) →
5. Uncertainty handling → 6. Engineering & reproducibility → 7. What's impressive → 8. Honest limits.

## Image / screenshot checklist (capture before publish)
- [ ] Dashboard overview (champion bars) → `docs/img/dashboard_overview.png`
- [ ] Champion intervals panel (P5/P50/P95) → `docs/img/champion_intervals.png`
- [ ] Data Quality page (provider status + "what this is / is not") → `docs/img/data_quality.png`
- [ ] Tournament walk-forward table → `docs/img/walkforward.png`
- [ ] Final forecast chart (already exists) → `outputs/public/wc2026_final_forecast_chart.png`

## CTA / link structure
- Primary CTA: **"Open the live forecast →"** `wc2026.yorian-melki.com` (or "Coming soon" until live).
- Secondary: **"Read the model card"** → link to `model_card_public.md` rendered page.
- Secondary: **"See the reviewer audit"** → `reviewer_attack_audit.md` (shows intellectual honesty).
- Tertiary: **"Code on GitHub"** → repo link.
- Footer disclaimer: "Probabilities for research, not predictions. Not betting advice."

## Cross-links (future projects)
`/projets/major` · `/projets/black-ice` · `/projets/pro-act-invest` — same card template.
