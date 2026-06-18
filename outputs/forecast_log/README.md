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

## How to capture
**One command (recommended — evolving capture):**
```bash
PYTHONPATH=src python scripts/daily_forecast_capture.py
```
It refreshes results → re-simulates the calibrated forecast → snapshots it → restores the
tracked runtime files so the working tree stays clean. Degrades gracefully (still snapshots)
if there's no key/network. NO git commit, NO push, NO deploy.

**Snapshot only (static, no refresh):** `scripts/log_forecast_snapshot.py` — freezes whatever
forecast is currently committed; dependency-free; never mutates any input.

## Schedule it (deterministic, no LLM needed) — launchd is installed for you
A launchd agent runs the capture daily — see `~/Library/LaunchAgents/com.wc2026.forecastlog.plist`.
Activate it once (your machine, your call):
```bash
launchctl load -w ~/Library/LaunchAgents/com.wc2026.forecastlog.plist
launchctl unload ~/Library/LaunchAgents/com.wc2026.forecastlog.plist   # to stop
```
A plain OS cron equivalent (daily 14:00 UTC):
```
0 14 * * *  cd ~/FinderProjects/wc2026_june2026 && PYTHONPATH=src .venv/bin/python scripts/daily_forecast_capture.py
```

## Tamper-evidence
Snapshots accumulate locally. Commit them to the public repo in batches (`git add
outputs/forecast_log && git commit -m "forecast log"`) — each snapshot's internal UTC
timestamp plus the public commit date is the dated, scoreable record.
