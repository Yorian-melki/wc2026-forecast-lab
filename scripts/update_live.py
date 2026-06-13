"""
Wave 1 — Live tournament update pipeline.

Usage:
    python3 scripts/update_live.py              # fetch + simulate + chart
    python3 scripts/update_live.py --dry-run    # fetch + show state, no sim
    python3 scripts/update_live.py --iterations 50000
    python3 scripts/update_live.py --from-file outputs/live/state_YYYYMMDD_HHMM.json

Output:
    outputs/live/state_YYYYMMDD_HHMM.json       — snapshot of live state
    outputs/live/summary_YYYYMMDD_HHMM.csv      — simulation results
    outputs/wc2026_linkedin_live.png            — updated chart
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from wc2026.live_state import fetch_live_state, load_live_state_from_file, save_live_state
from wc2026.tournament import run_live_tournament_to_disk

LIVE_DIR = ROOT / 'outputs' / 'live'
CHART_SCRIPT = ROOT / 'scripts' / 'generate_chart.py'


def print_state_summary(state) -> None:
    print(f"\n{'='*60}")
    print(f"LIVE STATE — fetched {state.fetched_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Completed matches: {state.n_completed}")
    if state.n_completed:
        print(f"Last result date: {state.last_result_date}")
        print(f"\nRESULTS:")
        for r in state.completed:
            tag = f"[{r.group}]" if r.group else f"[{r.round_name}]"
            suffix = f" ({r.decided_in})" if r.decided_in != '90' else ''
            print(f"  {tag} {r.team1} {r.goals1}–{r.goals2} {r.team2}{suffix}")
    else:
        print("  No completed matches yet.")
    if state.eliminated:
        print(f"\nEliminated (simplified): {sorted(state.eliminated)}")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description='WC2026 live update pipeline')
    parser.add_argument('--iterations', type=int, default=100000)
    parser.add_argument('--seed', type=int, default=20260611)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--from-file', type=str, default=None,
                        help='Load state from saved JSON instead of fetching')
    args = parser.parse_args()

    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M')

    print("Fetching live state from openfootball/worldcup.json...")
    if args.from_file:
        state = load_live_state_from_file(args.from_file)
        print(f"Loaded from file: {args.from_file}")
    else:
        try:
            state = fetch_live_state()
        except Exception as e:
            print(f"ERROR fetching live state: {e}")
            sys.exit(1)

    print_state_summary(state)

    state_path = LIVE_DIR / f'state_{ts}.json'
    save_live_state(state, str(state_path))
    print(f"State saved: {state_path}")

    if args.dry_run:
        print("DRY RUN — skipping simulation.")
        return

    out_dir = LIVE_DIR / f'sim_{ts}'
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running {args.iterations:,} simulations conditioned on {state.n_completed} real results...")
    t0 = time.time()
    artifacts = run_live_tournament_to_disk(
        iterations=args.iterations,
        seed=args.seed,
        out_dir=out_dir,
        live_state=state,
    )
    elapsed = time.time() - t0
    champ_sum = artifacts.summary['champion_prob'].sum()
    print(f"Done in {elapsed:.0f}s | champ sum={champ_sum:.6f}")

    # Also copy to the default output dir so generate_chart.py picks it up
    import shutil
    default_dir = ROOT / 'outputs' / 'tournament_run'
    default_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob('*.csv'):
        shutil.copy(f, default_dir / f.name)
    for f in out_dir.glob('*.json'):
        shutil.copy(f, default_dir / f.name)

    print("\nTop 10 champion probabilities:")
    print(f"{'Rank':<5} {'Team':<6} {'Win%':>7} {'SF%':>7} {'Grp%':>7}")
    print('-' * 35)
    for i, (_, row) in enumerate(artifacts.summary.head(10).iterrows(), 1):
        print(f"{i:<5} {row['team']:<6} {row['champion_prob']*100:>6.2f}%"
              f" {row['sf_prob']*100:>6.1f}% {row['group_survival_prob']*100:>6.0f}%")

    # Regenerate chart
    print("\nRegenerating chart...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("generate_chart", CHART_SCRIPT)
    chart_mod = importlib.util.load_from_spec(spec)
    spec.loader.exec_module(chart_mod)
    df = chart_mod.load_data()
    chart_path = chart_mod.make_chart(df)
    live_chart = ROOT / 'outputs' / 'wc2026_linkedin_live.png'
    import shutil
    shutil.copy(chart_path, live_chart)
    print(f"Chart: {live_chart}")

    print(f"\nSimulation output: {out_dir}")
    print(f"State snapshot: {state_path}")


if __name__ == '__main__':
    main()
