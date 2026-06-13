#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m wc2026.cli simulate-tournament --iterations 100000 --seed 20260404 --out-dir outputs/tournament_run
