#!/usr/bin/env python3
"""Daily EVOLVING-forecast capture (v2): refresh results -> re-simulate -> snapshot proof.

The point: freeze a forecast that actually moves as matches are played, so it can be scored
honestly against reality after WC2026. Best-effort and SAFE — every step is guarded:

  1. refresh  : scripts/update_live_data.py   (pulls fresh results into data/wc2026_live.json)
  2. resim    : scripts/run_live_simulation.py (regenerates the calibrated live forecast)
  3. snapshot : scripts/log_forecast_snapshot.py (append-only proof under outputs/forecast_log/)
  4. restore  : `git restore` the tracked runtime files so the working tree stays CLEAN —
                the append-only snapshot is the only record we keep.

If refresh isn't possible (no key / no network) it degrades gracefully: it still re-simulates
the current state and snapshots it. Pure orchestration: NO git commit, NO push, NO deploy.
Run on a schedule (launchd/cron) — see outputs/forecast_log/README.md.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_venv = ROOT / ".venv" / "bin" / "python"
PY = str(_venv if _venv.exists() else sys.executable)
TRACKED = [
    "data/wc2026_live.json",
    "outputs/tournament_run/live_summary.csv",
    "outputs/tournament_run/live_stage_probs.csv",
    "outputs/tournament_run/live_group_position_probs.csv",
]


def _run(label: str, args: list[str], required: bool = False) -> bool:
    env = {**os.environ, "PYTHONPATH": "src"}
    r = subprocess.run([PY, *args], cwd=ROOT, env=env, capture_output=True, text=True)
    ok = r.returncode == 0
    tail = (r.stdout or "").strip().splitlines()[-1:] if ok else [(r.stderr or r.stdout or "").strip()[-300:]]
    print(f"[{label}] {'ok' if ok else 'FAILED'} :: {' '.join(tail)}")
    if not ok and required:
        sys.exit(1)
    return ok


def main() -> int:
    n = "100000"
    if "--n" in sys.argv:
        n = sys.argv[sys.argv.index("--n") + 1]
    _run("refresh", ["scripts/update_live_data.py"])             # best-effort (needs keys/network)
    _run("resimulate", ["scripts/run_live_simulation.py", "--n", n])  # needs wc2026_live.json
    _run("snapshot", ["scripts/log_forecast_snapshot.py"], required=True)  # the proof artifact
    # Keep the working tree clean — the snapshot is the only thing we persist.
    git = shutil.which("git")
    if git:
        subprocess.run([git, "restore", *TRACKED], cwd=ROOT, capture_output=True)
        print("[restore] tracked runtime files restored (clean tree)")
    else:
        print("[restore] git not found on PATH — skipped (snapshot already written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
