#!/usr/bin/env python3
"""Backtest the Elo→Dixon-Coles score model on PAST competitions, compare credibility to WC2026.

Uses rolling pre-match Elos from martj42 results.csv and the SAME RPS / exact-score scoring as
the live scorecard. The scoreline is built directly from the frozen production params
(beta_elo / log_base / rho) so it works for any historical teams — the Elo-DC CORE only (the ML
layer is WC-2026-feature-specific and not applied here). Honest by construction: RPS shown next
to the same-matches coin-flip baseline. Writes outputs/audit/competition_backtest.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from wc2026.calibration.rolling_elo import RollingEloEngine          # noqa: E402
from wc2026.scorecard import _rps_ordered, _wdl_from_flat            # noqa: E402

P = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
BETA, LOGB, RHO = float(P["beta_elo"]), float(P["log_base"]), float(P["rho"])
MAXG = 8
_LF = np.array([math.lgamma(i + 1) for i in range(MAXG + 1)])


def dc_flat(elo_a: float, elo_b: float):
    d = (elo_a - elo_b) / 400.0
    mu_a = min(max(math.exp(LOGB + BETA * d), 0.15), 3.6)
    mu_b = min(max(math.exp(LOGB - BETA * d), 0.15), 3.6)
    g = MAXG + 1
    k = np.arange(g)
    pa = np.exp(k * math.log(mu_a) - mu_a - _LF)
    pb = np.exp(k * math.log(mu_b) - mu_b - _LF)
    j = np.outer(pa, pb)
    j[0, 0] *= max(1 - mu_a * mu_b * RHO, 1e-9)
    j[1, 0] *= max(1 + mu_b * RHO, 1e-9)
    j[0, 1] *= max(1 + mu_a * RHO, 1e-9)
    j[1, 1] *= max(1 - RHO, 1e-9)
    f = j.ravel()
    return f / f.sum(), g


def score_competition(matches: pd.DataFrame, eng: RollingEloEngine):
    rows = []
    for _, m in matches.iterrows():
        hg, ag = int(m["home_score"]), int(m["away_score"])
        eh = eng.get_elo(m["home_team"], before_date=m["date"])
        ea = eng.get_elo(m["away_team"], before_date=m["date"])
        flat, g = dc_flat(eh, ea)
        idx = min(hg, g - 1) * g + min(ag, g - 1)
        rank = int(np.where(np.argsort(flat)[::-1] == idx)[0][0]) + 1
        pw = _wdl_from_flat(flat, g)
        out = 0 if hg > ag else (1 if hg == ag else 2)
        rows.append({"p": float(flat[idx]), "rank": rank, "ok": int(np.argmax(pw) == out),
                     "rps": _rps_ordered(pw, out), "rpsu": _rps_ordered((1 / 3, 1 / 3, 1 / 3), out)})
    n = len(rows)
    if not n:
        return None
    return {"n": n,
            "outcome_accuracy": round(sum(r["ok"] for r in rows) / n, 4),
            "mean_rps": round(float(np.mean([r["rps"] for r in rows])), 4),
            "rps_uniform": round(float(np.mean([r["rpsu"] for r in rows])), 4),
            "exact_top1": round(sum(r["rank"] == 1 for r in rows) / n, 4),
            "exact_top3": round(sum(r["rank"] <= 3 for r in rows) / n, 4),
            "mean_prob_actual": round(float(np.mean([r["p"] for r in rows])), 4),
            "mean_rank": round(float(np.mean([r["rank"] for r in rows])), 2)}


def main() -> int:
    df = pd.read_csv(ROOT / "data" / "external" / "international_results" / "results.csv")
    df = df.dropna(subset=["home_score", "away_score"])
    eng = RollingEloEngine()
    eng.fit(df)
    df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
    comps = ["FIFA World Cup", "Copa América", "African Cup of Nations",
             "UEFA Nations League", "Friendly"]
    out = {"since": 2010, "model": "Elo->Dixon-Coles core (no ML)", "competitions": {}}
    for c in comps:
        sub = df[(df["tournament"] == c) & (df["year"] >= 2010)]
        r = score_competition(sub, eng)
        if r:
            out["competitions"][c] = r
            print(f"{c:28s} n={r['n']:5d} acc={r['outcome_accuracy']:.3f} "
                  f"rps={r['mean_rps']:.4f} (unif {r['rps_uniform']:.4f}) top3={r['exact_top3']:.3f}")
    (ROOT / "outputs" / "audit" / "competition_backtest.json").write_text(json.dumps(out, indent=2))
    print("saved → outputs/audit/competition_backtest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
