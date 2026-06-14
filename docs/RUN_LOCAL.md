# Run Local
```bash
cd ~/FinderProjects/wc2026_june2026
source .venv/bin/activate    # or use .venv/bin/python directly
PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.port 8512 --server.headless false
```
- URL: http://localhost:8512
- Live auto-update requires `API_FOOTBALL_KEY` in `.env` (see `.env.example`). Without it → static snapshot.
- Refresh cadence: `LIVE_REFRESH_SECONDS` (default 45).
- If port busy: `pkill -f "streamlit run app.py"` then relaunch (try 8513).
