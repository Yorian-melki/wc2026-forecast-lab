#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m wc2026.cli precompute-pairwise --iterations 1000000 --jobs 8 --batch-size 50000 --seed 20260404 --out outputs/pairwise_summary.csv
