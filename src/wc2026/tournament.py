from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .best_thirds import rank_best_thirds
from .bracket import build_final, build_quarterfinals, build_round_of_16, build_round_of_32, build_semifinals
from .constants import GROUP_ORDER
from .data_loader import Team, load_config, load_groups, load_teams
from .group_rules import simulate_group, simulate_group_conditioned
from .match_model import MatchModel
from .confidence import add_confidence_intervals
from .utils import ensure_dir, write_json


@dataclass
class TournamentArtifacts:
    summary: pd.DataFrame
    group_positions: pd.DataFrame
    stage_probs: pd.DataFrame
    top_paths: dict


class TournamentSimulator:
    def __init__(self, teams: Dict[str, Team], groups: Dict[str, List[str]],
                 config: dict | None = None, model=None):
        self.teams = teams
        self.groups = groups
        self.config = config or load_config()
        self.model = model if model is not None else MatchModel(self.config)

    def simulate_once(self, rng: np.random.Generator) -> dict:
        group_tables = {}
        group_orders = {}
        placements = {}
        for group, codes in self.groups.items():
            table, _, order = simulate_group(group, codes, self.teams, self.model, rng)
            group_tables[group] = table
            group_orders[group] = order
            placements[group] = {'1': order[0], '2': order[1], '3': order[2], '4': order[3]}

        ranked_thirds = rank_best_thirds(group_tables, group_orders, self.teams)
        best_thirds = ranked_thirds[:8]
        best_third_groups = [x.group for x in best_thirds]

        r32 = build_round_of_32(placements, best_third_groups)
        r32_winners = {}
        r32_losers = {}
        for match_no, (a, b) in r32.items():
            result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
            r32_winners[match_no] = result.winner
            r32_losers[match_no] = result.loser

        r16 = build_round_of_16(r32_winners)
        r16_winners = {}
        r16_losers = {}
        for match_no, (a, b) in r16.items():
            result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
            r16_winners[match_no] = result.winner
            r16_losers[match_no] = result.loser

        qf = build_quarterfinals(r16_winners)
        qf_winners = {}
        qf_losers = {}
        for match_no, (a, b) in qf.items():
            result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
            qf_winners[match_no] = result.winner
            qf_losers[match_no] = result.loser

        sf = build_semifinals(qf_winners)
        sf_winners = {}
        sf_losers = {}
        for match_no, (a, b) in sf.items():
            result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
            sf_winners[match_no] = result.winner
            sf_losers[match_no] = result.loser

        final = build_final(sf_winners)
        final_match = next(iter(final.items()))
        _, (a, b) = final_match
        final_result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
        champion = final_result.winner
        runner_up = final_result.loser

        third_place_match = self.model.simulate_knockout_match(self.teams[sf_losers['M101']], self.teams[sf_losers['M102']], rng)
        third_place = third_place_match.winner
        fourth_place = third_place_match.loser

        return {
            'placements': placements,
            'best_thirds': best_thirds,
            'best_third_groups': best_third_groups,
            'r32': r32,
            'r32_winners': r32_winners,
            'r16_winners': r16_winners,
            'qf_winners': qf_winners,
            'sf_winners': sf_winners,
            'champion': champion,
            'runner_up': runner_up,
            'third_place': third_place,
            'fourth_place': fourth_place,
        }

    def simulate_many_live(self, iterations: int, seed: int, live_state=None) -> TournamentArtifacts:
        """simulate_many conditioned on live_state real results (group stage)."""
        has_live_data = (
            live_state is not None
            and (live_state.n_completed > 0 or bool(live_state.group_results))
        )
        if not has_live_data:
            return self.simulate_many(iterations, seed)

        rng = np.random.default_rng(np.random.PCG64DXSM(seed))
        teams = list(self.teams.keys())
        stage_counts = {team: Counter() for team in teams}
        position_counts = {team: Counter() for team in teams}
        path_counts = Counter()

        for _ in range(iterations):
            group_tables = {}
            group_orders = {}
            placements = {}
            for group, codes in self.groups.items():
                fixed = live_state.group_results.get(group, [])
                if fixed:
                    table, _, order = simulate_group_conditioned(
                        group, codes, self.teams, self.model, rng, fixed
                    )
                else:
                    table, _, order = simulate_group(group, codes, self.teams, self.model, rng)
                group_tables[group] = table
                group_orders[group] = order
                placements[group] = {'1': order[0], '2': order[1], '3': order[2], '4': order[3]}

            ranked_thirds = rank_best_thirds(group_tables, group_orders, self.teams)
            best_thirds = ranked_thirds[:8]
            best_third_groups = [x.group for x in best_thirds]

            r32 = build_round_of_32(placements, best_third_groups)
            r32_winners = {}
            r32_losers = {}
            for match_no, (a, b) in r32.items():
                result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
                r32_winners[match_no] = result.winner
                r32_losers[match_no] = result.loser

            r16 = build_round_of_16(r32_winners)
            r16_winners = {}
            r16_losers = {}
            for match_no, (a, b) in r16.items():
                result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
                r16_winners[match_no] = result.winner
                r16_losers[match_no] = result.loser

            qf = build_quarterfinals(r16_winners)
            qf_winners = {}
            qf_losers = {}
            for match_no, (a, b) in qf.items():
                result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
                qf_winners[match_no] = result.winner
                qf_losers[match_no] = result.loser

            sf = build_semifinals(qf_winners)
            sf_winners = {}
            sf_losers = {}
            for match_no, (a, b) in sf.items():
                result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
                sf_winners[match_no] = result.winner
                sf_losers[match_no] = result.loser

            final = build_final(sf_winners)
            _, (a, b) = next(iter(final.items()))
            final_result = self.model.simulate_knockout_match(self.teams[a], self.teams[b], rng)
            champion = final_result.winner
            runner_up = final_result.loser

            third_match = self.model.simulate_knockout_match(
                self.teams[sf_losers['M101']], self.teams[sf_losers['M102']], rng
            )

            run = {
                'placements': placements, 'best_thirds': best_thirds,
                'best_third_groups': best_third_groups,
                'r32_winners': r32_winners, 'r16_winners': r16_winners,
                'qf_winners': qf_winners, 'sf_winners': sf_winners,
                'champion': champion, 'runner_up': runner_up,
                'third_place': third_match.winner, 'fourth_place': third_match.loser,
            }

            for group, pos_map in placements.items():
                for pos, team in pos_map.items():
                    position_counts[team][f'group_{pos}'] += 1
            for rec in run['best_thirds']:
                stage_counts[rec.code]['best_third_selected'] += 1
            for team in teams:
                stage_counts[team]['group_survived'] += int(
                    any(placements[g]['1'] == team or placements[g]['2'] == team or
                        (placements[g]['3'] == team and g in run['best_third_groups'])
                        for g in self.groups)
                )
            for winner in run['r32_winners'].values():
                stage_counts[winner]['r16'] += 1
            for winner in run['r16_winners'].values():
                stage_counts[winner]['qf'] += 1
            for winner in run['qf_winners'].values():
                stage_counts[winner]['sf'] += 1
            for winner in run['sf_winners'].values():
                stage_counts[winner]['final'] += 1
            stage_counts[run['champion']]['champion'] += 1
            stage_counts[run['runner_up']]['runner_up'] += 1
            stage_counts[run['third_place']]['third_place'] += 1
            stage_counts[run['fourth_place']]['fourth_place'] += 1
            path_counts[' > '.join(run['best_third_groups'])] += 1

        summary_rows = []
        group_position_rows = []
        stage_rows = []
        for team in teams:
            summary_rows.append({
                'team': team,
                'group_survival_prob': stage_counts[team]['group_survived'] / iterations,
                'r16_prob': stage_counts[team]['r16'] / iterations,
                'qf_prob': stage_counts[team]['qf'] / iterations,
                'sf_prob': stage_counts[team]['sf'] / iterations,
                'final_prob': stage_counts[team]['final'] / iterations,
                'champion_prob': stage_counts[team]['champion'] / iterations,
                'runner_up_prob': stage_counts[team]['runner_up'] / iterations,
                'third_place_prob': stage_counts[team]['third_place'] / iterations,
                'fourth_place_prob': stage_counts[team]['fourth_place'] / iterations,
            })
            for pos_key in ['group_1', 'group_2', 'group_3', 'group_4']:
                group_position_rows.append({
                    'team': team, 'position': pos_key,
                    'probability': position_counts[team][pos_key] / iterations,
                })
            for stage in ['group_survived', 'r16', 'qf', 'sf', 'final', 'champion']:
                stage_rows.append({'team': team, 'stage': stage,
                                   'probability': stage_counts[team][stage] / iterations})

        summary = pd.DataFrame(summary_rows).sort_values(
            ['champion_prob', 'final_prob', 'sf_prob'], ascending=False
        ).reset_index(drop=True)
        return TournamentArtifacts(
            summary=summary,
            group_positions=pd.DataFrame(group_position_rows),
            stage_probs=pd.DataFrame(stage_rows),
            top_paths={
                'iterations': iterations,
                'top_best_third_group_sets': [
                    {'best_third_groups': k, 'count': c, 'probability': c / iterations}
                    for k, c in path_counts.most_common(int(self.config.get('top_path_count', 20)))
                ]
            }
        )

    def simulate_many(self, iterations: int, seed: int) -> TournamentArtifacts:
        rng = np.random.default_rng(np.random.PCG64DXSM(seed))
        teams = list(self.teams.keys())

        stage_counts = {team: Counter() for team in teams}
        position_counts = {team: Counter() for team in teams}
        path_counts = Counter()

        for _ in range(iterations):
            run = self.simulate_once(rng)
            placements = run['placements']
            for group, pos_map in placements.items():
                for pos, team in pos_map.items():
                    position_counts[team][f'group_{pos}'] += 1
            for rec in run['best_thirds']:
                stage_counts[rec.code]['best_third_selected'] += 1
            for team in teams:
                stage_counts[team]['group_survived'] += int(
                    any(placements[g]['1'] == team or placements[g]['2'] == team or placements[g]['3'] == team and g in run['best_third_groups'] for g in self.groups)
                )
            for winner in run['r32_winners'].values():
                stage_counts[winner]['r16'] += 1
            for winner in run['r16_winners'].values():
                stage_counts[winner]['qf'] += 1
            for winner in run['qf_winners'].values():
                stage_counts[winner]['sf'] += 1
            for winner in run['sf_winners'].values():
                stage_counts[winner]['final'] += 1
            stage_counts[run['champion']]['champion'] += 1
            stage_counts[run['runner_up']]['runner_up'] += 1
            stage_counts[run['third_place']]['third_place'] += 1
            stage_counts[run['fourth_place']]['fourth_place'] += 1

            path_key = ' > '.join(run['best_third_groups'])
            path_counts[path_key] += 1

        summary_rows = []
        group_position_rows = []
        stage_rows = []
        for team in teams:
            summary_rows.append({
                'team': team,
                'group_survival_prob': stage_counts[team]['group_survived'] / iterations,
                'r16_prob': stage_counts[team]['r16'] / iterations,
                'qf_prob': stage_counts[team]['qf'] / iterations,
                'sf_prob': stage_counts[team]['sf'] / iterations,
                'final_prob': stage_counts[team]['final'] / iterations,
                'champion_prob': stage_counts[team]['champion'] / iterations,
                'runner_up_prob': stage_counts[team]['runner_up'] / iterations,
                'third_place_prob': stage_counts[team]['third_place'] / iterations,
                'fourth_place_prob': stage_counts[team]['fourth_place'] / iterations,
            })
            for pos_key in ['group_1', 'group_2', 'group_3', 'group_4']:
                group_position_rows.append({
                    'team': team,
                    'position': pos_key,
                    'probability': position_counts[team][pos_key] / iterations,
                })
            for stage in ['group_survived', 'r16', 'qf', 'sf', 'final', 'champion']:
                stage_rows.append({'team': team, 'stage': stage, 'probability': stage_counts[team][stage] / iterations})

        summary = pd.DataFrame(summary_rows).sort_values(['champion_prob', 'final_prob', 'sf_prob'], ascending=False).reset_index(drop=True)
        group_positions = pd.DataFrame(group_position_rows)
        stage_probs = pd.DataFrame(stage_rows)
        top_paths = {
            'iterations': iterations,
            'top_best_third_group_sets': [
                {'best_third_groups': key, 'count': count, 'probability': count / iterations}
                for key, count in path_counts.most_common(int(self.config.get('top_path_count', 20)))
            ]
        }
        return TournamentArtifacts(summary=summary, group_positions=group_positions, stage_probs=stage_probs, top_paths=top_paths)


