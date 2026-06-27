"""Phase 3G — OFFLINE Sportmonks international market-odds generalization (READ-ONLY, rate-limit-safe).

Does the market-implied 1X2 edge (Phase 3E/3F, WC only) generalize to other international tournament
FINALS? Bounded extract of Euro/Copa America/AFCON/Asian Cup (league ids from the Phase 3G inventory) +
reuse of the frozen Phase 3E WC dataset, compared vs the FULL production W/D/L (0.8*DC + 0.2*ML).

RATE-LIMIT SAFE: Retry-After honoured, else exponential backoff, MAX 2 retries, then SKIP and record
RATE_LIMITED (no looping). Processed dataset is CACHED to CSV (re-runs skip already-fetched fixtures).
Sportmonks-only. Token from .env.yorian; never printed; scrubbed. No production change, no integration.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/sportmonks_market_generalization.py
"""
from __future__ import annotations

import csv
import json
import pickle
import time
import unicodedata
from pathlib import Path
from statistics import median

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3g_market_generalization"
DATASET = OUT / "international_market_dataset.csv"
WC_3E = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab" / "market_odds_dataset.csv"
FB = "https://api.sportmonks.com/v3/football"
TIMEOUT = 30
MKT_1X2 = 1
ODDS_BATCH = 25
MAX_NEW_FIXTURES = 700

# league ids + tournament windows (from the Phase 3G inventory; NOT re-searched)
COMPETITIONS = [
    ("Euro", 1326, [("2020", "2021-06-01", "2021-07-15"), ("2024", "2024-06-10", "2024-07-20")]),
    ("Copa America", 1114, [("2019", "2019-06-10", "2019-07-10"), ("2021", "2021-06-10", "2021-07-15"),
                            ("2024", "2024-06-18", "2024-07-18")]),
    ("AFCON", 1117, [("2019", "2019-06-18", "2019-07-22"), ("2021", "2022-01-05", "2022-02-10"),
                     ("2023", "2024-01-10", "2024-02-15"), ("2025", "2025-12-15", "2026-01-25")]),
    ("Asian Cup", 1105, [("2019", "2019-01-04", "2019-02-05"), ("2023", "2024-01-10", "2024-02-12")]),
]

_state = {"requests": 0, "rate_limited": 0}


def tok():
    for l in ENV.read_text().splitlines():
        if l.strip().startswith("SPORTMONKS_TOKEN="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


TOK = tok()


def get(path, params=None):
    """GET with Retry-After / exponential backoff, MAX 2 retries, then ('RATE_LIMITED', {})."""
    p = dict(params or {}); p["api_token"] = TOK
    delay = 2.0
    for attempt in range(3):
        try:
            _state["requests"] += 1
            r = requests.get(FB + path, params=p, timeout=TIMEOUT)
            if r.status_code == 429:
                if attempt == 2:
                    _state["rate_limited"] += 1
                    return "RATE_LIMITED", {}
                ra = r.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else delay); delay *= 3
                continue
            return r.status_code, r.json()
        except Exception as e:
            if attempt == 2:
                return "ERR", {"_e": str(e)[:80]}
            time.sleep(delay); delay *= 3
    return "RATE_LIMITED", {}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    al = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
          "united states of america": "united states", "china pr": "china", "czechia": "czech republic",
          "cabo verde": "cape verde", "korea dpr": "north korea", "bosnia and herzegovina": "bosnia-herzegovina",
          "cote d'ivoire": "ivory coast", "côte d'ivoire": "ivory coast", "dr congo": "congo dr",
          "turkiye": "turkey", "turkey": "turkey", "north macedonia": "macedonia"}
    return al.get(s, s)


def novig_1x2(rows):
    b = {"1": [], "X": [], "2": []}
    for o in rows:
        try:
            dec = float(o.get("value"))
        except (TypeError, ValueError):
            continue
        if o.get("label") in b and dec > 1.0:
            b[o["label"]].append(1.0 / dec)
    if not all(b[k] for k in ("1", "X", "2")):
        return None
    raw = np.array([median(b["1"]), median(b["X"]), median(b["2"])])
    return tuple(raw / raw.sum())


