"""
Étape A — Full data pipeline entry point.

Usage:
    python3 scripts/run_data_pipeline.py                     # full run
    python3 scripts/run_data_pipeline.py --skip-statsbomb    # Elo only (fast)
    python3 scripts/run_data_pipeline.py --backtest          # also run WC2022 backtest
    python3 scripts/run_data_pipeline.py --fast              # cap at 20 SB matches/season

Outputs:
    data/elo_snapshot.csv         — raw Elo for 48 teams
    data/style_metrics.csv        — StatsBomb style metrics
    data/teams.csv                — updated with data-driven form + new columns
    outputs/backtest_wc2022.csv   — backtest detailed results (if --backtest)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="WC2026 Data Pipeline — Étape A")
    parser.add_argument("--skip-statsbomb", action="store_true",
                        help="Skip StatsBomb loading, use cached style_metrics.csv if present")
    parser.add_argument("--backtest", action="store_true",
                        help="Run WC 2022 backtest after updating teams.csv")
    parser.add_argument("--fast", action="store_true",
                        help="Cap StatsBomb at 20 matches/season (for testing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Do not write teams.csv")
    parser.add_argument("--backtest-iters", type=int, default=100_000,
                        help="Iterations for WC2022 backtest (default: 100000)")
    args = parser.parse_args()

    from wc2026.data_pipeline.form_engine import run_form_pipeline

    t0 = time.time()

    max_sb = 20 if args.fast else None
    teams_df = run_form_pipeline(
        skip_statsbomb=args.skip_statsbomb,
        max_sb_matches=max_sb,
        dry_run=args.dry_run,
    )

    print(f"\n[pipeline] Form engine done in {time.time()-t0:.0f}s")

    if args.backtest:
        from wc2026.data_pipeline.backtest import run_wc2022_backtest

        out_dir = ROOT / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        backtest_path = out_dir / "backtest_wc2022.csv"

        print(f"\n[backtest] Starting WC 2022 backtest ({args.backtest_iters:,} iters)...")
        t1 = time.time()
        result = run_wc2022_backtest(
            iterations=args.backtest_iters,
            seed=20220620,
            save_path=backtest_path,
        )
        print(result)
        print(f"[backtest] Done in {time.time()-t1:.0f}s")

    print(f"\n[pipeline] Total elapsed: {time.time()-t0:.0f}s")
    print("[pipeline] Étape A complete.")


if __name__ == "__main__":
    main()
