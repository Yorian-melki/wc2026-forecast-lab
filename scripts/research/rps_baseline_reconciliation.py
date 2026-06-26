"""Phase 3F-B — OFFLINE RPS comparability / baseline reconciliation (READ-ONLY, no API).

Explains why Phase 3F's production RPS (~0.234) differs from prior audits (~0.193 full-historical,
~0.180 live-48). Reproduces the production W/D/L (0.8*DC + 0.2*ML) for ALL martj42 competitive matches
via rolling Elo (the SAME pipeline as Phase 3F) using martj42's NATIVE home/away orientation (no
Sportmonks join), and computes RPS with the canonical formula on: full set, WC-only subset, and uniform
1/3 baselines. If the WC subset reproduces ~0.234 here, Phase 3F's join/orientation is validated and the
gap is pure dataset difficulty (WC matches are harder), not a bug.

No production change; reads params/config/pickle/martj42 read-only.
Run:  PYTHONPATH=src .venv/bin/python scripts/research/rps_baseline_reconciliation.py
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "research" / "phase_3f_market_vs_production"


def rps_rows(P, y):
    o = np.zeros_like(P); o[np.arange(len(y)), y] = 1.0
    return np.sum((np.cumsum(P, 1) - np.cumsum(o, 1)) ** 2, axis=1) / 2.0


def main():
    pr = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    lb, beta, rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
    cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
    ew = float(cfg["ensemble"]["elo_calibrated_weight"]); mw = float(cfg["ensemble"]["ml_logistic_weight"])
    s = ew + mw; w_elo, w_ml = ew / s, mw / s
    clf = pickle.load(open(ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb"))
    classes = list(int(c) for c in clf.classes_)

    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    df = df.sort_values("date").reset_index(drop=True)
    elo = RollingEloEngine(); elo.fit(df)
    is_wc = df["tournament"].astype(str).str.contains("World Cup", case=False, na=False).to_numpy()
    import pandas as pd
    yrs = pd.to_datetime(df["date"]).dt.year.to_numpy()

    dc_P, full_P, y = [], [], []
    for h, a, d, n, hg, ag in zip(df["home_team"], df["away_team"], df["date"], df["neutral"],
                                  df["home_goals"], df["away_goals"]):
        ea, eb = elo.get_elo(h, before_date=d), elo.get_elo(a, before_date=d)
        ed = (ea + (0.0 if n else 100.0) - eb) / 400.0
        mu_a = min(max(np.exp(lb + beta * ed), 0.15), 3.60)
        mu_b = min(max(np.exp(lb - beta * ed), 0.15), 3.60)
        dc = np.array(wdl_from_flat(poisson_dc_flat(mu_a, mu_b, rho, 8), 8))
        proba = clf.predict_proba(np.array([[ea - eb, 1.0]]))[0]
        mld = {classes[i]: float(proba[i]) for i in range(len(classes))}
        ml = np.array([mld.get(0, 0.0), mld.get(1, 0.0), mld.get(2, 0.0)])
        dc_P.append(dc); full_P.append(w_elo * dc + w_ml * ml)
        y.append(0 if hg > ag else (1 if hg == ag else 2))
    dc_P, full_P, y = np.array(dc_P), np.array(full_P), np.array(y)
    uni = np.full_like(dc_P, 1 / 3)

    def seg(mask, label):
        m = mask
        yy = y[m]
        return {
            "segment": label, "n": int(m.sum()),
            "dc_rps": round(float(rps_rows(dc_P[m], yy).mean()), 4),
            "full_prod_rps": round(float(rps_rows(full_P[m], yy).mean()), 4),
            "uniform_rps": round(float(rps_rows(uni[m], yy).mean()), 4),
            "model_acc": round(float((full_P[m].argmax(1) == yy).mean()), 3),
            "home_rate": round(float((yy == 0).mean()), 3),
            "draw_rate": round(float((yy == 1).mean()), 3),
            "away_rate": round(float((yy == 2).mean()), 3),
        }

    wc18_22 = is_wc & np.isin(yrs, [2018, 2022])
    rows = [seg(np.ones(len(y), bool), "ALL competitive 2010-2025"),
            seg(~is_wc, "non-WC competitive"),
            seg(is_wc, "all World Cup matches (incl. qualifiers)"),
            seg(wc18_22, "WC final tournament 2018+2022 (all, n=228)")]

    # --- decisive bug check: native-orientation RPS on the EXACT Phase 3F 128 odds-subset ---
    import unicodedata
    import pandas as pd

    def norm(t):
        t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower().strip()
        al = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
              "united states of america": "united states", "china pr": "china", "czechia": "czech republic",
              "cabo verde": "cape verde", "korea dpr": "north korea",
              "bosnia and herzegovina": "bosnia-herzegovina"}
        return al.get(t, t)

    native = {}
    for i in range(len(y)):
        if wc18_22[i]:
            native[(str(df["date"].iloc[i])[:10],
                    frozenset({norm(df["home_team"].iloc[i]), norm(df["away_team"].iloc[i])}))] = i
    d3e = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab" / "market_odds_dataset.csv"
    ds = pd.read_csv(d3e)
    ds = ds[ds["p_home_mkt"].notna() & (ds["p_home_mkt"].astype(str) != "")]
    idxs, mkts = [], []
    for _, r in ds.iterrows():
        key = (str(r["date"]), frozenset({norm(r["home"]), norm(r["away"])}))
        if key in native:
            idxs.append(native[key])
            mkts.append([float(r["p_home_mkt"]), float(r["p_draw_mkt"]), float(r["p_away_mkt"])])
    idxs = np.array(idxs)
    sub_full = full_P[idxs]; sub_y = y[idxs]; sub_uni = np.full_like(sub_full, 1 / 3)
    sub_mkt = np.array(mkts)
    rows.append({
        "segment": "WC2018+2022 odds-subset, NATIVE orientation (= 3F's 128)",
        "n": int(len(idxs)),
        "dc_rps": "", "full_prod_rps": round(float(rps_rows(sub_full, sub_y).mean()), 4),
        "uniform_rps": round(float(rps_rows(sub_uni, sub_y).mean()), 4),
        "model_acc": round(float((sub_full.argmax(1) == sub_y).mean()), 3),
        "market_rps_same_subset": round(float(rps_rows(sub_mkt, sub_y).mean()), 4),
        "home_rate": round(float((sub_y == 0).mean()), 3),
        "draw_rate": round(float((sub_y == 1).mean()), 3),
        "away_rate": round(float((sub_y == 2).mean()), 3),
    })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rps_reconciliation.json").write_text(json.dumps(rows, indent=2))
    print("segment                                                  n   dc_rps full_rps uni_rps acc")
    for r in rows:
        dc = f"{r['dc_rps']:.4f}" if isinstance(r["dc_rps"], (int, float)) else "  -   "
        print(f"{r['segment']:<54} {r['n']:>5} {dc} {r['full_prod_rps']:.4f} "
              f"{r['uniform_rps']:.4f} {r['model_acc']:.3f}")
    print(f"\nWrote {OUT}/rps_reconciliation.json")


if __name__ == "__main__":
    main()
