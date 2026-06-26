"""Phase 3F — OFFLINE: market-implied 1X2 vs the FULL frozen production W/D/L (READ-ONLY).

Phase 3E compared market to Elo→DC only. Production is Elo→DC→ML@0.20. The production W/D/L collapses to
  full_wdl = 0.8 * DC_implied_wdl + 0.2 * ML_1x2_wdl   (ML features = [elo_diff, neutral=1])
which is fully reproducible offline from rolling Elo + the trained pickle. This reproduces it for the
frozen Phase 3E WC fixtures and compares full-production / market-only / blend on proper scores with
bootstrap CIs. Settlement never used as a feature. No new API calls; production math untouched (read-only).

Run:  PYTHONPATH=src .venv/bin/python scripts/research/market_vs_full_production_baseline.py
"""
from __future__ import annotations

import csv
import json
import pickle
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab" / "market_odds_dataset.csv"
OUT = ROOT / "outputs" / "research" / "phase_3f_market_vs_production"
SEED, N_BOOT = 20260625, 4000


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    alias = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
             "united states of america": "united states", "china pr": "china", "czechia": "czech republic",
             "cabo verde": "cape verde", "korea dpr": "north korea",
             "bosnia and herzegovina": "bosnia-herzegovina"}
    return alias.get(s, s)


