#!/usr/bin/env python3
"""Append-only PRE-MATCH forecast snapshot — the proof artifact.

Captures the CURRENT published champion forecast + match state with a UTC timestamp,
so that AFTER WC2026 the forecast can be scored against the real outcome (calibration
vs reality, sharpening over time, vs bookmakers). This is the only thing whose value
EVAPORATES if not captured while the tournament is live — every unlogged matchday is
lost forever.

Pure standard library. Reads committed data only. NEVER writes to data/wc2026_live.json,
the model, or any forecast input — it only appends a timestamped JSON under
outputs/forecast_log/. Safe to run on a schedule (cron/launchd); see the README there.

Recommended pipeline for a true pre-kickoff capture (run BEFORE the day's first match):
    PYTHONPATH=src python scripts/update_live_data.py        # refresh live results (needs keys)
    PYTHONPATH=src python scripts/run_live_simulation.py      # regenerate the displayed forecast
    PYTHONPATH=src python scripts/log_forecast_snapshot.py    # <-- this script: freeze the proof
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGDIR = ROOT / "outputs" / "forecast_log"
SUMMARY = ROOT / "outputs" / "tournament_run" / "live_summary.csv"
INTERVALS = ROOT / "data" / "live" / "champion_probability_intervals.json"
LIVE = ROOT / "data" / "wc2026_live.json"


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def main() -> int:
    now = datetime.now(timezone.utc)
    snap: dict = {"utc": now.isoformat(), "schema": 1, "model": "calibrated Elo->DC + ML@0.20"}

    if LIVE.exists():
        try:
            live = json.loads(LIVE.read_text())
            snap["n_completed"] = len(live.get("completed_matches", []))
            snap["live_last_updated"] = live.get("last_updated")
        except Exception:
            pass

    champ: dict[str, float] = {}
    if SUMMARY.exists():
        with SUMMARY.open() as f:
            for row in csv.DictReader(f):
                try:
                    champ[row["team"]] = round(float(row["champion_prob"]), 5)
                except (KeyError, ValueError):
                    continue
        snap["source"] = "live_summary.csv"
        snap["source_sha256_16"] = _sha(SUMMARY)
    snap["champion_prob"] = dict(sorted(champ.items(), key=lambda kv: -kv[1]))

    if INTERVALS.exists():
        try:
            iv = json.loads(INTERVALS.read_text())
            snap["intervals_generated_at"] = iv.get("generated_at")
            snap["champion_intervals"] = {
                k: {"low": v.get("low"), "base": v.get("base"), "high": v.get("high")}
                for k, v in list((iv.get("intervals") or {}).items())[:10]
            }
        except Exception:
            pass

    LOGDIR.mkdir(parents=True, exist_ok=True)
    out = LOGDIR / f"snapshot_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(snap, indent=2))
    top3 = list(snap.get("champion_prob", {}).items())[:3]
    print(f"snapshot → outputs/forecast_log/{out.name} · "
          f"n_completed={snap.get('n_completed', '?')} · top3={top3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
