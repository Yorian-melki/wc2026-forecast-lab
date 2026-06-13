from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np

from .data_loader import Team
from .utils import logistic


@dataclass
class MatchSummary:
    goals_a: int
    goals_b: int
    conduct_a: int
    conduct_b: int
    winner: str | None = None
    loser: str | None = None
    decided_in: str | None = None


class MatchModel:
    def __init__(self, config: dict):
        self.config = config
        self.base_group_xg = float(config['base_group_xg'])
        self.knockout_intensity_multiplier = float(config['knockout_intensity_multiplier'])
        self.extra_time_multiplier = float(config['extra_time_multiplier'])
        self.max_goals_cap = int(config['max_goals_cap'])
        self.penalty_logit_scale = float(config['penalty_logit_scale'])
        self.discipline_base_lambda = float(config['discipline_base_lambda'])
        self.dc_rho = float(config.get('dc_rho', 0.0))
        self.dc_max_goals = int(config.get('dc_max_goals', 7))
        self.red_card_threshold = int(config.get('red_card_threshold', 3))
        self.red_card_malus_prob = float(config.get('red_card_malus_prob', 0.30))
        self.home_nations = set(config.get('home_nation_codes', []))
        self.home_nation_xg_boost = float(config.get('home_nation_xg_boost', 0.0))
        # lazily populated: (code_a, code_b, context) → flat DC-corrected joint PMF
        # context ∈ {'group', 'ko', 'et'}
        self._dc_cache: dict[Tuple[str, str, str], np.ndarray] = {}

    def _latent_score(self, team: Team, opp: Team) -> float:
        # Analyst-prior attributes (0-100 scale; not statistically calibrated)
        analyst_score = (
            0.060 * (team.attack - opp.defense)
            + 0.030 * (team.midfield - opp.midfield)
            + 0.020 * (team.transition - opp.transition)
            + 0.012 * (team.setpiece - opp.setpiece)
            + 0.010 * (team.coach - opp.coach)
            + 0.008 * (team.form - opp.form)
            + 0.006 * (team.depth - opp.depth)
            + 0.006 * (team.health - opp.health)
            + 0.004 * (team.climate_resilience - opp.climate_resilience)
            + 0.004 * (team.altitude_resilience - opp.altitude_resilience)
            + 0.004 * (team.travel_resilience - opp.travel_resilience)
        )
        # StatsBomb features (data-driven: 30/48 teams real; 18 use defaults)
        # Coefficients are analyst priors — not calibrated via MLE (P1 TODO)
        # After /10 divisor: ppda gives ±1.5% xG/ppda-unit, shot_quality ±3%, press ±1.2%
        statsbomb_score = (
            0.030 * (opp.ppda - team.ppda)                         # pressing: lower PPDA = better
            + 5.000 * (team.shot_quality - opp.shot_quality)       # xG quality per shot
            + 0.400 * (team.press_intensity - opp.press_intensity)  # high-press transition edge
            # Comeback/choke resilience — real StatsBomb data for 30/48; fallback 0.30/0.20 for 18
            # Max impact ±2% xG for extreme differential (CRO comeback 0.75 vs MAR 0.00)
            + 0.300 * (team.comeback_rate - opp.comeback_rate)     # resilience under pressure
            - 0.200 * (team.choke_rate - opp.choke_rate)           # consistency when leading
        )
        return (analyst_score + statsbomb_score) / 10.0

    def expected_goals(self, team_a: Team, team_b: Team, knockout: bool = False) -> tuple[float, float]:
        base = self.base_group_xg * (self.knockout_intensity_multiplier if knockout else 1.0)
        mu_a = base * math.exp(self._latent_score(team_a, team_b))
        mu_b = base * math.exp(self._latent_score(team_b, team_a))
        if team_a.code in self.home_nations:
            mu_a *= (1.0 + self.home_nation_xg_boost)
        if team_b.code in self.home_nations:
            mu_b *= (1.0 + self.home_nation_xg_boost)
        # Jet lag multiplier — static NA-venue approximation (Dallas/01:00 UTC, 5 days adapt)
        mu_a *= team_a.jet_lag_factor
        mu_b *= team_b.jet_lag_factor
        mu_a = min(max(mu_a, 0.15), 3.60)
        mu_b = min(max(mu_b, 0.15), 3.60)
        return mu_a, mu_b

    def _build_dc_flat(self, mu_a: float, mu_b: float) -> np.ndarray:
        """
        Build Dixon-Coles corrected joint PMF, flattened to (dc_max_goals+1)^2.
        ρ > 0 reduces 0-0 and 1-1 draws, increases 1-0 and 0-1 decisive results —
        correcting the well-known Poisson over-estimation of drawn scorelines.
        """
        g = self.dc_max_goals + 1
        k = np.arange(g, dtype=np.float64)
        # log-space Poisson PMF to avoid underflow
        log_fact = np.array([math.lgamma(i + 1) for i in range(g)])
        pa = np.exp(k * math.log(max(mu_a, 1e-9)) - mu_a - log_fact)
        pb = np.exp(k * math.log(max(mu_b, 1e-9)) - mu_b - log_fact)
        joint = np.outer(pa, pb)
        rho = self.dc_rho
        if rho != 0.0:
            joint[0, 0] *= max(1.0 - mu_a * mu_b * rho, 1e-9)
            joint[1, 0] *= max(1.0 + mu_b * rho, 1e-9)
            joint[0, 1] *= max(1.0 + mu_a * rho, 1e-9)
            joint[1, 1] *= max(1.0 - rho, 1e-9)
        flat = joint.ravel()
        flat /= flat.sum()
        return flat

    def _dc_sample(
        self,
        team_a: Team,
        team_b: Team,
        knockout: bool,
        rng: np.random.Generator,
    ) -> Tuple[int, int]:
        ctx = 'ko' if knockout else 'group'
        key = (team_a.code, team_b.code, ctx)
        if key not in self._dc_cache:
            mu_a, mu_b = self.expected_goals(team_a, team_b, knockout=knockout)
            self._dc_cache[key] = self._build_dc_flat(mu_a, mu_b)
        flat = self._dc_cache[key]
        idx = int(rng.choice(len(flat), p=flat))
        g = self.dc_max_goals + 1
        return min(idx // g, self.max_goals_cap), min(idx % g, self.max_goals_cap)

    def conduct_lambda(self, team: Team, opp: Team) -> float:
        raw = self.discipline_base_lambda + max((100.0 - team.discipline) / 25.0, 0.0)
        style_drag = max((opp.transition - team.defense) / 90.0, 0.0)
        return max(0.15, raw + style_drag)

    def _apply_red_card_malus(self, goals: int, conduct: int, rng: np.random.Generator) -> int:
        if conduct >= self.red_card_threshold and rng.random() < self.red_card_malus_prob:
            return max(0, goals - 1)
        return goals

    def simulate_group_match(self, team_a: Team, team_b: Team, rng: np.random.Generator) -> MatchSummary:
        goals_a, goals_b = self._dc_sample(team_a, team_b, knockout=False, rng=rng)
        conduct_a = int(rng.poisson(self.conduct_lambda(team_a, team_b)))
        conduct_b = int(rng.poisson(self.conduct_lambda(team_b, team_a)))
        goals_a = self._apply_red_card_malus(goals_a, conduct_a, rng)
        goals_b = self._apply_red_card_malus(goals_b, conduct_b, rng)
        return MatchSummary(goals_a=goals_a, goals_b=goals_b, conduct_a=conduct_a, conduct_b=conduct_b)

    def _penalty_win_prob(self, team_a: Team, team_b: Team) -> float:
        delta = (team_a.penalties - team_b.penalties) + 0.6 * (team_a.goalkeeper - team_b.goalkeeper)
        return logistic(delta * self.penalty_logit_scale)

    def simulate_knockout_match(self, team_a: Team, team_b: Team, rng: np.random.Generator) -> MatchSummary:
        goals_a, goals_b = self._dc_sample(team_a, team_b, knockout=True, rng=rng)
        conduct_a = int(rng.poisson(self.conduct_lambda(team_a, team_b)))
        conduct_b = int(rng.poisson(self.conduct_lambda(team_b, team_a)))
        goals_a = self._apply_red_card_malus(goals_a, conduct_a, rng)
        goals_b = self._apply_red_card_malus(goals_b, conduct_b, rng)
        if goals_a != goals_b:
            winner = team_a.code if goals_a > goals_b else team_b.code
            loser = team_b.code if winner == team_a.code else team_a.code
            return MatchSummary(goals_a, goals_b, conduct_a, conduct_b, winner, loser, '90')

        # Extra time — build DC-corrected ET sample from scaled lambdas
        et_key = (team_a.code, team_b.code, 'et')
        if et_key not in self._dc_cache:
            mu_a, mu_b = self.expected_goals(team_a, team_b, knockout=True)
            self._dc_cache[et_key] = self._build_dc_flat(
                mu_a * self.extra_time_multiplier,
                mu_b * self.extra_time_multiplier,
            )
        flat_et = self._dc_cache[et_key]
        et_idx = int(rng.choice(len(flat_et), p=flat_et))
        g = self.dc_max_goals + 1
        et_a = min(et_idx // g, self.max_goals_cap)
        et_b = min(et_idx % g, self.max_goals_cap)

        total_a = goals_a + et_a
        total_b = goals_b + et_b
        if total_a != total_b:
            winner = team_a.code if total_a > total_b else team_b.code
            loser = team_b.code if winner == team_a.code else team_a.code
            return MatchSummary(total_a, total_b, conduct_a, conduct_b, winner, loser, 'ET')

        p_a = self._penalty_win_prob(team_a, team_b)
        a_wins = bool(rng.random() < p_a)
        winner = team_a.code if a_wins else team_b.code
        loser = team_b.code if a_wins else team_a.code
        return MatchSummary(total_a, total_b, conduct_a, conduct_b, winner, loser, 'PEN')

    def simulate_pairwise_monte_carlo(
        self,
        team_a: Team,
        team_b: Team,
        iterations: int,
        seed: int,
        batch_size: int,
    ) -> Dict[str, float]:
        rng = np.random.default_rng(np.random.PCG64DXSM(seed))
        remaining = iterations
        group_win_a = group_draw = group_win_b = 0
        ko_win90_a = ko_draw90 = ko_win90_b = 0
        ko_advance_a = ko_advance_b = 0
        ko_et_a = ko_et_b = 0
        ko_pen_a = ko_pen_b = 0
        goals_a_sum = goals_b_sum = 0
        conduct_a_sum = conduct_b_sum = 0
        mu_group_a, mu_group_b = self.expected_goals(team_a, team_b, knockout=False)
        mu_ko_a, mu_ko_b = self.expected_goals(team_a, team_b, knockout=True)
        p_pen_a = self._penalty_win_prob(team_a, team_b)
        while remaining > 0:
            n = min(remaining, batch_size)
            ga = rng.poisson(mu_group_a, size=n)
            gb = rng.poisson(mu_group_b, size=n)
            group_win_a += int(np.sum(ga > gb))
            group_draw += int(np.sum(ga == gb))
            group_win_b += int(np.sum(ga < gb))
            goals_a_sum += int(np.sum(ga))
            goals_b_sum += int(np.sum(gb))
            ca = rng.poisson(self.conduct_lambda(team_a, team_b), size=n)
            cb = rng.poisson(self.conduct_lambda(team_b, team_a), size=n)
            conduct_a_sum += int(np.sum(ca))
            conduct_b_sum += int(np.sum(cb))

            kga = rng.poisson(mu_ko_a, size=n)
            kgb = rng.poisson(mu_ko_b, size=n)
            ko_win90_a += int(np.sum(kga > kgb))
            ko_draw90 += int(np.sum(kga == kgb))
            ko_win90_b += int(np.sum(kga < kgb))

            draw_mask = kga == kgb
            draw_count = int(np.sum(draw_mask))
            if draw_count:
                etga = rng.poisson(mu_ko_a * self.extra_time_multiplier, size=draw_count)
                etgb = rng.poisson(mu_ko_b * self.extra_time_multiplier, size=draw_count)
                adv_a_mask = etga > etgb
                adv_b_mask = etga < etgb
                et_tie_mask = etga == etgb
                ko_advance_a += int(np.sum(adv_a_mask))
                ko_advance_b += int(np.sum(adv_b_mask))
                ko_et_a += int(np.sum(adv_a_mask))
                ko_et_b += int(np.sum(adv_b_mask))
                pen_count = int(np.sum(et_tie_mask))
                if pen_count:
                    pen_draws = rng.random(size=pen_count)
                    pen_a = int(np.sum(pen_draws < p_pen_a))
                    pen_b = pen_count - pen_a
                    ko_advance_a += pen_a
                    ko_advance_b += pen_b
                    ko_pen_a += pen_a
                    ko_pen_b += pen_b
            ko_advance_a += int(np.sum(kga > kgb))
            ko_advance_b += int(np.sum(kga < kgb))
            remaining -= n

        return {
            'team_a': team_a.code,
            'team_b': team_b.code,
            'iterations': int(iterations),
            'group_mu_a': mu_group_a,
            'group_mu_b': mu_group_b,
            'ko_mu_a': mu_ko_a,
            'ko_mu_b': mu_ko_b,
            'group_win_a': group_win_a / iterations,
            'group_draw': group_draw / iterations,
            'group_win_b': group_win_b / iterations,
            'ko_win90_a': ko_win90_a / iterations,
            'ko_draw90': ko_draw90 / iterations,
            'ko_win90_b': ko_win90_b / iterations,
            'ko_advance_a': ko_advance_a / iterations,
            'ko_advance_b': ko_advance_b / iterations,
            'ko_et_a': ko_et_a / iterations,
            'ko_et_b': ko_et_b / iterations,
            'ko_pen_a': ko_pen_a / iterations,
            'ko_pen_b': ko_pen_b / iterations,
            'avg_goals_a': goals_a_sum / iterations,
            'avg_goals_b': goals_b_sum / iterations,
            'avg_conduct_a': conduct_a_sum / iterations,
            'avg_conduct_b': conduct_b_sum / iterations,
        }
