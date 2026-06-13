"""
In-play probability model — WC2026.

Separate from pre-match model. Do NOT use for pre-match forecasts.

Data quality badges:
  A = xG + full in-play stats (requires paid provider — not currently available)
  B = shots / SOT / corners / cards (requires paid provider)
  C = score + minute only (Dixon-Robinson score-time model)
  D = stale / no live data

Model: Dixon-Robinson (1998) score-time Poisson.
  At minute t with score (h, a), remaining goal rates are adjusted for:
  - Current score differential (leading teams defend more)
  - Time remaining
  - Pre-match expected goals (λ_h, λ_a)

Reference: Dixon, M.J. & Robinson, M.E. (1998). A birth process model for association football matches.
The Statistician, 47(3), 523–538.

Limitations (non-negotiable):
  - No historical in-play backtest performed.
  - Score-time model uses simplified rate adjustment, not MLE-fit decay.
  - xG proxy (shots × shot_quality) is NOT real xG.
  - Cannot claim "market-grade" in-play accuracy.
  - Minimum data quality: C (score + minute). Below that: return None.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class InPlayInput:
    """Input data for in-play model."""
    # Required
    minute: int
    home_score: int
    away_score: int
    pre_match_lambda_home: float  # Pre-match expected goals, home
    pre_match_lambda_away: float  # Pre-match expected goals, away

    # Optional — quality upgrades
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    xg_home: Optional[float] = None  # Real xG from provider
    xg_away: Optional[float] = None
    possession_home: Optional[float] = None  # 0–100
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None
    red_cards_home: Optional[int] = None
    red_cards_away: Optional[int] = None
    is_knockout: bool = False

    @property
    def data_quality(self) -> str:
        if self.xg_home is not None or self.xg_away is not None:
            return "A"
        if self.shots_home is not None and self.shots_on_target_home is not None:
            return "B"
        if self.minute is not None and self.home_score is not None:
            return "C"
        return "D"


@dataclass
class InPlayOutput:
    """Output of in-play model."""
    p_home_win: float
    p_draw: float
    p_away_win: float
    p_home_ko_advance: Optional[float]  # If knockout
    p_away_ko_advance: Optional[float]
    expected_remaining_goals_home: float
    expected_remaining_goals_away: float
    data_quality: str
    quality_warning: str
    model_note: str


# ─── core rate functions ───────────────────────────────────────────────────────

def _remaining_rate(
    lambda_pre: float,
    elapsed: int,
    total: int = 90,
    score_diff: int = 0,
    red_card_adj: float = 0.0,
) -> float:
    """
    Estimate remaining goal rate for one team.
    Uses simple time-scaling + score-state adjustment.
    NOT the full Dixon-Robinson Markov model (that requires MLE on in-play data).
    """
    remaining = max(total - elapsed, 1) / total
    rate = lambda_pre * remaining

    # Score-state adjustment: teams leading defend more aggressively
    if score_diff > 0:
        # Leading: reduce attack rate slightly
        rate *= max(0.65, 1.0 - 0.12 * score_diff)
    elif score_diff < 0:
        # Trailing: increase attack rate (desperate mode)
        rate *= min(1.45, 1.0 + 0.15 * abs(score_diff))

    # Red card adjustment
    rate *= max(0.0, 1.0 + red_card_adj)

    return max(rate, 0.0)


def _xg_proxy_rate(
    shots: int,
    shots_on_target: int,
    elapsed: int,
    total: int = 90,
    default_rate: float = 0.5,
) -> float:
    """
    Proxy xG rate from shots — NOT real xG.
    Must be labeled as PROXY in output.
    Using empirical shot-to-goal ratio ~10-11% for WC historically.
    """
    if elapsed < 5:
        return default_rate
    minutes_played = max(elapsed, 1)
    shot_rate_per_min = shots / minutes_played
    xg_rate_per_min = shot_rate_per_min * 0.105  # empirical WC ratio
    remaining = max(total - elapsed, 1)
    return xg_rate_per_min * remaining


def _poisson_sum_prob(lambda_h: float, lambda_a: float, max_goals: int = 8) -> tuple[float, float, float]:
    """
    Compute P(home win), P(draw), P(away win) from two independent Poisson rates.
    Returns (p_home, p_draw, p_away).
    """
    p_home = p_draw = p_away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = (math.exp(-lambda_h) * lambda_h**i / math.factorial(i) *
                 math.exp(-lambda_a) * lambda_a**j / math.factorial(j))
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    total = p_home + p_draw + p_away
    if total < 1e-9:
        return 1/3, 1/3, 1/3
    return p_home / total, p_draw / total, p_away / total


def _ko_advance_prob(
    p_home_win_90: float,
    p_draw_90: float,
    p_away_win_90: float,
    lambda_h_et: float,
    lambda_a_et: float,
) -> tuple[float, float]:
    """
    P(home/away advances) in knockout.
    If draw after 90: ET + penalties (simplified: 50/50 in penalties).
    """
    # 90-min winner goes through directly
    p_home_adv = p_home_win_90
    p_away_adv = p_away_win_90

    # If draw: play extra time
    p_h_et, p_d_et, p_a_et = _poisson_sum_prob(lambda_h_et, lambda_a_et)
    p_pens = 0.50  # simplified (would need team-specific penalty data)

    p_home_adv += p_draw_90 * (p_h_et + p_d_et * p_pens)
    p_away_adv += p_draw_90 * (p_a_et + p_d_et * (1 - p_pens))

    # Normalize
    total = p_home_adv + p_away_adv
    if total < 1e-9:
        return 0.5, 0.5
    return p_home_adv / total, p_away_adv / total


# ─── main function ─────────────────────────────────────────────────────────────

def compute_inplay(inp: InPlayInput) -> Optional[InPlayOutput]:
    """
    Compute in-play win probabilities.
    Returns None if data quality is D (stale/missing).
    """
    if inp.data_quality == "D":
        return None

    elapsed = max(0, min(inp.minute, 90))
    score_diff_h = inp.home_score - inp.away_score
    score_diff_a = -score_diff_h

    red_adj_h = -0.25 * (inp.red_cards_home or 0)
    red_adj_a = -0.25 * (inp.red_cards_away or 0)

    quality_note = ""
    model_note   = "Dixon-Robinson score-time Poisson (simplified, no MLE in-play backtest)"

    # Determine remaining rates
    if inp.data_quality == "A" and inp.xg_home is not None:
        # Real xG from provider
        remaining_frac = max(90 - elapsed, 1) / 90
        lam_h = max(inp.xg_home * remaining_frac * 0.9, 0.0)
        lam_a = max(inp.xg_away * remaining_frac * 0.9, 0.0)
        lam_h *= max(0.0, 1.0 + red_adj_h)
        lam_a *= max(0.0, 1.0 + red_adj_a)
        quality_note = ""

    elif inp.data_quality == "B" and inp.shots_home is not None:
        # Proxy xG from shots/SOT
        lam_h = _xg_proxy_rate(
            inp.shots_home, inp.shots_on_target_home or 0, elapsed,
            default_rate=inp.pre_match_lambda_home * (90 - elapsed) / 90
        )
        lam_a = _xg_proxy_rate(
            inp.shots_away, inp.shots_on_target_away or 0, elapsed,
            default_rate=inp.pre_match_lambda_away * (90 - elapsed) / 90
        )
        lam_h *= max(0.0, 1.0 + red_adj_h)
        lam_a *= max(0.0, 1.0 + red_adj_a)
        quality_note = "⚠️ xG PROXY (shots × 0.105 empirical ratio) — NOT real xG. Label as proxy."

    else:
        # Score + minute only
        lam_h = _remaining_rate(
            inp.pre_match_lambda_home, elapsed,
            score_diff=score_diff_h, red_card_adj=red_adj_h
        )
        lam_a = _remaining_rate(
            inp.pre_match_lambda_away, elapsed,
            score_diff=score_diff_a, red_card_adj=red_adj_a
        )
        quality_note = "ℹ️ Score-time model only. No in-play stats available."

    # Compute probabilities over remaining goals
    # Current score: (home_score, away_score) already on board
    # Outcome probabilities: P(home wins) = P(home adds more goals than away in remaining time)
    p_h_more, p_equal, p_a_more = _poisson_sum_prob(lam_h, lam_a)

    # Convert to final result probabilities
    diff = score_diff_h
    if diff > 0:
        # Home leading
        p_home_win_90 = p_h_more + p_equal + (p_a_more if abs(diff) > 1 else 0)
        # Actually need to think properly:
        # If home leads by D, home wins if away doesn't net D+ more goals than home
        p_home_win_90 = _compute_lead_win_prob(lam_h, lam_a, diff, 90 - elapsed)
        p_draw_90     = _compute_equalize_prob(lam_h, lam_a, diff, 90 - elapsed)
        p_away_win_90 = max(0, 1 - p_home_win_90 - p_draw_90)
    elif diff < 0:
        p_away_win_90 = _compute_lead_win_prob(lam_a, lam_h, abs(diff), 90 - elapsed)
        p_draw_90     = _compute_equalize_prob(lam_a, lam_h, abs(diff), 90 - elapsed)
        p_home_win_90 = max(0, 1 - p_away_win_90 - p_draw_90)
    else:
        # Level
        p_home_win_90, p_draw_90, p_away_win_90 = _poisson_sum_prob(lam_h, lam_a)

    # Knockout
    p_h_ko = p_a_ko = None
    if inp.is_knockout:
        lam_h_et = lam_h * 30 / max(90 - elapsed, 1)
        lam_a_et = lam_a * 30 / max(90 - elapsed, 1)
        p_h_ko, p_a_ko = _ko_advance_prob(p_home_win_90, p_draw_90, p_away_win_90,
                                           lam_h_et, lam_a_et)

    return InPlayOutput(
        p_home_win=round(p_home_win_90, 4),
        p_draw=round(p_draw_90, 4),
        p_away_win=round(p_away_win_90, 4),
        p_home_ko_advance=round(p_h_ko, 4) if p_h_ko is not None else None,
        p_away_ko_advance=round(p_a_ko, 4) if p_a_ko is not None else None,
        expected_remaining_goals_home=round(lam_h, 4),
        expected_remaining_goals_away=round(lam_a, 4),
        data_quality=inp.data_quality,
        quality_warning=quality_note,
        model_note=model_note,
    )


def _compute_lead_win_prob(
    lam_leader: float, lam_trailer: float, lead: int, remaining_min: int, max_g: int = 8
) -> float:
    """P(leading team wins given current lead of `lead` goals)."""
    p = 0.0
    for extra_l in range(max_g + 1):
        for extra_t in range(max_g + 1):
            if extra_l + lead > extra_t:  # still leads
                p += (math.exp(-lam_leader) * lam_leader**extra_l / math.factorial(extra_l) *
                      math.exp(-lam_trailer) * lam_trailer**extra_t / math.factorial(extra_t))
    return min(p, 1.0)


def _compute_equalize_prob(
    lam_leader: float, lam_trailer: float, lead: int, remaining_min: int, max_g: int = 8
) -> float:
    """P(match ends level given current leader leads by `lead`)."""
    p = 0.0
    for extra_l in range(max_g + 1):
        extra_t = extra_l + lead
        if extra_t > max_g:
            continue
        p += (math.exp(-lam_leader) * lam_leader**extra_l / math.factorial(extra_l) *
              math.exp(-lam_trailer) * lam_trailer**extra_t / math.factorial(extra_t))
    return min(p, 1.0)
