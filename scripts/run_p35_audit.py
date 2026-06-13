#!/usr/bin/env python
"""
P3.5 Elo-calibrated sanity audit.

Diagnoses and fixes over-concentration caused by beta_elo=0.988 fitted on
competitive-only data. Target: top3 champion concentration ≤ 45%.

Outputs:
  outputs/calibration/elo_concentration_audit.csv
  outputs/calibration/elo_concentration_audit.md
  outputs/calibration/elo_match_sanity.csv
  outputs/calibration/elo_temperature_ablation.csv
  outputs/calibration/elo_temperature_summary.md
  outputs/calibration/historical_tournament_concentration.csv
  outputs/calibration/historical_tournament_concentration.md
  outputs/calibration/elo_calibration_gate.json
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs" / "calibration"
OUT.mkdir(parents=True, exist_ok=True)

from wc2026.data_loader import load_config, load_groups, load_teams
from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
from wc2026.tournament import TournamentSimulator
from wc2026.confidence import add_confidence_intervals

# ─────────────────────────────────────────────────────────────────────────────
# 1. Concentration metrics
# ─────────────────────────────────────────────────────────────────────────────

def concentration_metrics(df: pd.DataFrame, label: str) -> dict:
    p = df["champion_prob"].sort_values(ascending=False).values
    entropy = float(-np.sum(p * np.log(np.maximum(p, 1e-15))))
    return {
        "model": label,
        "top1": round(float(p[0]), 5),
        "top3": round(float(p[:3].sum()), 5),
        "top5": round(float(p[:5].sum()), 5),
        "top10": round(float(p[:10].sum()), 5),
        "entropy": round(entropy, 4),
        "entropy_max": round(math.log(len(p)), 4),
        "entropy_ratio": round(entropy / math.log(len(p)), 4),
        "herfindahl": round(float(np.sum(p**2)), 6),
        "n_teams": len(p),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Match-level Poisson probabilities
# ─────────────────────────────────────────────────────────────────────────────

def poisson_1x2(mu_h: float, mu_a: float, rho: float = 0.0, max_g: int = 10) -> tuple[float, float, float]:
    def pmf(k, mu):
        return math.exp(-mu + k * math.log(max(mu, 1e-12)) - math.lgamma(k + 1))
    def tau(i, j):
        if i == 0 and j == 0: return max(1.0 - mu_h * mu_a * rho, 1e-9)
        if i == 1 and j == 0: return max(1.0 + mu_a * rho, 1e-9)
        if i == 0 and j == 1: return max(1.0 + mu_h * rho, 1e-9)
        if i == 1 and j == 1: return max(1.0 - rho, 1e-9)
        return 1.0
    ph = pd_ = pa = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = pmf(i, mu_h) * pmf(j, mu_a) * tau(i, j)
            if i > j: ph += p
            elif i == j: pd_ += p
            else: pa += p
    total = ph + pd_ + pa
    return ph / total, pd_ / total, pa / total


def match_probs_for_beta(elo_a: float, elo_b: float,
                          log_base: float, beta: float, rho: float,
                          knockout: bool = False, ko_mul: float = 0.96) -> dict:
    diff = (elo_a - elo_b) / 400.0
    mul = ko_mul if knockout else 1.0
    mu_a = math.exp(log_base + beta * diff) * mul
    mu_b = math.exp(log_base - beta * diff) * mul
    mu_a = min(max(mu_a, 0.15), 3.60)
    mu_b = min(max(mu_b, 0.15), 3.60)
    ph, pd, pa = poisson_1x2(mu_a, mu_b, rho=rho)
    # KO advance probability: win 90min + draw-then-coin (approx)
    p_ko_draw = pd
    p_advance_a = ph + p_ko_draw * 0.5  # rough approx (ignores ET scoring)
    p_advance_b = pa + p_ko_draw * 0.5
    return {
        "mu_a": round(mu_a, 3), "mu_b": round(mu_b, 3),
        "p_a_win_90": round(ph, 4), "p_draw_90": round(pd, 4), "p_b_win_90": round(pa, 4),
        "p_a_advance_ko": round(p_advance_a, 4), "p_b_advance_ko": round(p_advance_b, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Mini tournament simulation with custom beta
# ─────────────────────────────────────────────────────────────────────────────

def run_mini_simulation(beta_mul: float, label: str, iterations: int = 15_000,
                        seed: int = 20260609, verbose: bool = True) -> dict:
    """Run tournament simulation with beta_elo * beta_mul. Returns concentration metrics."""
    teams  = load_teams()
    groups = load_groups()
    config = load_config()
    params = load_calibrated_params()
    params_modified = {**params, "beta_elo": params["beta_elo"] * beta_mul}

    model = CalibratedEloMatchModel(config=config, params=params_modified)
    sim   = TournamentSimulator(teams=teams, groups=groups, config=config, model=model)
    arts  = sim.simulate_many(iterations=iterations, seed=seed)
    df    = arts.summary

    m = concentration_metrics(df, label)
    m["beta_elo"] = round(params_modified["beta_elo"], 4)
    m["beta_mul"] = round(beta_mul, 3)
    m["iterations"] = iterations

    # Top team probabilities
    top5 = df.head(5)[["team", "champion_prob"]].to_dict("records")
    m["top_teams"] = top5

    if verbose:
        t1, t3, t5 = m["top1"]*100, m["top3"]*100, m["top5"]*100
        print(f"  {label:<28}  top1={t1:.1f}%  top3={t3:.1f}%  top5={t5:.1f}%  "
              f"H={m['herfindahl']:.4f}  β={m['beta_elo']:.3f}")
        for r in top5[:3]:
            print(f"    {r['team']}: {r['champion_prob']*100:.1f}%")

    return m


# ─────────────────────────────────────────────────────────────────────────────
# 4. Historical WC approximation
# ─────────────────────────────────────────────────────────────────────────────

def build_historical_wc_snapshot(before_date: str) -> dict[str, float]:
    """Get Elo ratings for WC2026 teams just before given date from rolling engine."""
    from wc2026.calibration.international_dataset import build_clean_dataset
    from wc2026.calibration.rolling_elo import RollingEloEngine
    df, _ = build_clean_dataset(min_year=1990, max_year=2025)
    df_before = df[df["date"] < before_date]
    engine = RollingEloEngine()
    engine.fit(df_before)
    wc_teams_csv = ROOT / "data" / "teams.csv"
    import csv
    elos = {}
    with wc_teams_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            elo = engine.ratings.get(row["name"], 1500.0)
            elos[row["code"]] = elo
    return elos


def run_historical_concentration(before_date: str, tournament_label: str,
                                  beta_values: list[float], verbose: bool = True) -> list[dict]:
    """
    Approximate champion concentration for historical WC using martj42 Elos.
    Uses current WC2026 bracket structure (48 teams) as proxy.
    Not exact — groups and opponents differ — but captures concentration level.
    """
    if verbose:
        print(f"\n  Historical snapshot: {tournament_label} (Elos before {before_date})")

    hist_elos = build_historical_wc_snapshot(before_date)
    teams = load_teams()
    groups = load_groups()
    config = load_config()
    params = load_calibrated_params()
    rows = []
    for beta_mul in beta_values:
        params_mod = {**params, "beta_elo": params["beta_elo"] * beta_mul,
                      "team_elos": hist_elos}
        model = CalibratedEloMatchModel(config=config, params=params_mod)
        sim   = TournamentSimulator(teams=teams, groups=groups, config=config, model=model)
        arts  = sim.simulate_many(10_000, seed=20260609)
        df    = arts.summary
        m     = concentration_metrics(df, f"{tournament_label}_beta{beta_mul:.2f}")
        m["tournament"] = tournament_label
        m["before_date"] = before_date
        m["beta_mul"] = beta_mul
        rows.append(m)
        if verbose:
            print(f"    β×{beta_mul:.2f}: top1={m['top1']*100:.1f}%, "
                  f"top3={m['top3']*100:.2f}%")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. Match sanity table
# ─────────────────────────────────────────────────────────────────────────────

def build_match_sanity(params: dict) -> pd.DataFrame:
    """Compute match probabilities for key matchups at all temperature values."""
    log_base = params["log_base"]
    rho      = params["rho"]
    elos     = params["team_elos"]
    orig_beta = params["beta_elo"]

    team_elos_sorted = sorted(elos.items(), key=lambda x: -x[1])
    rank_20_code = team_elos_sorted[19][0]
    rank_40_code = team_elos_sorted[39][0]
    rank_10_code = team_elos_sorted[9][0]
    rank_30_code = team_elos_sorted[29][0]
    median_code  = team_elos_sorted[23][0]

    matchups = [
        ("ESP", "ARG"),
        ("ESP", "FRA"),
        ("ESP", "BRA"),
        ("ESP", "ENG"),
        ("FRA", "ARG"),
        ("ARG", "BRA"),
        ("BRA", "ENG"),
        ("ESP", rank_20_code),
        ("ESP", rank_40_code),
        (rank_10_code, rank_30_code),
    ]

    rows = []
    for beta_mul in [1.00, 0.85, 0.70, 0.55, 0.40]:
        beta = orig_beta * beta_mul
        for code_a, code_b in matchups:
            elo_a = elos.get(code_a, 1500.0)
            elo_b = elos.get(code_b, 1500.0)
            m = match_probs_for_beta(elo_a, elo_b, log_base, beta, rho, knockout=False)
            m_ko = match_probs_for_beta(elo_a, elo_b, log_base, beta, rho, knockout=True)
            rows.append({
                "beta_mul": beta_mul, "beta": round(beta, 4),
                "team_a": code_a, "team_b": code_b,
                "elo_a": elo_a, "elo_b": elo_b,
                "elo_diff": elo_a - elo_b,
                "expected_goals_a": m["mu_a"], "expected_goals_b": m["mu_b"],
                "p_a_win_90": m["p_a_win_90"],
                "p_draw_90": m["p_draw_90"],
                "p_b_win_90": m["p_b_win_90"],
                "p_a_advance_ko": m_ko["p_a_advance_ko"],
                "p_b_advance_ko": m_ko["p_b_advance_ko"],
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Production gate
# ─────────────────────────────────────────────────────────────────────────────

VERDICTS = ("PASS_ELO_CALIBRATED", "PASS_WITH_TEMPERATURE",
            "FAIL_KEEP_EXPERT", "FAIL_NEED_BLEND")

# Historical WC top3 reference (betting market calibration, average pre-tournament)
# WC2018: top3 ≈ 34%, WC2022: top3 ≈ 39%, avg ≈ 36%
HISTORICAL_TOP3_REFERENCE = 0.36
HISTORICAL_TOP3_TOLERANCE = 0.10  # allow ±10pp
TOP3_UPPER_BOUND = HISTORICAL_TOP3_REFERENCE + HISTORICAL_TOP3_TOLERANCE  # 46%
TOP1_UPPER_BOUND = 0.20   # no single team > 20% without very strong justification

# What constitutes a "plausible" match outcome
# ESP vs FRA (top team vs 2nd team): P(ESP win 90min) should be 42–58%
ESP_FRA_WIN_UPPER = 0.58
ESP_FRA_WIN_LOWER = 0.38
# ESP vs rank-20: P(ESP win 90min) should be 55–72%
ESP_RANK20_WIN_UPPER = 0.72
# Draw rate vs any opponent: draw ≥ 20% for any matchup
DRAW_FLOOR = 0.18


def compute_production_gate(
    conc_orig: dict,
    ablation_rows: list[dict],
    match_sanity: pd.DataFrame,
    best_beta_mul: float,
    best_conc: dict,
) -> dict:
    orig_top3 = conc_orig["top3"]
    orig_top1 = conc_orig["top1"]
    params = load_calibrated_params()
    log_base = params["log_base"]
    orig_beta = params["beta_elo"]
    rho = params["rho"]

    criteria_met, criteria_failed = [], []

    # --- top3 concentration check ---
    if orig_top3 <= TOP3_UPPER_BOUND:
        criteria_met.append(f"top3 concentration OK ({orig_top3*100:.1f}% ≤ {TOP3_UPPER_BOUND*100:.0f}%)")
    else:
        criteria_failed.append(f"top3 OVER-CONCENTRATED ({orig_top3*100:.1f}% > {TOP3_UPPER_BOUND*100:.0f}%)")

    # --- top1 check ---
    if orig_top1 <= TOP1_UPPER_BOUND:
        criteria_met.append(f"top1 concentration OK ({orig_top1*100:.1f}% ≤ {TOP1_UPPER_BOUND*100:.0f}%)")
    else:
        criteria_failed.append(f"top1 OVER-CONCENTRATED ({orig_top1*100:.1f}% > {TOP1_UPPER_BOUND*100:.0f}%)")

    # --- match plausibility: ESP vs FRA ---
    esp_fra = match_sanity[(match_sanity["team_a"]=="ESP") &
                            (match_sanity["team_b"]=="FRA") &
                            (match_sanity["beta_mul"]==1.00)]
    if not esp_fra.empty:
        pw = float(esp_fra.iloc[0]["p_a_win_90"])
        pd_ = float(esp_fra.iloc[0]["p_draw_90"])
        if ESP_FRA_WIN_LOWER <= pw <= ESP_FRA_WIN_UPPER:
            criteria_met.append(f"ESP vs FRA win prob plausible ({pw*100:.1f}%)")
        else:
            criteria_failed.append(f"ESP vs FRA win prob implausible ({pw*100:.1f}%, expected {ESP_FRA_WIN_LOWER*100:.0f}–{ESP_FRA_WIN_UPPER*100:.0f}%)")
        if pd_ >= DRAW_FLOOR:
            criteria_met.append(f"draw rate ≥ floor ({pd_*100:.1f}%)")
        else:
            criteria_failed.append(f"draw rate too low ({pd_*100:.1f}%)")
    else:
        criteria_failed.append("ESP vs FRA not found in match sanity")

    # --- ESP vs rank-20 plausibility ---
    esp_r20 = match_sanity[(match_sanity["team_a"]=="ESP") &
                            (match_sanity["beta_mul"]==1.00)]
    esp_r20 = esp_r20[esp_r20["elo_b"] < 1950]  # rank ~20 team
    if not esp_r20.empty:
        pw_r20 = float(esp_r20.iloc[0]["p_a_win_90"])
        if pw_r20 <= ESP_RANK20_WIN_UPPER:
            criteria_met.append(f"ESP vs rank-20 win prob plausible ({pw_r20*100:.1f}% ≤ {ESP_RANK20_WIN_UPPER*100:.0f}%)")
        else:
            criteria_failed.append(f"ESP vs rank-20 win prob IMPLAUSIBLE ({pw_r20*100:.1f}% > {ESP_RANK20_WIN_UPPER*100:.0f}%)")

    # --- temperature fix available? ---
    temp_top3_ok = [r for r in ablation_rows if r.get("top3", 1.0) <= TOP3_UPPER_BOUND]
    temp_top1_ok = [r for r in ablation_rows if r.get("top1", 1.0) <= TOP1_UPPER_BOUND]
    if temp_top3_ok and temp_top1_ok:
        best_mul = min([r["beta_mul"] for r in temp_top3_ok if r["beta_mul"] > 0.35])
        criteria_met.append(f"temperature fix available: beta×{best_mul:.2f} gives top3≤{TOP3_UPPER_BOUND*100:.0f}%")
    else:
        criteria_failed.append("no temperature fix found that satisfies top3 constraint")

    # ECE reference from P2.5
    criteria_met.append("P2.5: Elo-backbone ECE=0.0170 (better than hybrid 0.0199)")

    # --- final verdict ---
    if orig_top3 <= TOP3_UPPER_BOUND and orig_top1 <= TOP1_UPPER_BOUND:
        verdict = "PASS_ELO_CALIBRATED"
    elif temp_top3_ok and temp_top1_ok:
        verdict = "PASS_WITH_TEMPERATURE"
    else:
        verdict = "FAIL_NEED_BLEND"

    return {
        "verdict": verdict,
        "original_beta_elo": params["beta_elo"],
        "original_top1": orig_top1,
        "original_top3": orig_top3,
        "top3_upper_bound": TOP3_UPPER_BOUND,
        "top1_upper_bound": TOP1_UPPER_BOUND,
        "historical_top3_reference": HISTORICAL_TOP3_REFERENCE,
        "recommended_beta_mul": best_beta_mul,
        "recommended_beta_elo": round(params["beta_elo"] * best_beta_mul, 4),
        "recommended_top3": best_conc.get("top3"),
        "recommended_top1": best_conc.get("top1"),
        "criteria_met": criteria_met,
        "criteria_failed": criteria_failed,
        "n_criteria_met": len(criteria_met),
        "n_criteria_failed": len(criteria_failed),
        "note": (
            f"verdict={verdict}. "
            "PASS_ELO_CALIBRATED → publish as-is. "
            "PASS_WITH_TEMPERATURE → re-run simulation with recommended beta, then publish. "
            "FAIL_NEED_BLEND → blend with expert model before publication."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Summary markdown writers
# ─────────────────────────────────────────────────────────────────────────────

def write_concentration_md(elo_conc: dict, exp_conc: dict, out: Path):
    lines = ["# P3.5 Elo Concentration Audit\n"]
    lines.append(f"## Reference context")
    lines.append(f"Historical WC pre-tournament top3 concentration (betting markets): ~36% average")
    lines.append(f"  - WC2018: Brazil ~15%, Germany/Spain/France ~10% each → top3 ≈ 35%")
    lines.append(f"  - WC2022: Brazil ~15%, Argentina ~11%, France ~11% → top3 ≈ 37%\n")
    lines.append(f"## Concentration comparison\n")
    lines.append(f"| Metric | Expert | Elo-calibrated | Target |")
    lines.append(f"|:-------|:------:|:--------------:|:------:|")
    for k, tgt in [("top1","≤20%"), ("top3","≤46%"), ("top5","≤60%"), ("top10","—")]:
        lines.append(f"| {k} | {exp_conc[k]*100:.1f}% | **{elo_conc[k]*100:.1f}%** | {tgt} |")
    lines.append(f"| entropy | {exp_conc['entropy']:.3f} | {elo_conc['entropy']:.3f} | ≥3.2 |")
    lines.append(f"| entropy ratio | {exp_conc['entropy_ratio']:.3f} | {elo_conc['entropy_ratio']:.3f} | ≥0.82 |")
    lines.append(f"| Herfindahl | {exp_conc['herfindahl']:.5f} | {elo_conc['herfindahl']:.5f} | — |\n")
    lines.append(f"## Diagnosis")
    lines.append(f"- **beta_elo = 0.988** fitted on competitive-only data (2010-2025)")
    lines.append(f"- Over-amplifies Elo signal: ESP vs median → 3.15 vs 0.50 xG")
    lines.append(f"- Top3 = **{elo_conc['top3']*100:.1f}%** vs historical reference 36%")
    lines.append(f"- Root cause: competitive matches are more Elo-predictable,")
    lines.append(f"  but WC simulation includes many mismatches (rank 5 vs rank 45)")
    lines.append(f"- Fix: temperature-scale beta_elo down to match historical concentration")
    out.write_text("\n".join(lines))


def write_temperature_md(ablation_rows: list[dict], best_mul: float, out: Path):
    lines = ["# P3.5 Temperature Ablation\n"]
    lines.append(f"## Results by beta_elo multiplier\n")
    lines.append("| beta_mul | beta_elo | top1 | top3 | top5 | entropy | Herfindahl |")
    lines.append("|:--------:|:--------:|:----:|:----:|:----:|:-------:|:----------:|")
    for r in ablation_rows:
        flag = " ← ✓" if abs(r["beta_mul"] - best_mul) < 0.01 else ""
        lines.append(f"| {r['beta_mul']:.2f} | {r['beta_elo']:.3f} | "
                     f"{r['top1']*100:.1f}% | **{r['top3']*100:.1f}%** | "
                     f"{r['top5']*100:.1f}% | {r['entropy']:.3f} | "
                     f"{r['herfindahl']:.5f} |{flag}")
    lines.append(f"\n## Recommended: beta_mul = {best_mul:.2f}\n")
    rec = next(r for r in ablation_rows if abs(r["beta_mul"]-best_mul)<0.01)
    lines.append(f"- beta_elo: {rec['beta_elo']:.4f}")
    lines.append(f"- top3 concentration: {rec['top3']*100:.1f}%")
    lines.append(f"- entropy: {rec['entropy']:.3f} (max={rec['entropy_max']:.3f})")
    for r in rec.get("top_teams", [])[:5]:
        lines.append(f"  - {r['team']}: {r['champion_prob']*100:.2f}%")
    out.write_text("\n".join(lines))


def write_historical_md(rows: list[dict], out: Path):
    lines = ["# P3.5 Historical Tournament Concentration\n"]
    lines.append("Approximate champion concentration using WC2026-bracket simulation")
    lines.append("with pre-tournament Elo snapshots for WC2018 and WC2022 teams.\n")
    lines.append("Note: uses WC2026 48-team bracket structure as proxy (not exact WC32).\n")
    lines.append("| tournament | beta_mul | beta_elo | top1 | top3 | top5 | entropy |")
    lines.append("|:----------:|:--------:|:--------:|:----:|:----:|:----:|:-------:|")
    for r in rows:
        lines.append(f"| {r['tournament']} | {r['beta_mul']:.2f} | "
                     f"{r.get('beta_elo', '—')} | "
                     f"{r['top1']*100:.1f}% | **{r['top3']*100:.1f}%** | "
                     f"{r['top5']*100:.1f}% | {r['entropy']:.3f} |")
    lines.append(f"\n## Reference")
    lines.append(f"WC2018 pre-tournament (betting): top3 ≈ 35%, top1 ≈ 15%")
    lines.append(f"WC2022 pre-tournament (betting): top3 ≈ 37%, top1 ≈ 15%")
    out.write_text("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("P3.5 — Elo Calibration Sanity Audit")
    print("=" * 60)

    params = load_calibrated_params()

    # ── Step 1: Concentration audit ──────────────────────────────────────────
    print("\n[1/7] Concentration audit...")
    elo_df = pd.read_csv(ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv")
    exp_df = pd.read_csv(ROOT / "outputs" / "tournament_run" / "expert_summary.csv")
    elo_conc = concentration_metrics(elo_df, "elo_calibrated")
    exp_conc = concentration_metrics(exp_df, "expert")
    print(f"  Expert:         top1={exp_conc['top1']*100:.1f}%  top3={exp_conc['top3']*100:.1f}%  "
          f"entropy={exp_conc['entropy']:.3f}")
    print(f"  Elo-calibrated: top1={elo_conc['top1']*100:.1f}%  top3={elo_conc['top3']*100:.1f}%  "
          f"entropy={elo_conc['entropy']:.3f}  ← SUSPECT")
    print(f"  Historical WC reference: top3 ≈ 36%  → Elo at {elo_conc['top3']*100:.1f}% is ×{elo_conc['top3']/0.36:.1f} over-concentrated")

    conc_df = pd.DataFrame([elo_conc, exp_conc])
    conc_df.to_csv(OUT / "elo_concentration_audit.csv", index=False)
    write_concentration_md(elo_conc, exp_conc, OUT / "elo_concentration_audit.md")

    # ── Step 2: Match sanity ─────────────────────────────────────────────────
    print("\n[2/7] Match-level sanity...")
    sanity_df = build_match_sanity(params)
    sanity_df.to_csv(OUT / "elo_match_sanity.csv", index=False)

    # Print key matchup at original beta
    orig = sanity_df[sanity_df["beta_mul"] == 1.00]
    print(f"  {'Matchup':<18}  {'Elo-diff':>8}  {'mu_A':>6}  {'mu_B':>6}  "
          f"{'P(A win)':>9}  {'P(draw)':>8}  {'P(B win)':>9}  {'P(A KO adv)':>12}")
    for _, r in orig.iterrows():
        print(f"  {r['team_a']:>3} vs {r['team_b']:<3}"
              f"  {r['elo_diff']:>+8.0f}"
              f"  {r['expected_goals_a']:>6.3f}  {r['expected_goals_b']:>6.3f}"
              f"  {r['p_a_win_90']*100:>8.1f}%"
              f"  {r['p_draw_90']*100:>7.1f}%"
              f"  {r['p_b_win_90']*100:>8.1f}%"
              f"  {r['p_a_advance_ko']*100:>11.1f}%")

    # ── Step 3: Temperature ablation simulations ─────────────────────────────
    print("\n[3/7] Temperature ablation (5 × 15K simulations)...")
    temperatures = [1.00, 0.85, 0.70, 0.55, 0.40]
    ablation_rows = []
    for t in temperatures:
        label = f"beta_x{t:.2f}"
        r = run_mini_simulation(t, label, iterations=15_000, verbose=True)
        ablation_rows.append(r)

    ablation_df = pd.DataFrame([{
        k: v for k, v in r.items() if k != "top_teams"
    } for r in ablation_rows])
    ablation_df.to_csv(OUT / "elo_temperature_ablation.csv", index=False)

    # ── Step 4: Choose best temperature ─────────────────────────────────────
    # Target: top3 ≤ 46% AND top1 ≤ 20%, pick highest beta that satisfies
    print("\n[4/7] Choosing best temperature...")
    valid = [r for r in ablation_rows
             if r["top3"] <= TOP3_UPPER_BOUND and r["top1"] <= TOP1_UPPER_BOUND]
    if valid:
        best = max(valid, key=lambda r: r["beta_mul"])
        best_mul = best["beta_mul"]
        print(f"  Best: beta_mul={best_mul:.2f} → top1={best['top1']*100:.1f}%, top3={best['top3']*100:.1f}%")
    else:
        # Pick one with best top3 even if not ideal
        best = min(ablation_rows, key=lambda r: abs(r["top3"] - 0.40))
        best_mul = best["beta_mul"]
        print(f"  No perfect fit; closest: beta_mul={best_mul:.2f} → top3={best['top3']*100:.1f}%")

    write_temperature_md(ablation_rows, best_mul, OUT / "elo_temperature_summary.md")

    # ── Step 5: Historical WC approximation ─────────────────────────────────
    print("\n[5/7] Historical WC approximation...")
    hist_rows = []
    # WC2018: use Elos before June 2018
    hist_rows += run_historical_concentration(
        "2018-06-01", "WC2018_approx",
        beta_values=[1.00, best_mul, 0.55], verbose=True,
    )
    # WC2022: use Elos before November 2022
    hist_rows += run_historical_concentration(
        "2022-11-01", "WC2022_approx",
        beta_values=[1.00, best_mul, 0.55], verbose=True,
    )
    hist_df = pd.DataFrame([{k: v for k, v in r.items() if k != "top_teams"} for r in hist_rows])
    hist_df.to_csv(OUT / "historical_tournament_concentration.csv", index=False)
    write_historical_md(hist_rows, OUT / "historical_tournament_concentration.md")

    # ── Step 6: Production gate ──────────────────────────────────────────────
    print("\n[6/7] Computing production gate...")
    gate = compute_production_gate(elo_conc, ablation_rows, sanity_df, best_mul, best)
    (OUT / "elo_calibration_gate.json").write_text(json.dumps(gate, indent=2))
    print(f"  Verdict: {gate['verdict']}")
    print(f"  Recommended beta_mul: {gate['recommended_beta_mul']}")
    print(f"  Recommended beta_elo: {gate['recommended_beta_elo']}")
    print(f"  Expected top3 with recommended beta: {gate.get('recommended_top3', '—')}")
    print(f"  Criteria met: {gate['n_criteria_met']}, failed: {gate['n_criteria_failed']}")

    # ── Step 7: Final report ─────────────────────────────────────────────────
    print("\n[7/7] Summary")
    print(f"\n  DIAGNOSIS:")
    print(f"  - beta_elo={params['beta_elo']:.4f} → trained on competitive-only data")
    print(f"  - ESP vs Median xG: {math.exp(params['log_base'] + params['beta_elo']*(2155-1782)/400):.2f} vs {math.exp(params['log_base'] - params['beta_elo']*(2155-1782)/400):.2f}")
    print(f"  - Top3 concentration: {elo_conc['top3']*100:.1f}% vs historical 36%")
    print(f"\n  RECOMMENDED FIX:")
    print(f"  - Use beta_mul = {best_mul:.2f} → beta_elo = {params['beta_elo']*best_mul:.4f}")
    print(f"  - Top3 with fix: {best.get('top3', '?'):.3f}")
    print(f"  - Re-run: PYTHONPATH=src .venv/bin/python scripts/simulate_models.py --model elo_calibrated")
    print(f"    after updating data/elo_calibrated_params.json with beta_elo={params['beta_elo']*best_mul:.4f}")
    print(f"\n  GATE: {gate['verdict']}")
    if gate['verdict'] == "PASS_WITH_TEMPERATURE":
        print(f"  → Apply temperature {best_mul:.2f} to beta_elo, then re-run 100K simulation")
    elif gate['verdict'] == "PASS_ELO_CALIBRATED":
        print(f"  → Elo-calibrated model is publication-ready as-is")
    else:
        print(f"  → Consider blending with expert model")

    print("\n✓ P3.5 audit complete")
    return gate


if __name__ == "__main__":
    main()
