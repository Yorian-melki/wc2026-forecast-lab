"""
Calibrated Elo match model for WC2026.

Survives P2.5 ablation gate as the most robust production model.
Verdict: Elo + calibrated draw beats more complex hybrid on ECE.

Model:
  log_mu_home = log_base + beta_elo * (elo_home - elo_away) / 400
  log_mu_away = log_base - beta_elo * (elo_home - elo_away) / 400

Parameters fitted on martj42 international_results (competitive, 2010-2025)
via Independent Poisson MLE + DC rho correction.

Same simulate_group_match / simulate_knockout_match interface as MatchModel.
Penalty and discipline logic identical to MatchModel.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from .data_loader import Team, load_config
from .match_model import MatchSummary
from .utils import logistic

_ROOT = Path(__file__).resolve().parents[2]
_DATA = _ROOT / "data"
_PARAMS_FILE = _DATA / "elo_calibrated_params.json"

# Default params if fitting hasn't been run (conservative estimates)
_DEFAULT_PARAMS = {
    "log_base": 0.262,   # exp(0.262) ≈ 1.30 goals/team/match
    "beta_elo": 0.45,    # Elo-diff/400 coefficient
    "rho": -0.04,        # DC correction (small, doesn't hurt ECE)
    "fit_date": "default",
    "note": "default params — run fit_elo_calibrated_params() for data-fitted values",
}


def load_team_elos() -> Dict[str, float]:
    """Load elo_current from teams.csv. Returns {code: elo} for all 48 WC2026 teams."""
    path = _DATA / "teams.csv"
    elos = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                elos[row["code"]] = float(row["elo_current"])
            except (KeyError, ValueError):
                elos[row["code"]] = 1500.0
    return elos


def load_calibrated_params() -> dict:
    """Load fitted calibrated Elo params from cache, or return defaults."""
    if _PARAMS_FILE.exists():
        return json.loads(_PARAMS_FILE.read_text())
    return _DEFAULT_PARAMS.copy()


def fit_elo_calibrated_params(save: bool = True, verbose: bool = True) -> dict:
    """
    Fit log_base, beta_elo, rho on competitive international matches (2010-2025).
    Saves to data/elo_calibrated_params.json.
    Returns param dict.
    """
    from scipy.optimize import minimize
    from .calibration.international_dataset import build_clean_dataset
    from .calibration.rolling_elo import RollingEloEngine

    if verbose:
        print("  Fitting calibrated Elo params on martj42 competitive 2010-2025...")

    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    if verbose:
        print(f"  Dataset: {len(df):,} competitive matches")

    # Build rolling Elo on all data
    elo = RollingEloEngine()
    elo.fit(df)

    # Pre-compute features for optimization
    home_teams = df["home_team"].tolist()
    away_teams = df["away_team"].tolist()
    dates      = df["date"].tolist()
    neutrals   = df["neutral"].tolist()
    h_goals    = np.array(df["home_goals"].tolist(), dtype=int)
    a_goals    = np.array(df["away_goals"].tolist(), dtype=int)
    h_lgamma   = np.array([math.lgamma(int(g)+1) for g in h_goals])
    a_lgamma   = np.array([math.lgamma(int(g)+1) for g in a_goals])

    elo_diffs = np.array([
        (elo.get_elo(h, before_date=d) + (0.0 if n else 100.0)
         - elo.get_elo(a, before_date=d)) / 400.0
        for h, a, d, n in zip(home_teams, away_teams, dates, neutrals)
    ])
    low_mask = (h_goals <= 1) & (a_goals <= 1)

    def objective(x):
        log_base, beta, rho = x[0], x[1], x[2]
        lmh = log_base + beta * elo_diffs
        lma = log_base - beta * elo_diffs
        mh = np.clip(np.exp(lmh), 0.05, 8.0)
        ma = np.clip(np.exp(lma), 0.05, 8.0)
        ll = -mh + h_goals*np.log(mh) - h_lgamma - ma + a_goals*np.log(ma) - a_lgamma
        if low_mask.any():
            mhL, maL = mh[low_mask], ma[low_mask]
            hgL, agL = h_goals[low_mask], a_goals[low_mask]
            tau = np.ones(low_mask.sum())
            tau[(hgL==0)&(agL==0)] = np.maximum(1.0 - mhL[(hgL==0)&(agL==0)]*maL[(hgL==0)&(agL==0)]*rho, 1e-9)
            tau[(hgL==1)&(agL==0)] = np.maximum(1.0 + maL[(hgL==1)&(agL==0)]*rho, 1e-9)
            tau[(hgL==0)&(agL==1)] = np.maximum(1.0 + mhL[(hgL==0)&(agL==1)]*rho, 1e-9)
            tau[(hgL==1)&(agL==1)] = np.maximum(1.0 - rho, 1e-9)
            ll[low_mask] += np.log(tau)
        ll = np.where(np.isfinite(ll), ll, -30.0)
        return float(-np.mean(ll))

    mean_g = float((df["home_goals"].mean() + df["away_goals"].mean()) / 2)
    res = minimize(objective, [math.log(max(mean_g, 0.5)), 0.40, -0.04],
                   method="L-BFGS-B",
                   bounds=[(-2.0, 1.5), (0.0, 2.0), (-0.20, 0.20)],
                   options={"maxiter": 2000, "ftol": 1e-11, "gtol": 1e-8})

    log_base, beta_elo, rho = float(res.x[0]), float(res.x[1]), float(res.x[2])
    if verbose:
        print(f"  Fitted: log_base={log_base:.4f} (xg={math.exp(log_base):.3f}), "
              f"beta_elo={beta_elo:.4f}, rho={rho:.4f}, NLL={res.fun:.5f}")

    # Snapshot current WC2026 team Elos
    name_to_code = {}
    wc_path = _DATA / "teams.csv"
    with wc_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name_to_code[row["name"]] = row["code"]

    # Use teams.csv elo_current (more reliable for WC2026 snapshot)
    team_elos_csv = load_team_elos()

    params = {
        "log_base": round(log_base, 6),
        "base_xg": round(math.exp(log_base), 4),
        "beta_elo": round(beta_elo, 6),
        "rho": round(rho, 6),
        "final_nll": round(float(res.fun), 6),
        "converged": bool(res.success),
        "n_train_matches": len(df),
        "fit_date": "2026-06-09",
        "fit_dataset": "martj42 competitive 2010-2025",
        "team_elos": {k: round(v, 1) for k, v in team_elos_csv.items()},
        "note": (
            "P2.5 production candidate. P2.5 ablation: Elo+calibrated_draw beats "
            "Full Hybrid on ECE (0.0170 vs 0.0199). Gate: BORDERLINE_EXPERIMENTAL "
            "for full hybrid → use Elo backbone only."
        ),
    }

    if save:
        _PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PARAMS_FILE.write_text(json.dumps(params, indent=2))
        if verbose:
            print(f"  Saved → {_PARAMS_FILE}")

    return params


class CalibratedEloMatchModel:
    """
    Match model using Elo + calibrated Poisson.

    Expected goals are derived solely from Elo difference.
    No per-team analyst priors, no StatsBomb features (residual signal < noise).

    Penalty and discipline logic identical to MatchModel.
    Compatible drop-in for TournamentSimulator(model=...).
    """

    def __init__(self, config: Optional[dict] = None, params: Optional[dict] = None,
                 use_ml: Optional[bool] = None):
        cfg = config or load_config()
        p = params or load_calibrated_params()

        self.log_base:      float = float(p["log_base"])
        self.beta_elo:      float = float(p["beta_elo"])
        self.rho:           float = float(p.get("rho", 0.0))
        self.team_elos:     Dict[str, float] = {k: float(v) for k, v in p.get("team_elos", {}).items()}
        self.params:        dict = p

        # Reuse config params that govern knockout mechanics / discipline
        self.knockout_intensity_multiplier = float(cfg["knockout_intensity_multiplier"])
        self.extra_time_multiplier         = float(cfg["extra_time_multiplier"])
        self.max_goals_cap                 = int(cfg["max_goals_cap"])
        self.penalty_logit_scale           = float(cfg["penalty_logit_scale"])
        self.discipline_base_lambda        = float(cfg["discipline_base_lambda"])
        self.dc_max_goals                  = int(cfg.get("dc_max_goals", 7))
        self.red_card_threshold            = int(cfg.get("red_card_threshold", 3))
        self.red_card_malus_prob           = float(cfg.get("red_card_malus_prob", 0.30))
        self.home_nations                  = set(cfg.get("home_nation_codes", []))
        self.home_nation_xg_boost          = float(cfg.get("home_nation_xg_boost", 0.0))
        # DC joint PMF cache: (code_a, code_b, ctx) → flat array
        self._dc_cache: dict[Tuple[str, str, str], np.ndarray] = {}

        # ── ML 1X2 ensemble (rollback-safe) ──────────────────────────────────
        # When enabled, the DC scoreline PMF is reweighted so its W/D/L marginals
        # match an ensemble of (DC-implied W/D/L) and (ML logistic W/D/L). The
        # conditional scoreline shape WITHIN each win/draw/loss region is preserved,
        # so goal differences (group tiebreaks) and draw scorelines (ET/penalties)
        # are untouched. ET increment PMF is never reweighted.
        self._ml_clf = None
        self._elo_weight: float = 1.0
        self._ml_weight: float = 0.0
        self._region_masks: Optional[tuple] = None
        self._configure_ml_ensemble(use_ml)

    def _configure_ml_ensemble(self, use_ml: Optional[bool]) -> None:
        """Load ML model + ensemble weights from data/model_stack_config.json.

        use_ml overrides the config flag when not None (for A/B comparison & tests).
        Any failure (missing config, missing pickle, sklearn import error) silently
        falls back to Elo-only — this IS the rollback path.
        """
        cfg_path = _DATA / "model_stack_config.json"
        enabled, ew, mw = False, 1.0, 0.0
        self._ml_mode, self._ml_gap_scale = "fixed", 300.0
        if cfg_path.exists():
            try:
                sc = json.loads(cfg_path.read_text())
                enabled = bool(sc.get("use_ml_match_model", False))
                ens = sc.get("ensemble", {})
                ew = float(ens.get("elo_calibrated_weight", 1.0))
                mw = float(ens.get("ml_logistic_weight", 0.0))
                self._ml_mode = str(sc.get("ml_weight_mode", "fixed"))
                self._ml_gap_scale = float(sc.get("ml_gap_scale", 300.0))
            except Exception:
                enabled = False
        if use_ml is not None:
            enabled = bool(use_ml)
        if not enabled:
            self._ml_clf, self._elo_weight, self._ml_weight = None, 1.0, 0.0
            return
        try:
            import pickle
            with open(_ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb") as f:
                self._ml_clf = pickle.load(f)
            s = ew + mw
            self._elo_weight, self._ml_weight = (ew / s, mw / s) if s > 0 else (1.0, 0.0)
        except Exception:
            self._ml_clf, self._elo_weight, self._ml_weight = None, 1.0, 0.0

    def set_ml_ensemble(self, clf, ml_weight: float,
                        mode: str = "fixed", gap_scale: float = 300.0) -> None:
        """Inject a trained 1X2 classifier at an explicit weight (for walk-forward sweeps).

        ml_weight=0 disables the ensemble (Elo-only). Clears the scoreline cache so the
        new weighting takes effect.

        mode="fixed"   : constant ml_weight for every match.
        mode="dynamic" : upset-robust. The effective weight decays with the absolute Elo
                         gap: w_eff = ml_weight / (1 + |elo_diff|/gap_scale). Big mismatches
                         (where ML over-concentrates on the favorite and hurts on upsets)
                         get LESS ML influence; near-even matches keep the full weight.
        """
        w = max(0.0, min(1.0, float(ml_weight)))
        self._ml_mode = mode
        self._ml_gap_scale = float(gap_scale)
        if clf is None or w == 0.0:
            self._ml_clf, self._elo_weight, self._ml_weight = None, 1.0, 0.0
        else:
            self._ml_clf = clf
            self._ml_weight, self._elo_weight = w, 1.0 - w
        self._dc_cache.clear()

    def _effective_ml_weight(self, team_a: Team, team_b: Team) -> float:
        if getattr(self, "_ml_mode", "fixed") != "dynamic":
            return self._ml_weight
        gap = abs(self._get_elo(team_a) - self._get_elo(team_b))
        return self._ml_weight / (1.0 + gap / self._ml_gap_scale)

    @property
    def use_ml(self) -> bool:
        return self._ml_clf is not None and self._ml_weight > 0.0

    def _region_index_masks(self, g: int):
        """Boolean masks over the flat (g*g) grid for home-win/draw/away-win cells."""
        if self._region_masks is None or self._region_masks[0] != g:
            idx = np.arange(g * g)
            i, j = idx // g, idx % g
            self._region_masks = (g, i > j, i == j, i < j)
        return self._region_masks[1], self._region_masks[2], self._region_masks[3]

    def _implied_wdl(self, flat: np.ndarray) -> Tuple[float, float, float]:
        home, draw, away = self._region_index_masks(self.dc_max_goals + 1)
        return float(flat[home].sum()), float(flat[draw].sum()), float(flat[away].sum())

    def _ml_wdl(self, team_a: Team, team_b: Team) -> Optional[Tuple[float, float, float]]:
        """ML 1X2 for a neutral match (home=team_a). Feature order matches ml.features."""
        if self._ml_clf is None:
            return None
        try:
            # neutral tournament match -> neutral_int=1, no home advantage (matches training)
            x = np.array([[self._get_elo(team_a) - self._get_elo(team_b), 1.0]])
            proba = self._ml_clf.predict_proba(x)[0]
            classes = list(self._ml_clf.classes_)
            d = {int(c): float(proba[i]) for i, c in enumerate(classes)}
            return d.get(0, 0.0), d.get(1, 0.0), d.get(2, 0.0)  # (home, draw, away)
        except Exception:
            return None

    def _reweight_flat_to_wdl(self, flat: np.ndarray,
                              target: Tuple[float, float, float]) -> np.ndarray:
        """Scale each W/D/L region of `flat` so its sum matches target, renormalize.

        Preserves the conditional scoreline distribution within each region.
        """
        home, draw, away = self._region_index_masks(self.dc_max_goals + 1)
        tw, td, tl = target
        sw, sd, sl = flat[home].sum(), flat[draw].sum(), flat[away].sum()
        out = flat.copy()
        if sw > 0:
            out[home] *= tw / sw
        if sd > 0:
            out[draw] *= td / sd
        if sl > 0:
            out[away] *= tl / sl
        total = out.sum()
        return out / total if total > 0 else flat

    def _get_elo(self, team: Team) -> float:
        return self.team_elos.get(team.code, 1500.0)

    def expected_goals(self, team_a: Team, team_b: Team, knockout: bool = False) -> Tuple[float, float]:
        """Elo-only expected goals: no analyst priors, no StatsBomb residuals."""
        elo_a = self._get_elo(team_a)
        elo_b = self._get_elo(team_b)
        # WC2026: all venues in North America — always neutral for non-host teams
        elo_diff_scaled = (elo_a - elo_b) / 400.0
        log_mu_a = self.log_base + self.beta_elo * elo_diff_scaled
        log_mu_b = self.log_base - self.beta_elo * elo_diff_scaled
        mul = self.knockout_intensity_multiplier if knockout else 1.0
        mu_a = math.exp(log_mu_a) * mul
        mu_b = math.exp(log_mu_b) * mul
        # Host-nation home boost (USA/MEX/CAN)
        if team_a.code in self.home_nations:
            mu_a *= (1.0 + self.home_nation_xg_boost)
        if team_b.code in self.home_nations:
            mu_b *= (1.0 + self.home_nation_xg_boost)
        # Jet lag (already computed in Team.jet_lag_factor)
        mu_a *= team_a.jet_lag_factor
        mu_b *= team_b.jet_lag_factor
        mu_a = min(max(mu_a, 0.15), 3.60)
        mu_b = min(max(mu_b, 0.15), 3.60)
        return mu_a, mu_b

    def _build_dc_flat(self, mu_a: float, mu_b: float) -> np.ndarray:
        g = self.dc_max_goals + 1
        k = np.arange(g, dtype=np.float64)
        log_fact = np.array([math.lgamma(i + 1) for i in range(g)])
        pa = np.exp(k * math.log(max(mu_a, 1e-9)) - mu_a - log_fact)
        pb = np.exp(k * math.log(max(mu_b, 1e-9)) - mu_b - log_fact)
        joint = np.outer(pa, pb)
        rho = self.rho
        if rho != 0.0:
            joint[0, 0] *= max(1.0 - mu_a * mu_b * rho, 1e-9)
            joint[1, 0] *= max(1.0 + mu_b * rho, 1e-9)
            joint[0, 1] *= max(1.0 + mu_a * rho, 1e-9)
            joint[1, 1] *= max(1.0 - rho, 1e-9)
        flat = joint.ravel()
        flat /= flat.sum()
        return flat

    def scoreline_probs(self, team_a: Team, team_b: Team, knockout: bool = False) -> np.ndarray:
        """Flat scoreline distribution (incl. ML reweighting) the model samples from.

        Index idx -> goals (idx // g, idx % g) with g = dc_max_goals + 1; sums to 1.
        Exposed publicly so the live scorecard scores real results against the SAME
        distribution the Monte Carlo actually simulates (no re-derivation, no drift)."""
        mu_a, mu_b = self.expected_goals(team_a, team_b, knockout=knockout)
        flat = self._build_dc_flat(mu_a, mu_b)
        if self.use_ml:
            ml = self._ml_wdl(team_a, team_b)
            if ml is not None:
                w_ml = self._effective_ml_weight(team_a, team_b)  # per-pair (fixed or dynamic)
                w_elo = 1.0 - w_ml
                dc = self._implied_wdl(flat)
                target = tuple(w_elo * d + w_ml * m for d, m in zip(dc, ml))
                flat = self._reweight_flat_to_wdl(flat, target)
        return flat

    def _dc_sample(self, team_a: Team, team_b: Team,
                   knockout: bool, rng: np.random.Generator) -> Tuple[int, int]:
        ctx = "ko" if knockout else "group"
        key = (team_a.code, team_b.code, ctx)
        if key not in self._dc_cache:
            self._dc_cache[key] = self.scoreline_probs(team_a, team_b, knockout=knockout)
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

    def _penalty_win_prob(self, team_a: Team, team_b: Team) -> float:
        delta = (team_a.penalties - team_b.penalties) + 0.6 * (team_a.goalkeeper - team_b.goalkeeper)
        return logistic(delta * self.penalty_logit_scale)

    def simulate_group_match(self, team_a: Team, team_b: Team,
                              rng: np.random.Generator) -> MatchSummary:
        goals_a, goals_b = self._dc_sample(team_a, team_b, knockout=False, rng=rng)
        conduct_a = int(rng.poisson(self.conduct_lambda(team_a, team_b)))
        conduct_b = int(rng.poisson(self.conduct_lambda(team_b, team_a)))
        goals_a = self._apply_red_card_malus(goals_a, conduct_a, rng)
        goals_b = self._apply_red_card_malus(goals_b, conduct_b, rng)
        return MatchSummary(goals_a=goals_a, goals_b=goals_b,
                            conduct_a=conduct_a, conduct_b=conduct_b)

    def simulate_knockout_match(self, team_a: Team, team_b: Team,
                                 rng: np.random.Generator) -> MatchSummary:
        goals_a, goals_b = self._dc_sample(team_a, team_b, knockout=True, rng=rng)
        conduct_a = int(rng.poisson(self.conduct_lambda(team_a, team_b)))
        conduct_b = int(rng.poisson(self.conduct_lambda(team_b, team_a)))
        goals_a = self._apply_red_card_malus(goals_a, conduct_a, rng)
        goals_b = self._apply_red_card_malus(goals_b, conduct_b, rng)
        if goals_a != goals_b:
            winner = team_a.code if goals_a > goals_b else team_b.code
            loser  = team_b.code if winner == team_a.code else team_a.code
            return MatchSummary(goals_a, goals_b, conduct_a, conduct_b, winner, loser, "90")

        # Extra time
        et_key = (team_a.code, team_b.code, "et")
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
            loser  = team_b.code if winner == team_a.code else team_a.code
            return MatchSummary(total_a, total_b, conduct_a, conduct_b, winner, loser, "ET")

        p_a = self._penalty_win_prob(team_a, team_b)
        a_wins = bool(rng.random() < p_a)
        winner = team_a.code if a_wins else team_b.code
        loser  = team_b.code if a_wins else team_a.code
        return MatchSummary(total_a, total_b, conduct_a, conduct_b, winner, loser, "PEN")
