# RUNBOOK — WC2026 Forecast Lab

First doc for operating this project. For STATE read `PROJECT_STATE.md`. For AI handoff read
`docs/FUTURE_AGENT_START_HERE.md`.

## Run locally
```bash
cd ~/FinderProjects/wc2026_june2026
PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.port 8512 --server.headless false
```
→ http://localhost:8512  · Live Standings auto-updates every 45s if `API_FOOTBALL_KEY` is set in `.env`.

## Validate
```bash
PYTHONPATH=src .venv/bin/python -m py_compile app.py
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q          # 571 passed
```
AppTest all pages + secret scan: see `docs/FUTURE_AGENT_START_HERE.md`.

## Update live data manually (optional — the app does it automatically)
```bash
PYTHONPATH=src .venv/bin/python scripts/update_live_data.py
```

## Reproduce the forecast (offline, no keys)
```bash
PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py --full
```

## Deploy
- Portfolio: already live on Vercel (separate repo). 
- Live app: `docs/DEPLOY_RENDER.md` (Render, manual). DNS: `docs/DNS_SPACESHIP.md`.

## Detailed docs
`docs/RUN_LOCAL.md` · `docs/RUN_TESTS.md` · `docs/UPDATE_LIVE_DATA.md` · `docs/DEPLOY_RENDER.md`
· `docs/DNS_SPACESHIP.md` · `docs/TROUBLESHOOTING.md`