def extract():
    OUT.mkdir(parents=True, exist_ok=True)
    have = set()
    rows = []
    if DATASET.exists():           # cache: skip already-fetched fixtures
        import pandas as pd
        old = pd.read_csv(DATASET)
        rows = old.to_dict("records")
        have = set(old["fixture_id"].tolist())
        print(f"  cache: {len(have)} fixtures already in dataset")

    # 1) collect finished fixtures per competition/edition
    fixtures = []
    for comp, lid, editions in COMPETITIONS:
        for ed, start, end in editions:
            page = 1
            while True:
                st, b = get(f"/fixtures/between/{start}/{end}",
                            {"filters": f"fixtureLeagues:{lid}", "include": "participants;scores",
                             "per_page": 50, "page": page})
                if st in ("RATE_LIMITED", "ERR"):
                    print(f"  {comp} {ed}: {st} on fixtures p{page} — skipping rest of edition")
                    break
                for f in (b.get("data") or []):
                    if f.get("id") in have:
                        continue
                    parts = f.get("participants") or []
                    h = next((p for p in parts if (p.get("meta") or {}).get("location") == "home"), None)
                    a = next((p for p in parts if (p.get("meta") or {}).get("location") == "away"), None)
                    if not h or not a:
                        continue
                    hg = ag = None
                    for s in (f.get("scores") or []):
                        if s.get("description") in ("CURRENT", "FT") and isinstance(s.get("score"), dict):
                            if s["score"].get("participant") == "home":
                                hg = s["score"].get("goals")
                            elif s["score"].get("participant") == "away":
                                ag = s["score"].get("goals")
                    if hg is None or ag is None:
                        continue
                    fixtures.append({"fixture_id": f.get("id"), "competition": comp, "season": ed,
                                     "date": str(f.get("starting_at"))[:10], "home": h.get("name"),
                                     "away": a.get("name"), "home_goals": hg, "away_goals": ag,
                                     "outcome": 0 if hg > ag else (1 if hg == ag else 2)})
                pg = b.get("pagination") or {}
                if not pg.get("has_more") or page >= 4 or len(fixtures) >= MAX_NEW_FIXTURES:
                    break
                page += 1
            print(f"  {comp} {ed}: collected {sum(1 for x in fixtures if x['competition']==comp and x['season']==ed)} new finished fixtures")

    fixtures = fixtures[:MAX_NEW_FIXTURES]
    # 2) odds via multi-fixture batches (markets:1)
    ids = [f["fixture_id"] for f in fixtures]
    odds_by_fid = {}
    for i in range(0, len(ids), ODDS_BATCH):
        batch = ids[i:i + ODDS_BATCH]
        st, b = get("/fixtures/multi/" + ",".join(map(str, batch)),
                    {"include": "odds", "filters": f"markets:{MKT_1X2}"})
        if st in ("RATE_LIMITED", "ERR"):
            print(f"  odds batch {i//ODDS_BATCH}: {st} — recording RATE_LIMITED, skipping batch")
            continue
        for f in (b.get("data") or []):
            odds_by_fid[f.get("id")] = [o for o in (f.get("odds") or []) if o.get("market_id") == MKT_1X2]
        time.sleep(0.2)

    # 3) build no-vig rows
    for f in fixtures:
        fr = odds_by_fid.get(f["fixture_id"])
        if not fr:
            continue
        m = novig_1x2(fr)
        if not m:
            continue
        f.update({"p_home_mkt": m[0], "p_draw_mkt": m[1], "p_away_mkt": m[2], "n_books": len({o.get("bookmaker_id") for o in fr})})
        rows.append(f)

    if rows:
        cols = ["fixture_id", "competition", "season", "date", "home", "away", "home_goals",
                "away_goals", "outcome", "p_home_mkt", "p_draw_mkt", "p_away_mkt", "n_books"]
        with DATASET.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
            for r in rows:
                if "p_home_mkt" in r:
                    w.writerow(r)
    return rows


# ---- production baseline (0.8*DC + 0.2*ML) for ALL martj42 matches, keyed by (date, teams) ----
def production_map():
    pr = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    lb, beta, rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
    cfg = json.loads((ROOT / "data" / "model_stack_config.json").read_text())
    ew = float(cfg["ensemble"]["elo_calibrated_weight"]); mw = float(cfg["ensemble"]["ml_logistic_weight"])
    s = ew + mw; w_elo, w_ml = ew / s, mw / s
    clf = pickle.load(open(ROOT / "outputs" / "models" / "ml_match_model.pkl", "rb"))
    classes = list(int(c) for c in clf.classes_)
    from wc2026.calibration.international_dataset import build_clean_dataset
    from wc2026.calibration.rolling_elo import RollingEloEngine
    from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat
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


def sc(P, y):
    return {"rps": float(rps_rows(P, y).mean()), "nll": float(nll_rows(P, y).mean()),
            "brier": float(brier_rows(P, y).mean()), "acc": float((P.argmax(1) == y).mean()), "ece": ece(P, y)}


