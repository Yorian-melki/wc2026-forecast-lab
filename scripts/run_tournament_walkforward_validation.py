#!/usr/bin/env python3
"""Batch A — clean walk-forward tournament validation (WC2018 + WC2022).

For each tournament:
  - Rolling Elo computed ONLY from pre-cutoff matches (leak-free team strengths).
  - ML 1X2 model trained ONLY on matches before the cutoff (leak-free — the model
    never sees the tournament it is scored on). This fixes the leakage in the prior
    backtest (the disk ML model was trained on data <=2018, which included WC2018).
  - Sweep ML ensemble weight in {0.0, 0.1, 0.2, 0.3, 0.5} with common random numbers
    (same seed) so the weight comparison is low-variance.

Metrics per (tournament, weight): champion / SF / group Brier, actual-champion rank,
top-3/5/10 coverage, champion-distribution entropy (concentration), favorite top-1 prob.

Honest scope: beta_elo is held FIXED across all weights, so the *relative* weight
comparison is internally valid even though absolute Brier is mildly optimistic (beta
fit on full history). Two tournaments is a small sample — decision is robustness-biased.
"""
from __future__ import annotations

import json
import math
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
from wc2026.data_loader import load_config
from wc2026.ml.train_match_model import train_logistic_until

from run_wc_historical_backtest import (
    WC2018, WC2022, NAME_TO_CODE, _make_team, _simulate_tournament, _brier,
)

RESULTS_CSV = ROOT / "data" / "external" / "international_results" / "results.csv"
WEIGHTS = [0.0, 0.10, 0.20, 0.30, 0.50]
N = 30_000


def _entropy(probs: dict) -> float:
    return -sum(p * math.log(p) for p in probs.values() if p > 0)


def _pre_tournament(tournament):
    df = pd.read_csv(RESULTS_CSV)
    df = df[df.date < tournament["cutoff"]].copy()
    df = df[df.home_score.notna() & df.away_score.notna()]
    df = df.rename(columns={"home_score": "home_goals", "away_score": "away_goals"})
    engine = RollingEloEngine()
    engine.fit(df)
    names = {n for g in tournament["groups"].values() for n in g}
    pre_elos = {NAME_TO_CODE.get(n, n): round(engine.get_elo(n), 1) for n in names}
    codes = set(pre_elos.keys())
    teams_df = pd.read_csv(ROOT / "data" / "teams.csv").set_index("code")
    teams = {}
    for c in codes:
        pen = float(teams_df.loc[c, "penalties"]) if c in teams_df.index else 75.0
        teams[c] = _make_team(c, pre_elos.get(c, 1500.0), pen)
    return pre_elos, teams, codes


def _score(tournament, teams, codes, model, n, seed):
    rng = np.random.default_rng(seed)
    counts = {t: {"group": 0, "r16": 0, "qf": 0, "sf": 0, "champion": 0} for t in teams}
    for _ in range(n):
        res = _simulate_tournament(tournament, teams, model, rng)
        for t, st in res.items():
            for s, v in st.items():
                counts[t][s] += v
    probs = {t: {s: counts[t][s] / n for s in counts[t]} for t in teams}
    nm = lambda S: {NAME_TO_CODE.get(x, x) for x in S}
    champ = {t: probs[t]["champion"] for t in teams}
    actual = NAME_TO_CODE.get(list(tournament["champion"])[0], list(tournament["champion"])[0])
    ranked = sorted(champ.items(), key=lambda x: -x[1])
    rank = next((i + 1 for i, (t, _) in enumerate(ranked) if t == actual), 99)
    return {
        "champ_brier": round(_brier(champ, nm(tournament["champion"]), codes), 6),
        "group_brier": round(_brier({t: probs[t]["group"] for t in teams}, nm(tournament["group_survivors"]), codes), 6),
        "sf_brier": round(_brier({t: probs[t]["sf"] for t in teams}, nm(tournament["semifinalists"]), codes), 6),
        "qf_brier": round(_brier({t: probs[t]["qf"] for t in teams}, nm(tournament["quarterfinalists"]), codes), 6),
        "actual_champ": actual, "actual_champ_prob": round(champ.get(actual, 0.0), 4),
        "actual_champ_rank": rank,
        "top3_cover": int(rank <= 3), "top5_cover": int(rank <= 5), "top10_cover": int(rank <= 10),
        "champ_entropy": round(_entropy(champ), 4),
        "top1_prob": round(ranked[0][1], 4), "top1_team": ranked[0][0],
        "top5": [{"team": t, "p": round(p, 4)} for t, p in ranked[:5]],
    }


