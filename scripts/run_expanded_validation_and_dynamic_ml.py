#!/usr/bin/env python3
"""Batch B + C — expanded tournament validation + fixed-vs-dynamic ML weighting.

B: add WC2010 & WC2014 to the leak-free walk-forward harness. Each team name is checked
   against the pre-cutoff rolling-Elo history; a tournament with unresolved teams (which
   would silently get the 1500 default) is REJECTED with reason.
C: on every cleanly-reconstructed tournament, compare Elo-only vs ML@0.20 fixed vs
   ML@0.20 dynamic (weight decays with Elo gap). Adopt dynamic ONLY if it improves
   robustness (lower worst-case upset regret without losing aggregate Brier).
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
N = 30_000
SEED = 20260613

WC2010 = {
    "name": "FIFA World Cup 2010", "cutoff": "2010-06-11",
    "groups": {
        "A": ["South Africa", "Mexico", "Uruguay", "France"],
        "B": ["Argentina", "Nigeria", "South Korea", "Greece"],
        "C": ["England", "United States", "Algeria", "Slovenia"],
        "D": ["Germany", "Australia", "Serbia", "Ghana"],
        "E": ["Netherlands", "Denmark", "Japan", "Cameroon"],
        "F": ["Italy", "Paraguay", "New Zealand", "Slovakia"],
        "G": ["Brazil", "North Korea", "Ivory Coast", "Portugal"],
        "H": ["Spain", "Switzerland", "Honduras", "Chile"],
    },
    "group_survivors": {"Uruguay", "Mexico", "Argentina", "South Korea", "United States",
                        "England", "Germany", "Ghana", "Netherlands", "Japan", "Paraguay",
                        "Slovakia", "Brazil", "Portugal", "Spain", "Chile"},
    "quarterfinalists": {"Uruguay", "Ghana", "Netherlands", "Brazil", "Argentina", "Germany",
                         "Paraguay", "Spain"},
    "semifinalists": {"Uruguay", "Netherlands", "Germany", "Spain"},
    "champion": {"Spain"},
}
WC2014 = {
    "name": "FIFA World Cup 2014", "cutoff": "2014-06-12",
    "groups": {
        "A": ["Brazil", "Croatia", "Mexico", "Cameroon"],
        "B": ["Spain", "Netherlands", "Chile", "Australia"],
        "C": ["Colombia", "Greece", "Ivory Coast", "Japan"],
        "D": ["Uruguay", "Costa Rica", "England", "Italy"],
        "E": ["Switzerland", "Ecuador", "France", "Honduras"],
        "F": ["Argentina", "Bosnia and Herzegovina", "Iran", "Nigeria"],
        "G": ["Germany", "Portugal", "Ghana", "United States"],
        "H": ["Belgium", "Algeria", "Russia", "South Korea"],
    },
    "group_survivors": {"Brazil", "Mexico", "Netherlands", "Chile", "Colombia", "Greece",
                        "Costa Rica", "Uruguay", "France", "Switzerland", "Argentina",
                        "Nigeria", "Germany", "United States", "Belgium", "Algeria"},
    "quarterfinalists": {"Brazil", "Colombia", "France", "Germany", "Netherlands",
                         "Costa Rica", "Argentina", "Belgium"},
    "semifinalists": {"Brazil", "Germany", "Netherlands", "Argentina"},
    "champion": {"Germany"},
}
ALL = [WC2010, WC2014, WC2018, WC2022]


def _entropy(p): return -sum(x * math.log(x) for x in p.values() if x > 0)


def reconstruct(tournament):
    """Return (engine, teams, codes, pre_elos, unresolved). Rejects if unresolved teams."""
    df = pd.read_csv(RESULTS_CSV)
    df = df[df.date < tournament["cutoff"]].copy()
    df = df[df.home_score.notna() & df.away_score.notna()]
    df = df.rename(columns={"home_score": "home_goals", "away_score": "away_goals"})
    engine = RollingEloEngine(); engine.fit(df)
    names = {n for g in tournament["groups"].values() for n in g}
    # a team is resolved if it has >=5 matches of history before the cutoff
    unresolved = [n for n in names if len(engine.history.get(n, [])) < 5]
    pre_elos = {NAME_TO_CODE.get(n, n): round(engine.get_elo(n), 1) for n in names}
    teams_df = pd.read_csv(ROOT / "data" / "teams.csv").set_index("code")
    teams = {}
    for n in names:
        c = NAME_TO_CODE.get(n, n)
        pen = float(teams_df.loc[c, "penalties"]) if c in teams_df.index else 75.0
        teams[c] = _make_team(c, pre_elos.get(c, 1500.0), pen)
    return engine, teams, set(teams), pre_elos, unresolved


def score(tournament, teams, codes, model, n, seed):
    rng = np.random.default_rng(seed)
    counts = {t: {"group": 0, "r16": 0, "qf": 0, "sf": 0, "champion": 0} for t in teams}
    for _ in range(n):
        for t, st in _simulate_tournament(tournament, teams, model, rng).items():
            for s, v in st.items():
                counts[t][s] += v
    probs = {t: {s: counts[t][s] / n for s in counts[t]} for t in teams}
    nm = lambda S: {NAME_TO_CODE.get(x, x) for x in S}
    champ = {t: probs[t]["champion"] for t in teams}
    actual = NAME_TO_CODE.get(list(tournament["champion"])[0], list(tournament["champion"])[0])
    ranked = sorted(champ.items(), key=lambda x: -x[1])
    rank = next((i + 1 for i, (t, _) in enumerate(ranked) if t == actual), 99)
    return {"champ_brier": _brier(champ, nm(tournament["champion"]), codes),
            "sf_brier": _brier({t: probs[t]["sf"] for t in teams}, nm(tournament["semifinalists"]), codes),
            "actual_rank": rank, "actual_prob": round(champ.get(actual, 0.0), 4),
            "entropy": round(_entropy(champ), 4), "top1": round(ranked[0][1], 4),
            "top1_team": ranked[0][0], "actual_champ": actual}


def main(n=N, seed=SEED):
    t0 = time.monotonic(); NOW = datetime.now(timezone.utc).isoformat()
    base_params = load_calibrated_params(); cfg = load_config()
    accepted, rejected = [], []
    recon = {}
    for tour in ALL:
        _, teams, codes, pre_elos, unresolved = reconstruct(tour)
        if unresolved:
            rejected.append({"tournament": tour["name"], "reason": f"unresolved teams (no pre-cutoff Elo history): {unresolved}"})
            print(f"REJECT {tour['name']}: unresolved {unresolved}")
            continue
        accepted.append(tour); recon[tour["name"]] = (teams, codes, pre_elos)
        print(f"ACCEPT {tour['name']} ({len(codes)} teams resolved)")

    # B + C: score Elo-only / fixed / dynamic on each accepted tournament
    rows = []
    for tour in accepted:
        teams, codes, pre_elos = recon[tour["name"]]
        clf = train_logistic_until(tour["cutoff"])
        params = deepcopy(base_params); params["team_elos"] = pre_elos
        configs = [("elo_only", 0.0, "fixed"), ("fixed_0.20", 0.20, "fixed"), ("dynamic_0.20", 0.20, "dynamic")]
        for label, w, mode in configs:
            model = CalibratedEloMatchModel(config=cfg, params=params, use_ml=False)
            if w > 0:
                model.set_ml_ensemble(clf, w, mode=mode, gap_scale=300.0)
            s = score(tour, teams, codes, model, n, seed)
            rows.append({"tournament": tour["name"], "config": label, **s})
            print(f"  {tour['name'][-4:]} {label:13s}: champ_brier={s['champ_brier']:.5f} "
                  f"entropy={s['entropy']:.3f} top1={s['top1']:.3f} actual={s['actual_champ']} rank#{s['actual_rank']}")

    df = pd.DataFrame(rows)
    # Aggregate by config
    agg = df.groupby("config").agg(mean_champ_brier=("champ_brier", "mean"),
                                   mean_sf_brier=("sf_brier", "mean"),
                                   mean_entropy=("entropy", "mean")).reset_index()
    # Worst-case regret vs elo_only per config
    regret = {}
    for label in ("fixed_0.20", "dynamic_0.20"):
        worst = 0.0
        for tour in accepted:
            b = df[(df.tournament == tour["name"]) & (df.config == label)]["champ_brier"].iloc[0]
            b0 = df[(df.tournament == tour["name"]) & (df.config == "elo_only")]["champ_brier"].iloc[0]
            worst = max(worst, (b - b0) / b0)
        regret[label] = round(worst, 4)
    bri = {r["config"]: r["mean_champ_brier"] for _, r in agg.iterrows()}

    # Decision: adopt dynamic only if it reduces worst-case regret AND aggregate Brier not worse
    adopt_dynamic = (regret["dynamic_0.20"] < regret["fixed_0.20"] and
                     bri["dynamic_0.20"] <= bri["fixed_0.20"] * 1.002)

    out = {
        "generated_at": NOW, "n_sims": n, "seed": seed,
        "accepted_tournaments": [t["name"] for t in accepted],
        "rejected_tournaments": rejected,
        "aggregate_by_config": agg.round(6).to_dict("records"),
        "worst_case_regret_vs_elo": regret,
        "fixed_vs_dynamic_decision": "ADOPT_DYNAMIC" if adopt_dynamic else "KEEP_FIXED",
        "decision_rule": "adopt dynamic only if it lowers worst-case upset regret AND aggregate champ Brier within 0.2% of fixed",
        "per_tournament": df.round(6).to_dict("records"),
        "honest_caveats": [
            "Sample is now 4 World Cups (2010/2014/2018/2022) — still small; EUROs/Copa not added (32-team bracket harness only).",
            "beta_elo held fixed (full-history fit) -> absolute Brier mildly optimistic; config comparison valid.",
            "ML retrained per cutoff (leak-free).",
        ],
    }
    Path(ROOT / "outputs" / "audit" / "expanded_tournament_validation.json").write_text(json.dumps(out, indent=2))
    Path(ROOT / "outputs" / "audit" / "upset_robust_ml_weighting.json").write_text(json.dumps({
        "generated_at": NOW, "decision": out["fixed_vs_dynamic_decision"],
        "worst_case_regret_vs_elo": regret, "aggregate_brier": {k: round(v, 6) for k, v in bri.items()},
        "decision_rule": out["decision_rule"], "gap_scale": 300.0,
        "per_tournament": df[df.config.isin(["fixed_0.20", "dynamic_0.20", "elo_only"])].round(6).to_dict("records"),
    }, indent=2))

    # Markdown
    ml = ["# Expanded Validation + Upset-Robust ML (Batch B + C)", "",
          f"Generated {NOW[:19]} · N={n:,}/config", "",
          f"## Accepted: {', '.join(t['name'] for t in accepted)}",
          f"## Rejected: {[r['tournament'] for r in rejected] or 'none'}", "",
          "## Aggregate champion Brier by config (4 WCs)", "",
          "| Config | Champ Brier | SF Brier | Entropy | Worst-case regret |", "|---|---|---|---|---|"]
    for r in agg.round(5).itertuples():
        rg = regret.get(r.config, "—")
        ml.append(f"| {r.config} | {r.mean_champ_brier} | {r.mean_sf_brier} | {r.mean_entropy} | {rg} |")
    ml += ["", f"**Decision: {out['fixed_vs_dynamic_decision']}** — {out['decision_rule']}", "",
           "## Per-tournament champion Brier", "",
           "| Tournament | elo_only | fixed_0.20 | dynamic_0.20 | actual champ |", "|---|---|---|---|---|"]
    for tour in accepted:
        sub = {r["config"]: r for r in df[df.tournament == tour["name"]].to_dict("records")}
        ac = sub["elo_only"]["actual_champ"]
        ml.append(f"| {tour['name'][-4:]} | {sub['elo_only']['champ_brier']:.5f} | "
                  f"{sub['fixed_0.20']['champ_brier']:.5f} | {sub['dynamic_0.20']['champ_brier']:.5f} | {ac} |")
    ml += ["", "## Honest caveats", ""] + [f"- {c}" for c in out["honest_caveats"]]
    txt = "\n".join(ml)
    Path(ROOT / "outputs" / "audit" / "expanded_tournament_validation.md").write_text(txt)
    Path(ROOT / "outputs" / "audit" / "upset_robust_ml_weighting.md").write_text(txt)

    print(f"\n=== DECISION: {out['fixed_vs_dynamic_decision']} ===")
    print(f"regret fixed={regret['fixed_0.20']} dynamic={regret['dynamic_0.20']} | "
          f"brier fixed={bri['fixed_0.20']:.5f} dynamic={bri['dynamic_0.20']:.5f}")
    print(f"Done in {time.monotonic()-t0:.0f}s")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=N)
    main(n=ap.parse_args().n)