def run_live_tournament_to_disk(
    iterations: int,
    seed: int,
    out_dir: str | Path,
    live_state=None,  # LiveState | None — avoids circular import
) -> TournamentArtifacts:
    """Run simulation conditioned on real match results in live_state."""
    teams = load_teams()
    groups = load_groups()
    config = load_config()
    simulator = TournamentSimulator(teams=teams, groups=groups, config=config)
    artifacts = simulator.simulate_many_live(
        iterations=iterations, seed=seed, live_state=live_state
    )
    out_dir = ensure_dir(out_dir)
    summary_with_ci = add_confidence_intervals(artifacts.summary, iterations)
    summary_with_ci.to_csv(out_dir / 'summary.csv', index=False)
    artifacts.group_positions.to_csv(out_dir / 'group_position_probs.csv', index=False)
    artifacts.stage_probs.to_csv(out_dir / 'stage_probs.csv', index=False)
    write_json(out_dir / 'top_paths.json', artifacts.top_paths)
    write_json(out_dir / 'summary.json', json.loads(summary_with_ci.to_json(orient='records')))
    artifacts.summary = summary_with_ci
    return artifacts


def run_tournament_to_disk(iterations: int, seed: int, out_dir: str | Path) -> TournamentArtifacts:
    teams = load_teams()
    groups = load_groups()
    config = load_config()
    simulator = TournamentSimulator(teams=teams, groups=groups, config=config)
    artifacts = simulator.simulate_many(iterations=iterations, seed=seed)
    out_dir = ensure_dir(out_dir)
    summary_with_ci = add_confidence_intervals(artifacts.summary, iterations)
    summary_with_ci.to_csv(out_dir / 'summary.csv', index=False)
    artifacts.group_positions.to_csv(out_dir / 'group_position_probs.csv', index=False)
    artifacts.stage_probs.to_csv(out_dir / 'stage_probs.csv', index=False)
    write_json(out_dir / 'top_paths.json', artifacts.top_paths)
    write_json(out_dir / 'summary.json', json.loads(summary_with_ci.to_json(orient='records')))
    # replace summary in artifacts so callers get CI columns too
    artifacts.summary = summary_with_ci
    return artifacts
