"""Phase 3I — OFFLINE market-informed Model-Lab prototype (READ-ONLY, no API, no production touch).

Applies the Phase 3H-B identity-preserving blend offline on the frozen 3E (WC) + 3G (international) market
datasets, vs the FULL production W/D/L (0.8*DC + 0.2*ML reproduced via rolling Elo). Reports fixed-alpha
blends {0, 0.25, 0.40, 0.60}, a regime-aware prototype, and market-only (alpha=1.0) as an ORACLE REFERENCE
(rejected for production identity). Includes a champion-concentration PROXY and emits a shadow-log schema.

No provider calls. Nothing here changes default forecasts or deployed behavior.
Run:  PYTHONPATH=src .venv/bin/python scripts/research/market_model_lab_prototype.py
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
from wc2026.experimental.market_blend import blend_wdl, blend_wdl_regime, regime_alpha, entropy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "research" / "phase_3i_market_model_lab"
DS_WC = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab" / "market_odds_dataset.csv"
DS_INTL = ROOT / "outputs" / "research" / "phase_3g_market_generalization" / "international_market_dataset.csv"
ALPHAS = [0.0, 0.25, 0.40, 0.60]
SEED, NBOOT = 20260625, 4000


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    al = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
          "united states of america": "united states", "china pr": "china", "czechia": "czech republic",
          "cabo verde": "cape verde", "korea dpr": "north korea", "bosnia and herzegovina": "bosnia-herzegovina",
          "cote d'ivoire": "ivory coast", "dr congo": "congo dr", "turkiye": "turkey", "north macedonia": "macedonia"}
    return al.get(s, s)


def production_map():
    pr = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    lb, beta, rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
    cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
    ew = float(cfg["ensemble"]["elo_calibrated_weight"]); mw = float(cfg["ensemble"]["ml_logistic_weight"])
    s = ew + mw; w_elo, w_ml = ew / s, mw / s
    clf = pickle.load(open(ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb"))
    classes = list(int(c) for c in clf.classes_)
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    out = {}
    for h, a, d, n in zip(df["home_team"], df["away_team"], df["date"], df["neutral"]):
        ea, eb = elo.get_elo(h, before_date=d), elo.get_elo(a, before_date=d)
        ed = (ea + (0.0 if n else 100.0) - eb) / 400.0
        mu_a = min(max(np.exp(lb + beta * ed), 0.15), 3.60)
        mu_b = min(max(np.exp(lb - beta * ed), 0.15), 3.60)
        dc = np.array(wdl_from_flat(poisson_dc_flat(mu_a, mu_b, rho, 8), 8))
        proba = clf.predict_proba(np.array([[ea - eb, 1.0]]))[0]
        mld = {classes[i]: float(proba[i]) for i in range(len(classes))}
        ml = np.array([mld.get(0, 0.0), mld.get(1, 0.0), mld.get(2, 0.0)])
        out[(str(d)[:10], frozenset({norm(h), norm(a)}))] = (w_elo * dc + w_ml * ml, norm(h))
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
    conf = P.max(1); corr = (P.argmax(1) == y); e = 0.0
    for lo in np.linspace(0, 1, bins + 1)[:-1]:
        m = (conf >= lo) & (conf < lo + 1 / bins)
        if m.any():
            e += m.mean() * abs(corr[m].mean() - conf[m].mean())
    return float(e)


def scores(P, y):
    return {"rps": float(rps_rows(P, y).mean()), "nll": float(nll_rows(P, y).mean()),
            "brier": float(brier_rows(P, y).mean()), "acc": float((P.argmax(1) == y).mean()),
            "ece": ece(P, y), "mean_conf": float(P.max(1).mean()), "mean_entropy": float(entropy(P).mean())}


def boot(a, b):
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(SEED)
    bs = d[rng.integers(0, len(d), size=(NBOOT, len(d)))].mean(1)
    return [float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def load_rows(pm):
    recs = []

    def add(comp, date, home, away, outcome, pmk):
        key = (str(date), frozenset({norm(home), norm(away)}))
        if key not in pm:
            return
        full, hn = pm[key]
        if hn != norm(home):
            full = full[[2, 1, 0]]
        recs.append({"comp": comp, "prod": full, "mkt": np.array(pmk, float), "y": int(outcome)})

    if DS_WC.exists():
        wc = pd.read_csv(DS_WC); wc = wc[wc["p_home_mkt"].notna() & (wc["p_home_mkt"].astype(str) != "")]
        for _, r in wc.iterrows():
            add("World Cup", r["date"], r["home"], r["away"], r["outcome"], [r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])
    if DS_INTL.exists():
        it = pd.read_csv(DS_INTL); it = it[it["p_home_mkt"].notna()]
        for _, r in it.iterrows():
            add(r["competition"], r["date"], r["home"], r["away"], r["outcome"], [r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])
    return recs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pm = production_map()
    recs = load_rows(pm)
    y = np.array([r["y"] for r in recs]); P = np.array([r["prod"] for r in recs]); K = np.array([r["mkt"] for r in recs])
    n = len(recs)
    print(f"prototype built · matched fixtures n={n}")

    methods = {"production(alpha=0)": P}
    for a in ALPHAS[1:]:
        methods[f"blend_alpha={a}"] = blend_wdl(P, K, a)
    methods["blend_regime(cap0.6)"] = blend_wdl_regime(P, K, cap=0.6)
    methods["market_only(alpha=1.0 ORACLE-ref)"] = K

    report = {"n": n, "methods": {}, "alpha_grid": ALPHAS,
              "identity_note": "alpha=1.0 is an ORACLE REFERENCE only — rejected for production (bookmaker wrapper)."}
    base_rps, base_nll = rps_rows(P, y), nll_rows(P, y)
    for name, Q in methods.items():
        s = scores(Q, y)
        s["vs_prod_rps"] = boot(rps_rows(Q, y), base_rps)
        s["vs_prod_nll"] = boot(nll_rows(Q, y), base_nll)
        s["beats_prod_beyond_noise"] = bool(s["vs_prod_rps"][2] < 0 and s["vs_prod_nll"][2] < 0)
        report["methods"][name] = s

    # segment: WC vs nonWC for the best capped blend (0.60) and regime
    seg = {}
    for sname, mask in [("WC", np.array([r["comp"] == "World Cup" for r in recs])),
                        ("nonWC", np.array([r["comp"] != "World Cup" for r in recs]))]:
        seg[sname] = {}
        for name in ("blend_alpha=0.6", "blend_regime(cap0.6)"):
            Q = methods[name]
            seg[sname][name] = {"n": int(mask.sum()),
                                "rps_vs_prod": boot(rps_rows(Q[mask], y[mask]), rps_rows(P[mask], y[mask]))}
    report["segments"] = seg

    # champion-concentration PROXY (match-level): does the blend sharpen W/D/L?
    report["champion_proxy"] = {
        name: {"mean_conf": report["methods"][name]["mean_conf"],
               "mean_entropy": report["methods"][name]["mean_entropy"],
               "ece": report["methods"][name]["ece"]}
        for name in methods}
    report["champion_proxy_note"] = (
        "PROXY ONLY: mean match-level confidence/entropy. Higher confidence than production => champion "
        "RE-CONCENTRATION risk (the thing the x0.55 temperature fixed). The FULL champion guardrail requires "
        "running the 100k tournament Monte Carlo with blended W/D/L on a reconstructed WC bracket — NOT "
        "testable from these match-level datasets alone. MISSING: bracket/group wiring + MC harness with "
        "blended per-match W/D/L + champion-Brier/top-3-concentration vs frozen baseline.")

    (OUT / "market_blend_report.json").write_text(json.dumps(report, indent=2, default=str))
    with (OUT / "market_blend_results.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["method", "rps", "nll", "brier", "acc", "ece", "mean_conf", "mean_entropy",
                    "drps_vs_prod", "drps_ci_lo", "drps_ci_hi", "beats_beyond_noise"])
        for name, s in report["methods"].items():
            w.writerow([name, round(s["rps"], 4), round(s["nll"], 4), round(s["brier"], 4), round(s["acc"], 3),
                        round(s["ece"], 4), round(s["mean_conf"], 4), round(s["mean_entropy"], 4),
                        round(s["vs_prod_rps"][0], 4), round(s["vs_prod_rps"][1], 4), round(s["vs_prod_rps"][2], 4),
                        s["beats_prod_beyond_noise"]])

    # shadow-log schema (design artifact; no active logger)
    schema = {"_doc": "Phase 3H-B shadow logger — proposed schema; OFFLINE design only, no active scheduler.",
              "fields": {"fixture_id": "str/int", "kickoff_utc": "ISO8601", "provider": "the_odds_api|sportmonks",
                         "snapshot_ts_utc": "ISO8601 (<= kickoff-15min)", "n_books": "int (>=3 else low_coverage)",
                         "market_wdl": "[p_home,p_draw,p_away] no-vig", "production_wdl": "[p_home,p_draw,p_away]",
                         "alpha": "float (0..0.6 capped)", "alpha_policy": "fixed|regime",
                         "blended_wdl": "[p_home,p_draw,p_away]", "freshness_min": "minutes before kickoff",
                         "fallback_reason": "none|stale|missing|low_coverage|provider_down|name_unmapped",
                         "served": "false (shadow mode — never served)"}}
    (OUT / "shadow_log_schema.json").write_text(json.dumps(schema, indent=2))

    print("\n=== fixed-alpha blends (RPS lower=better; Δ vs production) ===")
    for name, s in report["methods"].items():
        print(f"  {name:<34} RPS {s['rps']:.4f} NLL {s['nll']:.4f} ECE {s['ece']:.3f} conf {s['mean_conf']:.3f} "
              f"| Δrps {s['vs_prod_rps'][0]:+.4f} CI[{s['vs_prod_rps'][1]:+.4f},{s['vs_prod_rps'][2]:+.4f}] "
              f"{'BEYOND' if s['beats_prod_beyond_noise'] else 'within'}-noise")
    print(f"\nproduction mean_conf {report['methods']['production(alpha=0)']['mean_conf']:.3f} · "
          f"market mean_conf {report['methods']['market_only(alpha=1.0 ORACLE-ref)']['mean_conf']:.3f} "
          f"(champion-proxy: blend confidence between these)")
    print(f"Wrote {OUT}/ (results.csv, report.json, shadow_log_schema.json)")


if __name__ == "__main__":
    main()
