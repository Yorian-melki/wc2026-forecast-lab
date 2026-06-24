"""Phase 2B — OFFLINE tail-overdispersion diagnostic (READ-ONLY w.r.t. production).

Compares the production independent-Poisson + Dixon-Coles scoreline distribution against
Negative-Binomial (fat-tailed) variants over a grid of dispersion `r` and mu-cap, scored on the
deterministic in-repo historical dataset (martj42 competitive 2010-2025).

It reads production params/data READ-ONLY and builds candidate distributions in a scratch module.
It does NOT touch app.py, calibrated_elo_model.py, scorecard.py, data/, or configs/. It writes only
to outputs/experiments/2B_tail_dispersion/. Nothing here is imported by the live app.

Run:  PYTHONPATH=src .venv/bin/python scripts/exp_tail_dispersion.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.nb_scoreline import negbin_dc_flat, wdl_from_flat

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "data" / "elo_calibrated_params.json"
OUT_DIR = ROOT / "outputs" / "experiments" / "2B_tail_dispersion"

G = 8                       # dc_max_goals(7) + 1 — matches production grid
MU_LOW = 0.15               # production live lower clamp
R_GRID = [2.0, 4.0, 6.0, 8.0, 12.0, 20.0, float("inf")]   # inf == Poisson baseline
CAP_GRID = [3.60, 4.5, 6.0, 8.0]                            # 3.60 == production cap
BASELINE = ("inf", 3.60)    # (r, cap) treated as the live baseline

# materiality thresholds (pre-registered)
REL_RANK_IMPROVE = 0.10     # high-total/blowout mean-rank must drop >= 10% relative
ABS_RANK_IMPROVE = 0.5      # ...and >= 0.5 absolute
REL_GUARD_DEGRADE = 0.005   # Brier/RPS/NLL not worse by > 0.5% relative
ABS_ACC_DEGRADE = 0.005     # outcome accuracy not lower by > 0.5pp
ABS_ECE_DEGRADE = 0.005     # ECE not worse by > 0.005 absolute


def build_match_features() -> pd.DataFrame:
    """Deterministic per-match (mu_a, mu_b, goals, buckets) using the SAME path as the MLE fit."""
    params = json.loads(PARAMS_PATH.read_text())
    log_base, beta = float(params["log_base"]), float(params["beta_elo"])
    rho = float(params["rho"])

    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine()
    elo.fit(df)

    rows = []
    for h, a, d, n, hg, ag in zip(df["home_team"], df["away_team"], df["date"],
                                  df["neutral"], df["home_goals"], df["away_goals"]):
        elo_diff = (elo.get_elo(h, before_date=d) + (0.0 if n else 100.0)
                    - elo.get_elo(a, before_date=d)) / 400.0
        rows.append((log_base + beta * elo_diff, log_base - beta * elo_diff, int(hg), int(ag)))
    feat = pd.DataFrame(rows, columns=["log_mu_a", "log_mu_b", "hg", "ag"])
    feat["rho"] = rho
    feat["total"] = feat["hg"] + feat["ag"]
    feat["margin"] = (feat["hg"] - feat["ag"]).abs()
    feat["blowout"] = (feat["margin"] >= 3) | (feat["total"] >= 5)
    feat["bucket"] = pd.cut(feat["total"], [-1, 1, 3, 4, 99], labels=["0-1", "2-3", "4", "5+"])
    return feat


def score_grid(feat: pd.DataFrame, r, cap) -> dict:
    """Score every match under one (r, cap) candidate; return aggregate + guardrail metrics."""
    mu_a = np.clip(np.exp(feat["log_mu_a"].to_numpy()), MU_LOW, cap)
    mu_b = np.clip(np.exp(feat["log_mu_b"].to_numpy()), MU_LOW, cap)
    rho = float(feat["rho"].iloc[0])
    hg, ag = feat["hg"].to_numpy(), feat["ag"].to_numpy()
    cap_idx = G - 1

    ranks = np.empty(len(feat)); rps = np.empty(len(feat)); nll = np.empty(len(feat))
    brier = np.empty(len(feat)); ok = np.empty(len(feat), dtype=bool)
    conf = np.empty(len(feat)); correct = np.empty(len(feat), dtype=bool)

    for n in range(len(feat)):
        flat = negbin_dc_flat(mu_a[n], mu_b[n], rho, r, G)
        idx = min(hg[n], cap_idx) * G + min(ag[n], cap_idx)
        order = np.argsort(flat)[::-1]
        ranks[n] = int(np.where(order == idx)[0][0]) + 1
        ph, pd_, pa = wdl_from_flat(flat, G)
        wdl = np.array([ph, pd_, pa])
        outcome = 0 if hg[n] > ag[n] else (1 if hg[n] == ag[n] else 2)
        obs = np.zeros(3); obs[outcome] = 1.0
        cum_p = np.cumsum(wdl); cum_o = np.cumsum(obs)
        rps[n] = float(np.sum((cum_p - cum_o) ** 2)) / 2.0
        nll[n] = -math.log(max(wdl[outcome], 1e-12))
        brier[n] = float(np.sum((wdl - obs) ** 2))
        pred = int(np.argmax(wdl))
        ok[n] = (pred == outcome)
        conf[n] = wdl[pred]; correct[n] = ok[n]

    # top-label ECE (10 bins) on this set
    ece = 0.0
    for lo in np.linspace(0, 1, 11)[:-1]:
        m = (conf >= lo) & (conf < lo + 0.1)
        if m.any():
            ece += (m.mean()) * abs(correct[m].mean() - conf[m].mean())

    def bucket_rank(label):
        m = (feat["bucket"] == label).to_numpy()
        return float(ranks[m].mean()) if m.any() else float("nan")

    bl = feat["blowout"].to_numpy()
    return {
        "r": "inf" if not math.isfinite(r) else r, "cap": cap, "n": len(feat),
        "mean_rank": float(ranks.mean()),
        "rank_0_1": bucket_rank("0-1"), "rank_2_3": bucket_rank("2-3"),
        "rank_4": bucket_rank("4"), "rank_5plus": bucket_rank("5+"),
        "blowout_rank": float(ranks[bl].mean()), "blowout_n": int(bl.sum()),
        "top3_cov": float((ranks <= 3).mean()), "top10_cov": float((ranks <= 10).mean()),
        "blowout_top10_cov": float((ranks[bl] <= 10).mean()),
        "brier_wdl": float(brier.mean()), "rps": float(rps.mean()), "nll_wdl": float(nll.mean()),
        "outcome_acc": float(ok.mean()), "ece": float(ece),
    }


def verdict(cand: dict, base: dict) -> tuple[bool, str]:
    """Pass only if high-total/blowout ranking improves materially AND guardrails hold."""
    def improved(key):
        b, c = base[key], cand[key]
        return (b - c) >= ABS_RANK_IMPROVE and (b - c) / b >= REL_RANK_IMPROVE
    rank_better = improved("rank_5plus") and improved("blowout_rank")
    guards = (
        cand["brier_wdl"] <= base["brier_wdl"] * (1 + REL_GUARD_DEGRADE)
        and cand["rps"] <= base["rps"] * (1 + REL_GUARD_DEGRADE)
        and cand["nll_wdl"] <= base["nll_wdl"] * (1 + REL_GUARD_DEGRADE)
        and cand["outcome_acc"] >= base["outcome_acc"] - ABS_ACC_DEGRADE
        and cand["ece"] <= base["ece"] + ABS_ECE_DEGRADE
    )
    if rank_better and guards:
        return True, "PASS — rank improved, guardrails held"
    if rank_better and not guards:
        return False, "FAIL — rank improved but a guardrail degraded"
    return False, "FAIL — no material rank improvement"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Building deterministic match features (martj42 2010-2025)...")
    feat = build_match_features()
    print(f"  {len(feat):,} matches")

    results = []
    for cap in CAP_GRID:
        for r in R_GRID:
            res = score_grid(feat, r, cap)
            results.append(res)
            print(f"  r={res['r']:<5} cap={cap:<4} | 5+ rank {res['rank_5plus']:.2f} "
                  f"blow {res['blowout_rank']:.2f} | Brier {res['brier_wdl']:.4f} "
                  f"RPS {res['rps']:.4f} acc {res['outcome_acc']:.3f} ECE {res['ece']:.4f}")

    rdf = pd.DataFrame(results)
    base = next(x for x in results if x["r"] == "inf" and x["cap"] == BASELINE[1])
    rdf["verdict"] = [verdict(x, base)[1] for x in results]
    rdf["passes"] = [verdict(x, base)[0] for x in results]
    rdf.to_csv(OUT_DIR / "tradeoff.csv", index=False)

    write_report(rdf, base)
    plot(rdf)
    print(f"\nWrote {OUT_DIR}/tradeoff.csv, report.md, tradeoff.png")


def write_report(rdf: pd.DataFrame, base: dict) -> None:
    passers = rdf[rdf["passes"]]
    cols = ["r", "cap", "rank_5plus", "blowout_rank", "top3_cov", "top10_cov",
            "brier_wdl", "rps", "nll_wdl", "outcome_acc", "ece", "verdict"]
    lines = [
        "# Phase 2B — Tail-overdispersion diagnostic (offline, in-repo historical set)",
        "",
        f"Dataset: martj42 competitive 2010-2025, **{base['n']:,} matches**. Production scoring grid "
        f"g={G} (goals 0-7), mu clamp [{MU_LOW}, cap]. **Baseline = (r=inf, cap=3.60)** "
        "= the live independent-Poisson + Dixon-Coles model. All params held at production values "
        "(no recalibration). Negative-Binomial dispersion r: smaller r = fatter tail; r=inf = Poisson.",
        "",
        "## Baseline (live model on this set)",
        f"- 5+ goals mean rank **{base['rank_5plus']:.2f}** · blowout mean rank **{base['blowout_rank']:.2f}** "
        f"· top-3 {base['top3_cov']*100:.1f}% · top-10 {base['top10_cov']*100:.1f}%",
        f"- Guardrails: Brier {base['brier_wdl']:.4f} · RPS {base['rps']:.4f} · NLL {base['nll_wdl']:.4f} "
        f"· acc {base['outcome_acc']*100:.1f}% · ECE {base['ece']:.4f}",
        "",
        "## Pass/fail rule (pre-registered)",
        f"PASS only if **both** 5+ and blowout mean rank drop ≥{ABS_RANK_IMPROVE} abs AND ≥{REL_RANK_IMPROVE*100:.0f}% rel, "
        f"**and** Brier/RPS/NLL not worse by >{REL_GUARD_DEGRADE*100:.1f}% rel, acc not lower by >{ABS_ACC_DEGRADE*100:.1f}pp, "
        f"ECE not worse by >{ABS_ECE_DEGRADE:.3f} abs.",
        "",
        f"**Candidates that PASS: {len(passers)} / {len(rdf)-1}** (baseline excluded).",
        "",
        "## Tradeoff table",
        rdf[cols].to_markdown(index=False, floatfmt=".4f"),
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines))


def plot(rdf: pd.DataFrame) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for cap in CAP_GRID:
        sub = rdf[rdf["cap"] == cap].copy()
        x = [99 if r == "inf" else r for r in sub["r"]]
        ax[0].plot(x, sub["rank_5plus"], "o-", label=f"cap {cap}")
        ax[1].plot(sub["brier_wdl"], sub["rank_5plus"], "o-", label=f"cap {cap}")
    ax[0].set_xlabel("NB dispersion r (99 = Poisson)"); ax[0].set_ylabel("5+ goals mean rank ↓")
    ax[0].set_title("Tail fatness vs high-total rank"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].set_xlabel("Brier W/D/L ↓ (guardrail)"); ax[1].set_ylabel("5+ goals mean rank ↓")
    ax[1].set_title("Rank gain vs calibration cost"); ax[1].legend(); ax[1].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT_DIR / "tradeoff.png", dpi=110)


if __name__ == "__main__":
    main()