def boot(a, b, seed=20260625, n=4000):
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), size=(n, len(d)))].mean(1)
    return [float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def main():
    if not TOK:
        raise SystemExit("token missing")
    print("Extracting international tournament odds (bounded, rate-limit-safe)...")
    inter = extract()
    print(f"  requests made: {_state['requests']} · rate_limited events: {_state['rate_limited']}")

    # assemble unified eval rows: WC (reuse 3E) + international (this phase)
    import pandas as pd
    pm = production_map()
    recs = []

    def add(comp, date, home, away, outcome, pmk):
        key = (str(date), frozenset({norm(home), norm(away)}))
        if key not in pm:
            return
        full, hn = pm[key]
        if hn != norm(home):
            full = full[[2, 1, 0]]
        recs.append({"competition": comp, "year": int(str(date)[:4]), "prod": full,
                     "mkt": np.array(pmk, float), "y": int(outcome)})

    if WC_3E.exists():
        wc = pd.read_csv(WC_3E)
        wc = wc[wc["p_home_mkt"].notna() & (wc["p_home_mkt"].astype(str) != "")]
        for _, r in wc.iterrows():
            add("World Cup", r["date"], r["home"], r["away"], r["outcome"],
                [r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])
    for r in inter:
        if "p_home_mkt" in r:
            add(r["competition"], r["date"], r["home"], r["away"], r["outcome"],
                [r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])

    usable = len(recs)
    print(f"  unified usable+matched-to-production fixtures: {usable}")
    report = {"requests_made": _state["requests"], "rate_limited_events": _state["rate_limited"],
              "usable_matched": usable, "by_segment": {}}

    enough = usable >= 150
    if not enough:
        report["status"] = "INSUFFICIENT_DATA (rate-limit or sparse odds) — no generalization conclusion"
    else:
        report["status"] = "OK"

    def seg(name, sub):
        if len(sub) < 20:
            report["by_segment"][name] = {"n": len(sub), "note": "too small (<20) — skipped"}
            return
        y = np.array([r["y"] for r in sub]); P = np.array([r["prod"] for r in sub]); K = np.array([r["mkt"] for r in sub])
        grid = {float(a): sc((1 - a) * P + a * K, y) for a in np.round(np.arange(0, 1.01, 0.1), 1)}
        ba = min(grid, key=lambda a: grid[a]["rps"])
        report["by_segment"][name] = {
            "n": len(sub), "full_production": sc(P, y), "market": sc(K, y),
            "market_minus_prod_rps": boot(rps_rows(K, y), rps_rows(P, y)),
            "market_minus_prod_nll": boot(nll_rows(K, y), nll_rows(P, y)),
            "blend_best_alpha": ba, "blend_best": grid[ba],
            "blend_minus_prod_rps": boot(rps_rows((1 - ba) * P + ba * K, y), rps_rows(P, y))}

    comps = sorted({r["competition"] for r in recs})
    for c in comps:
        seg(c, [r for r in recs if r["competition"] == c])
    seg("pooled_ALL", recs)
    seg("pooled_nonWC", [r for r in recs if r["competition"] != "World Cup"])
    seg("pooled_WC", [r for r in recs if r["competition"] == "World Cup"])
    seg("pre_2022", [r for r in recs if r["year"] < 2022])
    seg("post_2022", [r for r in recs if r["year"] >= 2022])

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "market_generalization_report.json").write_text(json.dumps(report, indent=2, default=str))
    with (OUT / "market_generalization_results.csv").open("w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["segment", "n", "metric", "full_production", "market", "blend_best", "best_alpha"])
        for nm, s in report["by_segment"].items():
            if "full_production" not in s:
                continue
            for met in ("rps", "nll", "brier", "acc", "ece"):
                w.writerow([nm, s["n"], met, round(s["full_production"][met], 4), round(s["market"][met], 4),
                            round(s["blend_best"].get(met, float("nan")), 4) if met != "acc" else round(s["blend_best"]["acc"], 4),
                            s["blend_best_alpha"]])

    print(f"\n=== Phase 3G results (status: {report['status']}) ===")
    for nm, s in report["by_segment"].items():
        if "full_production" not in s:
            print(f"[{nm}] {s.get('note','')} (n={s['n']})"); continue
        mm = s["market_minus_prod_rps"]
        print(f"[{nm}] n={s['n']} | prod RPS {s['full_production']['rps']:.4f} · market {s['market']['rps']:.4f} "
              f"| Δrps {mm[0]:+.4f} CI[{mm[1]:+.4f},{mm[2]:+.4f}] {'BEYOND' if mm[2]<0 else 'within'}-noise "
              f"| blend* α={s['blend_best_alpha']} | ECE prod {s['full_production']['ece']:.3f} mkt {s['market']['ece']:.3f}")
    print(f"\nWrote {OUT}/ (dataset, results.csv, report.json)")


if __name__ == "__main__":
    main()
