from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from .bracket import export_all_third_place_mappings
from .data_loader import load_config, load_groups, load_teams, validate_data
from .match_model import MatchModel
from .tournament import run_tournament_to_disk
from .utils import ensure_dir


def _pairwise_worker(args: tuple[str, str, int, int, int]):
    team_a_code, team_b_code, iterations, seed, batch_size = args
    teams = load_teams()
    config = load_config()
    model = MatchModel(config)
    result = model.simulate_pairwise_monte_carlo(
        teams[team_a_code],
        teams[team_b_code],
        iterations=iterations,
        seed=seed,
        batch_size=batch_size,
    )
    return result


def cmd_validate_data(_: argparse.Namespace) -> None:
    validate_data()
    print('data validation passed')


def cmd_export_third_place_map(args: argparse.Namespace) -> None:
    export_all_third_place_mappings(args.out)
    print(f'exported 495 generated mappings to {args.out}')


def cmd_precompute_pairwise(args: argparse.Namespace) -> None:
    validate_data()
    teams = sorted(load_teams().keys())
    combos = list(itertools.combinations(teams, 2))
    jobs = max(1, int(args.jobs))
    batch_size = int(args.batch_size)
    iterations = int(args.iterations)
    seed = int(args.seed)
    rows = []
    if jobs == 1:
        for idx, (a, b) in enumerate(combos):
            rows.append(_pairwise_worker((a, b, iterations, seed + idx, batch_size)))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futures = {
                ex.submit(_pairwise_worker, (a, b, iterations, seed + idx, batch_size)): (a, b)
                for idx, (a, b) in enumerate(combos)
            }
            for fut in as_completed(futures):
                rows.append(fut.result())
    df = pd.DataFrame(rows).sort_values(['team_a', 'team_b']).reset_index(drop=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f'wrote {len(df)} pairwise rows to {out}')


def cmd_simulate_tournament(args: argparse.Namespace) -> None:
    validate_data()
    artifacts = run_tournament_to_disk(iterations=int(args.iterations), seed=int(args.seed), out_dir=args.out_dir)
    print(artifacts.summary.head(10).to_string(index=False))
    print(f'outputs written to {args.out_dir}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='wc2026', description='Localhost Monte Carlo World Cup 2026 simulator')
    sub = parser.add_subparsers(dest='command', required=True)

    p_validate = sub.add_parser('validate-data', help='Validate shipped data files')
    p_validate.set_defaults(func=cmd_validate_data)

    p_thirds = sub.add_parser('export-third-place-map', help='Export generated 495 third-place mappings')
    p_thirds.add_argument('--out', required=True, help='Output CSV path')
    p_thirds.set_defaults(func=cmd_export_third_place_map)

    p_pair = sub.add_parser('precompute-pairwise', help='Run pairwise Monte Carlo for all 1128 unique matchups')
    p_pair.add_argument('--iterations', type=int, default=1_000_000)
    p_pair.add_argument('--jobs', type=int, default=1)
    p_pair.add_argument('--seed', type=int, default=20260404)
    p_pair.add_argument('--batch-size', type=int, default=50_000)
    p_pair.add_argument('--out', required=True)
    p_pair.set_defaults(func=cmd_precompute_pairwise)

    p_tour = sub.add_parser('simulate-tournament', help='Run full tournament Monte Carlo')
    p_tour.add_argument('--iterations', type=int, default=100_000)
    p_tour.add_argument('--seed', type=int, default=20260404)
    p_tour.add_argument('--out-dir', required=True)
    p_tour.set_defaults(func=cmd_simulate_tournament)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
