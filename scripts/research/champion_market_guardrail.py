"""Phase 3J — OFFLINE champion Monte-Carlo guardrail (CONTROLLED SYNTHETIC; READ-ONLY, no API).

QUESTION: does a capped market-informed blend over-concentrate the champion distribution (the risk the
×0.55 temperature controls)?

FEASIBILITY (stated honestly): a *full* market-blended tournament replay is NOT possible — real market
odds exist only for the 356 ACTUAL historical matches (3E/3G), never for the HYPOTHETICAL knockout matchups
a bracket MC generates. Champion-Brier vs the actual champion is likewise not computable (n=2 real WCs +
no market for hypothetical matchups). So this is a CONTROLLED SYNTHETIC guardrail that tests the
concentration MECHANISM:
  • a synthetic WC-style bracket (32 top WC2026 teams by Elo, 8 groups of 4, top-2 → 16-team single-elim),
  • per-matchup model W/D/L from the production formula (0.8*DC + 0.2*ML, neutral),
  • market is represented by a SHARPENING PROXY: power-temper the model W/D/L by T, where T is FIT on the
    356 real fixtures so the proxy reproduces the REAL market's mean confidence (0.558),
  • blend_alpha = (1-alpha)*model + alpha*market_proxy, applied to every matchup.
Limitations are explicit; this does NOT replace a live champion validation with real per-matchup odds.

No production change. Run:  PYTHONPATH=src .venv/bin/python scripts/research/champion_market_guardrail.py
"""
from __future__ import annotations

import csv
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat
from wc2026.experimental.market_blend import blend_wdl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "research" / "phase_3j_champion_guardrail"
DS_WC = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab" / "market_odds_dataset.csv"
DS_INTL = ROOT / "outputs" / "research" / "phase_3g_market_generalization" / "international_market_dataset.csv"
N_SIMS = 20000
SEED = 20260625
ALPHAS = [0.0, 0.25, 0.40, 0.60, 1.0]   # 1.0 = oracle/reference only (rejected for production)
MARKET_MEAN_CONF = 0.558                # from 3F/3I: real market mean max-prob on the 356 set


def powersharpen(wdl, T):
    w = np.asarray(wdl, float) ** T
    return w / w.sum(axis=-1, keepdims=True)


def fit_T(prod_wdls):
    """Find T so power-tempered model reproduces the real market mean confidence (0.558)."""
    lo, hi = 1.0, 6.0
    for _ in range(40):
        mid = (lo + hi) / 2
        conf = powersharpen(prod_wdls, mid).max(axis=1).mean()
        if conf < MARKET_MEAN_CONF:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ── production W/D/L from two Elos (same formula as production) ──────────────
