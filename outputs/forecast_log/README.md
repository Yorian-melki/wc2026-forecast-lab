# Forecast log — the pre-match proof artifact

Each `snapshot_<UTC>.json` here freezes the **published champion forecast** at a moment in
time, with a UTC timestamp and the source-file SHA256. Committed to git, the commit history
makes the timestamps tamper-evident.

**Why this exists.** A forecast is only credible if it was recorded *before* the outcome.
These snapshots are the record. After WC2026 they let you score the model honestly:

- How much probability did the *eventual champion* carry at each date? (calibration / sharpening)
- Did the live-conditioned forecast move sensibly as results came in?
- Compared to bookmaker closing odds (if also logged), where did the model win or lose?

This replaces hand-wavy skill claims with a measured, dated track record.

## How to capture (run before the day's first kickoff)
```bash
PYTHONPATH=src python scripts/update_live_data.py        # refresh results (needs API keys)
PYTHONPATH=src python scripts/run_live_simulation.py      # regenerate the displayed forecast
PYTHONPATH=src python scripts/log_forecast_snapshot.py    # freeze the proof
```
The logger alone (last line) snapshots whatever forecast is currently committed — safe and
dependency-free. It never mutates `data/wc2026_live.json` or any model input.

## Schedule it (deterministic, no LLM needed) — example launchd/cron
Daily at 14:00 UTC:
```
0 14 * * *  cd ~/FinderProjects/wc2026_june2026 && PYTHONPATH=src .venv/bin/python scripts/log_forecast_snapshot.py
```
A plain OS cron is the robust, free, survives-everything way to run this — it does not need
an AI agent.
