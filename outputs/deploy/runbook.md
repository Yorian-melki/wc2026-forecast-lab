# Runbook — WC2026 Forecast Lab

## Local
```bash
cd ~/FinderProjects/wc2026_june2026
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m pytest tests/ -q            # expect 558 passed
streamlit run app.py                                  # dashboard at localhost:8501
```

## Reproduce the forecast
```bash
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py          # smoke (<60s)
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py --full    # full (~25 min)
```

## Refresh live data (needs API keys in .env)
```bash
PYTHONPATH=src .venv/bin/python scripts/update_live_data.py
```

## Deploy — live app on Render (recommended)
1. Push repo to GitHub (confirm `.env` is gitignored: `git check-ignore .env`).
2. Render → New Web Service → connect repo.
3. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Environment: add API keys (only if live refresh wanted; otherwise skip — app uses the snapshot).
5. Custom domain: add `wc2026.yorian-melki.com`; Render shows a CNAME target.
6. **User:** at Spaceship DNS, add CNAME `wc2026` → Render's target. (Claude does not change DNS.)

## Deploy — portfolio/case study on Vercel
1. Vercel project for the portfolio repo (apex + www already Vercel-wired).
2. Add `/projets/wc2026` page using `outputs/public/portfolio_wc2026_case_study.md`.

## Rollback
- ML ensemble: set `use_ml_match_model=false` in `data/model_stack_config.json` → Elo-only.
- App: redeploy previous commit on the host.

## Incident: provider outage / xG drift
- Check `data/live/provider_status.json` and `provider_disagreements.json`.
- The forecast still runs offline from the last snapshot; live panels degrade gracefully.