def full_production_map():
    """(date, frozenset{norm teams}) -> (dc_wdl, full_wdl, home_norm) for WC matches in martj42."""
    pr = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    lb, beta, rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
    cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
    ew = float(cfg["ensemble"]["elo_calibrated_weight"]); mw = float(cfg["ensemble"]["ml_logistic_weight"])
    s = ew + mw; w_elo, w_ml = ew / s, mw / s
    clf = pickle.load(open(ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb"))
    classes = list(int(c) for c in clf.classes_)

    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    wc = df[df["tournament"].astype(str).str.contains("World Cup", case=False, na=False)]
    out = {}
    for h, a, d, n in zip(wc["home_team"], wc["away_team"], wc["date"], wc["neutral"]):
        ea, eb = elo.get_elo(h, before_date=d), elo.get_elo(a, before_date=d)
        ed = (ea + (0.0 if n else 100.0) - eb) / 400.0
        mu_a = min(max(np.exp(lb + beta * ed), 0.15), 3.60)
        mu_b = min(max(np.exp(lb - beta * ed), 0.15), 3.60)
        dc = np.array(wdl_from_flat(poisson_dc_flat(mu_a, mu_b, rho, 8), 8))
        proba = clf.predict_proba(np.array([[ea - eb, 1.0]]))[0]   # ML: raw elo diff, neutral
        mld = {classes[i]: float(proba[i]) for i in range(len(classes))}
        ml = np.array([mld.get(0, 0.0), mld.get(1, 0.0), mld.get(2, 0.0)])
        full = w_elo * dc + w_ml * ml
        out[(str(d)[:10], frozenset({norm(h), norm(a)}))] = (dc, full, norm(h))
    return out


def rps_rows(P, y):
    o = np.zeros_like(P); o[np.arange(len(y)), y] = 1.0
    return np.sum((np.cumsum(P, 1) - np.cumsum(o, 1)) ** 2, axis=1) / 2.0


def nll_rows(P, y):
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def brier_rows(P, y):
    o = np.zeros_like(P); o[np.arange(len(y)), y] = 1.0
    return np.sum((P - o) ** 2, axis=1)


def ece(P, y, bins=10):
    conf = P.max(1); pred = P.argmax(1); corr = (pred == y); e = 0.0
    for lo in np.linspace(0, 1, bins + 1)[:-1]:
        m = (conf >= lo) & (conf < lo + 1 / bins)
        if m.any():
            e += m.mean() * abs(corr[m].mean() - conf[m].mean())
    return float(e)


def scores(P, y):
    return {"rps": float(rps_rows(P, y).mean()), "nll": float(nll_rows(P, y).mean()),
            "brier": float(brier_rows(P, y).mean()), "acc": float((P.argmax(1) == y).mean()),
            "ece": ece(P, y)}


def boot(a, b):
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(SEED)
    bs = d[rng.integers(0, len(d), size=(N_BOOT, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ds = pd.read_csv(DATASET)
    ds = ds[ds["p_home_mkt"].notna() & (ds["p_home_mkt"].astype(str) != "")].copy()
    fp = full_production_map()

    rows = []
    for _, r in ds.iterrows():
        key = (str(r["date"]), frozenset({norm(r["home"]), norm(r["away"])}))
        if key not in fp:
            continue
        dc, full, hn = fp[key]
        if hn != norm(r["home"]):                      # orient to market home
            dc = dc[[2, 1, 0]]; full = full[[2, 1, 0]]
        rows.append({"season": str(r["season"]), "y": int(r["outcome"]),
                     "prod": full, "dc": dc,
                     "mkt": np.array([r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]], float)})
    print(f"matched {len(rows)}/{len(ds)} usable-1X2 fixtures to full production")

    report = {"counts": {"usable_1x2": int(len(ds)), "matched_full_production": len(rows)},
              "full_production_reproducible": True, "by_segment": {}}

    def seg(name, sub):
        if not sub:
            return
        y = np.array([r["y"] for r in sub])
        P = np.array([r["prod"] for r in sub]); D = np.array([r["dc"] for r in sub])
        K = np.array([r["mkt"] for r in sub])
        grid = {}
        for al in np.round(np.arange(0, 1.01, 0.1), 1):
            B = (1 - al) * P + al * K
            grid[float(al)] = scores(B, y)
        best_a = min(grid, key=lambda a: grid[a]["rps"])
        dr = boot(rps_rows(K, y), rps_rows(P, y)); dn = boot(nll_rows(K, y), nll_rows(P, y))
        Bbest = (1 - best_a) * P + best_a * K
        br = boot(rps_rows(Bbest, y), rps_rows(P, y))
        report["by_segment"][name] = {
            "n": len(sub),
            "full_production": scores(P, y), "dc_only": scores(D, y), "market": scores(K, y),
            "market_minus_prod": {"rps": dr, "nll": dn, "rps_beyond_noise": dr[2] < 0, "nll_beyond_noise": dn[2] < 0},
            "blend_best_alpha": best_a, "blend_best": grid[best_a],
            "blend_minus_prod_rps": br, "blend_beyond_noise": br[2] < 0,
            "blend_grid": grid}

    for s in ("2018", "2022"):
        seg(s, [r for r in rows if r["season"] == s])
    seg("pooled", rows)

    (OUT / "market_vs_production_report.json").write_text(json.dumps(report, indent=2, default=str))
    with (OUT / "market_vs_production_results.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "n", "metric", "full_production", "dc_only", "market", "blend_best", "best_alpha"])
        for nm, s in report["by_segment"].items():
            for met in ("rps", "nll", "brier", "acc", "ece"):
                w.writerow([nm, s["n"], met, round(s["full_production"][met], 4), round(s["dc_only"][met], 4),
                            round(s["market"][met], 4),
                            round(s["blend_best"][met], 4) if met in s["blend_best"] else "",
                            s["blend_best_alpha"]])

    print("\n=== market vs FULL production (RPS/NLL lower=better) ===")
    for nm, s in report["by_segment"].items():
        mm = s["market_minus_prod"]
        print(f"[{nm}] n={s['n']} | prod RPS {s['full_production']['rps']:.4f} (dc {s['dc_only']['rps']:.4f}) "
              f"· market RPS {s['market']['rps']:.4f} | Δrps {mm['rps'][0]:+.4f} CI[{mm['rps'][1]:+.4f},{mm['rps'][2]:+.4f}] "
              f"{'BEYOND' if mm['rps_beyond_noise'] else 'within'}-noise | NLL prod {s['full_production']['nll']:.3f} "
              f"mkt {s['market']['nll']:.3f} {'BEYOND' if mm['nll_beyond_noise'] else 'within'}")
        print(f"      blend* α={s['blend_best_alpha']} RPS {s['blend_best']['rps']:.4f} "
              f"(Δ vs prod {s['blend_minus_prod_rps'][0]:+.4f} CI[{s['blend_minus_prod_rps'][1]:+.4f},{s['blend_minus_prod_rps'][2]:+.4f}]) "
              f"| ECE prod {s['full_production']['ece']:.3f} mkt {s['market']['ece']:.3f} blend {s['blend_best']['ece']:.3f}")
    print(f"\nWrote {OUT}/market_vs_production_results.csv, market_vs_production_report.json")


if __name__ == "__main__":
    main()