class WDLFromElo:
    def __init__(self):
        pr = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
        self.lb, self.beta, self.rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
        cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
        ew = float(cfg["ensemble"]["elo_calibrated_weight"]); mw = float(cfg["ensemble"]["ml_logistic_weight"])
        s = ew + mw; self.w_elo, self.w_ml = ew / s, mw / s
        self.clf = pickle.load(open(ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb"))
        self.classes = list(int(c) for c in self.clf.classes_)

    def wdl(self, elo_a, elo_b):
        ed = (elo_a - elo_b) / 400.0
        mu_a = min(max(np.exp(self.lb + self.beta * ed), 0.15), 3.60)
        mu_b = min(max(np.exp(self.lb - self.beta * ed), 0.15), 3.60)
        dc = np.array(wdl_from_flat(poisson_dc_flat(mu_a, mu_b, self.rho, 8), 8))
        proba = self.clf.predict_proba(np.array([[elo_a - elo_b, 1.0]]))[0]
        mld = {self.classes[i]: float(proba[i]) for i in range(len(self.classes))}
        ml = np.array([mld.get(0, 0.0), mld.get(1, 0.0), mld.get(2, 0.0)])
        return self.w_elo * dc + self.w_ml * ml


def production_and_market_356(wdlfn):
    """PRODUCTION W/D/L (rolling Elo, 0.8*DC+0.2*ML) + MARKET no-vig, per matched 356 fixture.

    Production is the base for the T-fit (sharpen prod conf -> market conf); market validates the proxy.
    """
    import unicodedata
    from wc2026.calibration.international_dataset import build_clean_dataset
    from wc2026.calibration.rolling_elo import RollingEloEngine

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
        al = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
              "united states of america": "united states", "china pr": "china", "czechia": "czech republic",
              "cabo verde": "cape verde", "korea dpr": "north korea", "bosnia and herzegovina": "bosnia-herzegovina",
              "cote d'ivoire": "ivory coast", "dr congo": "congo dr", "turkiye": "turkey", "north macedonia": "macedonia"}
        return al.get(s, s)

    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    pm = {}
    for h, a, d, n in zip(df["home_team"], df["away_team"], df["date"], df["neutral"]):
        ea, eb = elo.get_elo(h, before_date=d), elo.get_elo(a, before_date=d)
        # neutral-orientation prod W/D/L (matches the live-feed/bracket convention)
        pm[(str(d)[:10], frozenset({norm(h), norm(a)}))] = (wdlfn.wdl(ea, eb), norm(h))

    prod, mkt, y = [], [], []
    for ds in (DS_WC, DS_INTL):
        if not ds.exists():
            continue
        dd = pd.read_csv(ds); dd = dd[dd["p_home_mkt"].notna() & (dd["p_home_mkt"].astype(str) != "")]
        hcol = "home" if "home" in dd.columns else "home"
        for _, r in dd.iterrows():
            key = (str(r["date"]), frozenset({norm(r[hcol]), norm(r["away"])}))
            if key not in pm:
                continue
            full, hn = pm[key]
            if hn != norm(r[hcol]):
                full = full[[2, 1, 0]]
            prod.append(full)
            mkt.append([r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])
            y.append(int(r["outcome"]))
    return np.array(prod, float), np.array(mkt, float), np.array(y, int)


def make_bracket_elos():
    t = pd.read_csv(ROOT / "data" / "teams.csv")
    t = t.dropna(subset=["elo_current"]).sort_values("elo_current", ascending=False).head(32)
    codes = t["code"].tolist(); elos = dict(zip(t["code"], t["elo_current"].astype(float)))
    # snake draw into 8 groups of 4 (spread strength)
    groups = {g: [] for g in range(8)}
    order = codes[:]
    for i, c in enumerate(order):
        rnd = i // 8
        pos = i % 8 if rnd % 2 == 0 else 7 - (i % 8)
        groups[pos].append(c)
    return codes, elos, groups


def pairwise(codes, elos, wdlfn, T, alpha, retemper_S=None):
    """Per-ordered-pair W/D/L: model proxy-blended at alpha; optional champion re-temper (S<1)."""
    M = {}
    for a in codes:
        for b in codes:
            if a == b:
                continue
            base = wdlfn.wdl(elos[a], elos[b])
            if alpha == 0.0:
                M[(a, b)] = base
            else:
                w = blend_wdl(base, powersharpen(base, T), alpha)
                M[(a, b)] = powersharpen(w, retemper_S) if retemper_S else w
    return M


def fit_S(prod, proxy_market, alpha, target_conf):
    """Find S so re-tempered blend mean-conf returns to `target_conf` (the baseline model sharpness)."""
    blended = blend_wdl(prod, proxy_market, alpha)
    lo, hi = 0.2, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        c = powersharpen(blended, mid).max(1).mean()
        if c > target_conf:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def sim_tournament(codes, groups, M, rng):
    # group stage: round-robin, sample W/D/L -> points
    advance = []
    for g, gc in groups.items():
        pts = {c: 0.0 for c in gc}
        for i in range(len(gc)):
            for j in range(i + 1, len(gc)):
                a, b = gc[i], gc[j]
                pH, pD, pA = M[(a, b)]
                r = rng.random()
                if r < pH:
                    pts[a] += 3
                elif r < pH + pD:
                    pts[a] += 1; pts[b] += 1
                else:
                    pts[b] += 3
        ranked = sorted(gc, key=lambda c: (pts[c], rng.random()), reverse=True)
        advance += ranked[:2]
    # 16-team single-elim KO (seed by group order: winners vs runners-up cross-bracket)
    ko = advance[:]
    while len(ko) > 1:
        nxt = []
        for i in range(0, len(ko), 2):
            a, b = ko[i], ko[i + 1]
            pH, pD, pA = M[(a, b)]
            pw = pH / (pH + pA) if (pH + pA) > 0 else 0.5     # draw -> ET/pens by win share
            nxt.append(a if rng.random() < pw else b)
        ko = nxt
    return ko[0]


def metrics(champ_counts, n):
    p = np.array([champ_counts.get(c, 0) for c in champ_counts]) / n
    p = p[p > 0]
    top = sorted(p, reverse=True)
    ent = float(-np.sum(p * np.log2(p)))
    g = float((np.abs(np.subtract.outer(p, p)).sum()) / (2 * len(p) * p.sum())) if len(p) else 0.0
    return {"top1": round(float(top[0]), 4), "top3_share": round(float(sum(top[:3])), 4),
            "entropy_bits": round(ent, 3), "gini": round(g, 3),
            "n_teams_ge_1pct": int(np.sum(np.array(top) >= 0.01))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wdlfn = WDLFromElo()
    prod356, mkt356, y356 = production_and_market_356(wdlfn)
    T = fit_T(prod356)
    # validate proxy reproduces real blend mean-confidence at each alpha
    proxy_val, real_val = {}, {}
    for a in (0.25, 0.40, 0.60):
        proxy_val[a] = round(float(blend_wdl(prod356, powersharpen(prod356, T), a).max(1).mean()), 3)
        real_val[a] = round(float(blend_wdl(prod356, mkt356, a).max(1).mean()), 3)
    print(f"prod conf {prod356.max(1).mean():.3f} · market conf {mkt356.max(1).mean():.3f} · "
          f"fit T={T:.3f} -> proxy market conf {powersharpen(prod356,T).max(1).mean():.3f} (target {MARKET_MEAN_CONF})")
    print(f"proxy-blend conf by alpha {proxy_val} vs REAL-blend {real_val} (should be close)")

    # MITIGATION: re-temper the blend back to baseline model sharpness for the champion MC
    base_conf = float(prod356.max(1).mean())
    proxy_market356 = powersharpen(prod356, T)
    S = {a: round(fit_S(prod356, proxy_market356, a, base_conf), 3) for a in (0.40, 0.60)}
    print(f"champion re-temper S (to restore baseline conf {base_conf:.3f}): {S}")

    # CRUCIAL: does re-temper KEEP the match-level RPS gain? (re-temper the REAL blend by S)
    def rps(P, yy):
        o = np.zeros_like(P); o[np.arange(len(yy)), yy] = 1.0
        return float(np.mean(np.sum((np.cumsum(P, 1) - np.cumsum(o, 1)) ** 2, axis=1) / 2.0))
    rps_match = {"production": round(rps(prod356, y356), 4)}
    for a in (0.40, 0.60):
        nb = blend_wdl(prod356, mkt356, a)
        rt = powersharpen(nb, S[a])
        rps_match[f"blend_{a}"] = round(rps(nb, y356), 4)
        rps_match[f"blend_{a}+retemper"] = round(rps(rt, y356), 4)
    print(f"match-level RPS (356): {rps_match}")

    codes, elos, groups = make_bracket_elos()
    rng = np.random.default_rng(SEED)
    results, configs = {}, [(a, None, str(a)) for a in ALPHAS] + \
        [(0.40, S[0.40], "0.4+retemper"), (0.60, S[0.60], "0.6+retemper")]
    for a, rs, label in configs:
        M = pairwise(codes, elos, wdlfn, T, a, retemper_S=rs)
        counts = {}
        for _ in range(N_SIMS):
            champ = sim_tournament(codes, groups, M, rng)
            counts[champ] = counts.get(champ, 0) + 1
        results[label] = metrics(counts, N_SIMS)
    report_S = S

    base = results["0.0"]
    report = {"method": "controlled synthetic 32-team WC-style bracket; market = power-sharpen proxy (T-fit "
                        "to real market mean-confidence 0.558); +retemper = champion mitigation (de-sharpen "
                        "blend back to baseline conf)", "n_sims": N_SIMS, "fit_T": round(T, 3), "retemper_S": report_S,
              "prod_conf": round(float(prod356.max(1).mean()), 3), "market_conf": round(float(mkt356.max(1).mean()), 3),
              "proxy_blend_conf_by_alpha": proxy_val, "real_blend_conf_by_alpha": real_val,
              "match_level_rps_356": rps_match,
              "limitations": ["market is a sharpening PROXY, not real per-matchup odds (unavailable for "
                              "hypothetical matchups)", "synthetic 32-team bracket, not the exact 48-team "
                              "WC2026 format", "champion-Brier vs actual NOT computable", "tests the "
                              "concentration MECHANISM only; full guardrail needs live per-matchup odds"],
              "by_alpha": {}, "acceptance": {}}
    # acceptance thresholds (vs frozen baseline)
    TOP3_TOL, ENT_TOL, TOP1_TOL = 0.05, 0.30, 0.03
    capped = {"0.25", "0.4", "0.6", "0.4+retemper", "0.6+retemper"}
    for label, m in results.items():
        d_top3 = m["top3_share"] - base["top3_share"]
        d_ent = base["entropy_bits"] - m["entropy_bits"]      # positive = concentration up
        d_top1 = m["top1"] - base["top1"]
        passes = label in capped and (d_top3 <= TOP3_TOL and d_ent <= ENT_TOL and d_top1 <= TOP1_TOL)
        report["by_alpha"][label] = {**m, "d_top3_share": round(d_top3, 4), "d_entropy_bits": round(d_ent, 3),
                                     "d_top1": round(d_top1, 4)}
        if label in capped:
            report["acceptance"][label] = "PASS" if passes else "FAIL (over-concentrates)"

    (OUT / "champion_guardrail_report.json").write_text(json.dumps(report, indent=2, default=str))
    with (OUT / "champion_guardrail_results.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["alpha", "top1", "top3_share", "entropy_bits", "gini", "n_teams_ge_1pct",
                    "d_top3_share", "d_entropy_bits", "d_top1", "acceptance"])
        for a, m in report["by_alpha"].items():
            w.writerow([a, m["top1"], m["top3_share"], m["entropy_bits"], m["gini"], m["n_teams_ge_1pct"],
                        m["d_top3_share"], m["d_entropy_bits"], m["d_top1"], report["acceptance"].get(a, "ref")])

    print("\n=== champion concentration by alpha (synthetic bracket, N=%d) ===" % N_SIMS)
    print("alpha  top1   top3   entropy  gini  #>=1%  Δtop3   Δentropy  verdict")
    for a, m in report["by_alpha"].items():
        print(f"{a:<5} {m['top1']:.3f}  {m['top3_share']:.3f}  {m['entropy_bits']:.2f}    {m['gini']:.2f}  "
              f"{m['n_teams_ge_1pct']:>3}   {m['d_top3_share']:+.3f}  {m['d_entropy_bits']:+.3f}   "
              f"{report['acceptance'].get(a,'(oracle ref)')}")
    print(f"\nWrote {OUT}/ (results.csv, report.json)")


if __name__ == "__main__":
    main()