def main(n=N, seed=20260613):
    t0 = time.monotonic()
    NOW = datetime.now(timezone.utc).isoformat()
    base_params = load_calibrated_params()
    cfg = load_config()
    rows = []
    per_tourn = {}

    for tournament in (WC2018, WC2022):
        name = tournament["name"]
        print(f"\n=== {name} (cutoff {tournament['cutoff']}) ===")
        pre_elos, teams, codes = _pre_tournament(tournament)
        print(f"  training leak-free ML (matches < {tournament['cutoff']}) ...")
        clf = train_logistic_until(tournament["cutoff"])
        params = deepcopy(base_params); params["team_elos"] = pre_elos
        n_teams = len(codes)
        random_brier = round((1.0 / n_teams) ** 2 * (n_teams - 1) + (1 - 1.0 / n_teams) ** 2, 6)
        per_tourn[name] = {"cutoff": tournament["cutoff"], "n_teams": n_teams,
                           "random_champ_brier": random_brier, "by_weight": {}}
        for w in WEIGHTS:
            model = CalibratedEloMatchModel(config=cfg, params=params, use_ml=False)
            if w > 0:
                model.set_ml_ensemble(clf, w)
            s = _score(tournament, teams, codes, model, n, seed)  # CRN: same seed across weights
            s["weight"] = w
            per_tourn[name]["by_weight"][f"{w:.2f}"] = s
            rows.append({"tournament": name, "ml_weight": w, **{k: v for k, v in s.items()
                         if k in ("champ_brier", "sf_brier", "qf_brier", "group_brier",
                                  "actual_champ_prob", "actual_champ_rank", "top3_cover",
                                  "top5_cover", "champ_entropy", "top1_prob", "top1_team")}})
            print(f"  w={w:.2f}: champ_brier={s['champ_brier']:.5f} sf={s['sf_brier']:.5f} "
                  f"entropy={s['champ_entropy']:.3f} top1={s['top1_prob']:.3f}({s['top1_team']}) "
                  f"actual={s['actual_champ']} rank#{s['actual_champ_rank']} p={s['actual_champ_prob']:.3f}")

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "audit" / "ml_weight_sensitivity.csv", index=False)

    # Aggregate: mean champ Brier per weight across both tournaments (leak-free)
    agg = df.groupby("ml_weight").agg(
        mean_champ_brier=("champ_brier", "mean"),
        mean_sf_brier=("sf_brier", "mean"),
        mean_group_brier=("group_brier", "mean"),
        mean_entropy=("champ_entropy", "mean"),
        mean_top1=("top1_prob", "mean"),
    ).reset_index()
    best_w = float(agg.loc[agg["mean_champ_brier"].idxmin(), "ml_weight"])
    best_brier = float(agg["mean_champ_brier"].min())
    elo_brier = float(agg.loc[agg["ml_weight"] == 0.0, "mean_champ_brier"].iloc[0])

    # Worst-case per-tournament regret vs that tournament's own Elo-only baseline.
    # This catches the WC2018-style case where ML hurts on an upset winner even if the
    # aggregate (favorite-driven) looks good.
    regret = {}
    for w in WEIGHTS:
        worst = 0.0
        for name, d in per_tourn.items():
            b_w = d["by_weight"][f"{w:.2f}"]["champ_brier"]
            b0 = d["by_weight"]["0.00"]["champ_brier"]
            worst = max(worst, (b_w - b0) / b0)
        regret[w] = worst
    best_improvement = max(elo_brier - best_brier, 0.0)

    # Robustness-first rule: among weights that (a) improve aggregate Brier vs Elo-only,
    # (b) capture >=60% of the best achievable improvement, and (c) keep worst-case
    # per-tournament regret <= 3%, pick the SMALLEST such weight. If none qualify, the
    # tournament-level evidence does not robustly support ML -> weight 0 (diagnostic only
    # at tournament level, even though match-level ML is accepted).
    eligible = []
    for w in WEIGHTS:
        if w == 0.0:
            continue
        b = float(agg.loc[agg["ml_weight"] == w, "mean_champ_brier"].iloc[0])
        improves = (elo_brier - b) >= 0.60 * best_improvement and b < elo_brier
        safe = regret[w] <= 0.03
        if improves and safe:
            eligible.append(w)
    chosen_w = min(eligible) if eligible else 0.0
    chosen_brier = float(agg.loc[agg["ml_weight"] == chosen_w, "mean_champ_brier"].iloc[0])

    ent_elo = float(agg.loc[agg["ml_weight"] == 0.0, "mean_entropy"].iloc[0])
    ent_chosen = float(agg.loc[agg["ml_weight"] == chosen_w, "mean_entropy"].iloc[0])
    overconcentrated = regret.get(best_w, 0.0) > 0.03  # best-by-Brier weight hurts an upset tournament

    decision = {
        "generated_at": NOW, "n_sims_per_config": n, "seed": seed,
        "weights_tested": WEIGHTS,
        "aggregate_by_weight": agg.round(6).to_dict(orient="records"),
        "elo_only_champ_brier": round(elo_brier, 6),
        "best_weight_by_brier": best_w, "best_brier": round(best_brier, 6),
        "worst_case_regret_by_weight": {f"{w:.2f}": round(regret[w], 4) for w in WEIGHTS},
        "chosen_weight": chosen_w,
        "chosen_rule": "smallest ML weight that improves aggregate champ Brier, captures >=60% of best improvement, AND keeps worst-case per-tournament regret <=3%; else 0 (ML tournament-diagnostic-only)",
        "chosen_champ_brier": round(chosen_brier, 6),
        "improvement_vs_elo_only_pct": round((elo_brier - chosen_brier) / elo_brier * 100, 2) if chosen_w > 0 else 0.0,
        "tournament_disagreement": "ML helps when the favorite wins (WC2022) and hurts on an upset winner (WC2018). 2-tournament sample.",
        "overconcentration_flag": bool(overconcentrated),
        "entropy_elo_only": round(ent_elo, 4), "entropy_chosen": round(ent_chosen, 4),
        "leakage_notes": [
            "Team Elos: leak-free (pre-cutoff rolling Elo).",
            "ML model: leak-free (retrained per cutoff; never sees the test tournament).",
            "beta_elo: FIXED across weights (full-history fit) -> absolute Brier mildly optimistic, but weight comparison valid.",
            "Sample = 2 tournaments. Treat as directional evidence, not proof.",
        ],
        "per_tournament": per_tourn,
    }
    Path(ROOT / "outputs" / "audit" / "tournament_walkforward_validation.json").write_text(json.dumps(decision, indent=2))

    # Markdown
    lines = ["# Tournament Walk-Forward Validation (WC2018 + WC2022)", "",
             f"Generated {NOW[:19]} · N={n:,}/config · seed={seed} (common random numbers across weights)", "",
             "## Aggregate champion Brier by ML weight (mean of WC2018, WC2022)", "",
             "| ML weight | Champ Brier ↓ | SF Brier | Group Brier | Entropy | Mean top-1 |",
             "|---|---|---|---|---|---|"]
    for r in agg.round(5).itertuples():
        mark = " ←chosen" if r.ml_weight == chosen_w else ""
        lines.append(f"| {r.ml_weight:.2f}{mark} | {r.mean_champ_brier} | {r.mean_sf_brier} | "
                     f"{r.mean_group_brier} | {r.mean_entropy} | {r.mean_top1} |")
    lines += ["",
              f"**Chosen ML weight: {chosen_w:.2f}** ({decision['chosen_rule']}).",
              f"Champion Brier {chosen_brier:.5f} vs Elo-only {elo_brier:.5f} "
              f"({decision['improvement_vs_elo_only_pct']:+.2f}%). "
              f"Overconcentration flag: **{overconcentrated}**.", "",
              "## Per-tournament detail", ""]
    for name, d in per_tourn.items():
        lines.append(f"### {name} (random champ Brier {d['random_champ_brier']:.4f})")
        lines.append("| weight | champ Brier | actual champ | rank | p | entropy | top-1 |")
        lines.append("|---|---|---|---|---|---|---|")
        for wk, s in d["by_weight"].items():
            lines.append(f"| {wk} | {s['champ_brier']:.5f} | {s['actual_champ']} | "
                         f"#{s['actual_champ_rank']} | {s['actual_champ_prob']:.3f} | "
                         f"{s['champ_entropy']:.3f} | {s['top1_prob']:.3f} {s['top1_team']} |")
        lines.append("")
    lines += ["## Honest notes", ""] + [f"- {x}" for x in decision["leakage_notes"]]
    Path(ROOT / "outputs" / "audit" / "tournament_walkforward_validation.md").write_text("\n".join(lines))

    print(f"\n=== DECISION ===")
    print(f"Elo-only champ Brier: {elo_brier:.5f}")
    print(f"Best weight by Brier: {best_w:.2f} ({best_brier:.5f})")
    print(f"CHOSEN weight (robust): {chosen_w:.2f} ({chosen_brier:.5f}, {decision['improvement_vs_elo_only_pct']:+.2f}% vs Elo)")
    print(f"Overconcentration flag: {overconcentrated}")
    print(f"Done in {time.monotonic()-t0:.0f}s")
    return decision


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N)
    ap.add_argument("--seed", type=int, default=20260613)
    args = ap.parse_args()
    main(n=args.n, seed=args.seed)
