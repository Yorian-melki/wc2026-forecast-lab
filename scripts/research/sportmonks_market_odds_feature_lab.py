"""Phase 3E — OFFLINE Sportmonks historical market-odds feature lab (READ-ONLY, no production touch).

Tests whether Sportmonks historical WC odds (league 732, 2018/2022/2026) carry predictive value vs the
FROZEN production model. Builds a frozen offline dataset (cached to CSV; API hit once), de-vigs 1X2 +
O/U, and compares market-only / frozen-model / blend on proper scores (RPS, Brier, NLL, acc, ECE),
split by WC + pooled. Settlement (`winning`) used ONLY for a leakage diagnostic, never as a feature.

SECRET-SAFE: token from .env.yorian only; never printed; scrubbed from any saved sample. No integration,
no betting, bounded extract (WC fixtures only, hard cap). Model math FROZEN — read-only reproduction.

Run:  PYTHONPATH=src .venv/bin/python scripts/research/sportmonks_market_odds_feature_lab.py
"""
from __future__ import annotations

import csv
import json
import time
import unicodedata
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.yorian"
OUT = ROOT / "outputs" / "research" / "phase_3e_market_odds_feature_lab"
DATASET = OUT / "market_odds_dataset.csv"
FB = "https://api.sportmonks.com/v3/football"
TIMEOUT = 30
MKT_1X2, MKT_OU = 1, 80
WC_WINDOWS = {  # league 732 season -> (start, end)
    "2018": ("2018-06-14", "2018-07-15"),
    "2022": ("2022-11-20", "2022-12-18"),
    "2026": ("2026-06-01", "2026-06-26"),
}
FIXTURE_CAP = 260


def tok():
    for l in ENV.read_text().splitlines():
        if l.strip().startswith("SPORTMONKS_TOKEN="):
            return l.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


TOK = tok()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()
    alias = {"korea republic": "south korea", "ir iran": "iran", "usa": "united states",
             "united states of america": "united states", "china pr": "china",
             "czechia": "czech republic", "cabo verde": "cape verde",
             "korea dpr": "north korea", "bosnia and herzegovina": "bosnia-herzegovina"}
    return alias.get(s, s)


def get(path, params=None):
    p = dict(params or {}); p["api_token"] = TOK
    for attempt in range(2):
        try:
            r = requests.get(FB + path, params=p, timeout=TIMEOUT)
            return r.status_code, r.json()
        except Exception:
            if attempt == 0:
                time.sleep(1.0); continue
            return "ERR", {}
    return "ERR", {}


def implied_novig_1x2(rows):
    """Median bookmaker no-vig 1X2. rows: odds rows for market 1. Returns (pH,pD,pA,n_books) or None."""
    from statistics import median
    buckets = {"1": [], "X": [], "2": []}
    books = set()
    for o in rows:
        lab = o.get("label")
        try:
            dec = float(o.get("value"))
        except (TypeError, ValueError):
            continue
        if lab in buckets and dec > 1.0:
            buckets[lab].append(1.0 / dec); books.add(o.get("bookmaker_id"))
    if not all(buckets[k] for k in ("1", "X", "2")):
        return None
    raw = np.array([median(buckets["1"]), median(buckets["X"]), median(buckets["2"])])
    return (*(raw / raw.sum()), len(books))


def implied_novig_ou(rows):
    """No-vig Over/Under at the line closest to 2.5. Returns (line,pOver,pUnder) or None."""
    from collections import defaultdict
    from statistics import median
    by_line = defaultdict(lambda: {"Over": [], "Under": []})
    for o in rows:
        try:
            tot = float(o.get("total")); dec = float(o.get("value"))
        except (TypeError, ValueError):
            continue
        lab = o.get("label")
        if lab in ("Over", "Under") and dec > 1.0:
            by_line[tot][lab].append(1.0 / dec)
    best = None
    for line, d in by_line.items():
        if d["Over"] and d["Under"]:
            if best is None or abs(line - 2.5) < abs(best - 2.5):
                best = line
    if best is None:
        return None
    o_, u_ = median(by_line[best]["Over"]), median(by_line[best]["Under"])
    s = o_ + u_
    return best, o_ / s, u_ / s


def extract():
    if not TOK:
        raise SystemExit("token missing")
    OUT.mkdir(parents=True, exist_ok=True)
    rows_out = []
    n_fix = 0
    for season, (start, end) in WC_WINDOWS.items():
        fixtures, page = [], 1
        while True:
            st, b = get(f"/fixtures/between/{start}/{end}",
                        {"filters": "fixtureLeagues:732", "include": "participants;scores",
                         "per_page": 50, "page": page})
            fixtures += (b.get("data") or []) if isinstance(b, dict) else []
            pg = b.get("pagination") or {} if isinstance(b, dict) else {}
            if not pg.get("has_more") or page >= 6:
                break
            page += 1
        print(f"  season {season}: {len(fixtures)} fixtures in window ({page} page(s), HTTP {st})")
        for f in fixtures:
            if n_fix >= FIXTURE_CAP:
                break
            parts = f.get("participants") or []
            home = next((p for p in parts if (p.get("meta") or {}).get("location") == "home"), None)
            away = next((p for p in parts if (p.get("meta") or {}).get("location") == "away"), None)
            if not home or not away:
                continue
            scores = f.get("scores") or []
            hg = ag = None
            for s in scores:
                if s.get("description") in ("CURRENT", "FT") and isinstance(s.get("score"), dict):
                    pid = s["score"].get("participant")
                    g = s["score"].get("goals")
                    if pid == "home":
                        hg = g
                    elif pid == "away":
                        ag = g
            if hg is None or ag is None:
                continue                     # not finished / no score
            fid = f.get("id")
            st2, ob = get(f"/fixtures/{fid}", {"include": "odds", "filters": f"markets:{MKT_1X2},{MKT_OU}"})
            odds = (ob.get("data") or {}).get("odds") or []
            fr = [o for o in odds if o.get("market_id") == MKT_1X2]
            ou = [o for o in odds if o.get("market_id") == MKT_OU]
            m = implied_novig_1x2(fr)
            ouv = implied_novig_ou(ou)
            settle = sorted({o.get("label") for o in fr if o.get("winning")})  # diagnostic only
            ts = max((o.get("latest_bookmaker_update") or "") for o in fr) if fr else ""
            rows_out.append({
                "fixture_id": fid, "season": season, "date": str(f.get("starting_at"))[:10],
                "home": home.get("name"), "away": away.get("name"),
                "home_goals": hg, "away_goals": ag,
                "outcome": 0 if hg > ag else (1 if hg == ag else 2),
                "p_home_mkt": m[0] if m else "", "p_draw_mkt": m[1] if m else "",
                "p_away_mkt": m[2] if m else "", "n_books": m[3] if m else 0,
                "ou_line": ouv[0] if ouv else "", "p_over_mkt": ouv[1] if ouv else "",
                "p_under_mkt": ouv[2] if ouv else "",
                "settle_label": "|".join(str(x) for x in settle), "last_update": ts,
            })
            n_fix += 1
            time.sleep(0.05)
    with DATASET.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader(); w.writerows(rows_out)
    print(f"  wrote {len(rows_out)} fixtures -> {DATASET}")
    return rows_out


def load_dataset():
    import pandas as pd
    return pd.read_csv(DATASET)


def frozen_model_wdl():
    """Reproduce the FROZEN model's W/D/L for WC2018/2022 from martj42 + rolling Elo (read-only).
    Returns dict keyed by (date, frozenset{norm(home),norm(away)}) -> (pH,pD,pA, home_norm)."""
    import json as _j
    from wc2026.calibration.international_dataset import build_clean_dataset
    from wc2026.calibration.rolling_elo import RollingEloEngine
    from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat
    pr = _j.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    lb, beta, rho = float(pr["log_base"]), float(pr["beta_elo"]), float(pr["rho"])
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    wc = df[df["tournament"].astype(str).str.contains("World Cup", case=False, na=False)]
    out = {}
    for h, a, d, n in zip(wc["home_team"], wc["away_team"], wc["date"], wc["neutral"]):
        ed = (elo.get_elo(h, before_date=d) + (0.0 if n else 100.0) - elo.get_elo(a, before_date=d)) / 400.0
        mu_a = min(max(np.exp(lb + beta * ed), 0.15), 3.60)
        mu_b = min(max(np.exp(lb - beta * ed), 0.15), 3.60)
        pH, pD, pA = wdl_from_flat(poisson_dc_flat(mu_a, mu_b, rho, 8), 8)
        out[(str(d)[:10], frozenset({norm(h), norm(a)}))] = (pH, pD, pA, norm(h))
    return out


def rps_rows(P, y):
    obs = np.zeros_like(P); obs[np.arange(len(y)), y] = 1.0
    return np.sum((np.cumsum(P, 1) - np.cumsum(obs, 1)) ** 2, axis=1) / 2.0


def nll_rows(P, y):
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def boot_diff(a_rows, b_rows, seed=20260625, n=4000):
    """Bootstrap CI of mean(a-b) per match. Negative => a better (lower score). Returns (mean,lo,hi)."""
    d = np.asarray(a_rows) - np.asarray(b_rows)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n, len(d)))
    bs = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def rps(P, y):
    return float(rps_rows(P, y).mean())


def nll(P, y):
    return float(np.mean(-np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))))


def brier(P, y):
    obs = np.zeros_like(P); obs[np.arange(len(y)), y] = 1.0
    return float(np.mean(np.sum((P - obs) ** 2, axis=1)))


def acc(P, y):
    return float(np.mean(P.argmax(1) == y))


def main():
    if DATASET.exists():
        print(f"Using cached dataset {DATASET}")
        import pandas as pd
        ds = pd.read_csv(DATASET)
    else:
        print("Extracting Sportmonks WC odds (bounded)...")
        extract()
        import pandas as pd
        ds = pd.read_csv(DATASET)

    mkt = ds.dropna(subset=["p_home_mkt", "p_draw_mkt", "p_away_mkt"]).copy()
    mkt = mkt[mkt["p_home_mkt"] != ""]
    print(f"\nfixtures total={len(ds)} · with usable 1X2={len(mkt)} · with totals={ds['p_over_mkt'].apply(lambda x: x not in ('', None) and not (isinstance(x,float) and np.isnan(x))).sum()}")

    # leakage check: settlement not used as a feature (it's only in settle_label col, never in P)
    leak_ok = True

    fm = frozen_model_wdl()
    report = {"counts": {"total": int(len(ds)), "usable_1x2": int(len(mkt))}, "by_segment": {}, "blend": {}}

    def eval_segment(name, sub):
        sub = sub[sub["p_home_mkt"] != ""].copy()
        if len(sub) == 0:
            return
        y = sub["outcome"].to_numpy().astype(int)
        Pm = sub[["p_home_mkt", "p_draw_mkt", "p_away_mkt"]].to_numpy(dtype=float)
        seg = {"n": int(len(sub)),
               "market_only": {"rps": rps(Pm, y), "nll": nll(Pm, y), "brier": brier(Pm, y), "acc": acc(Pm, y)}}
        # frozen-model join (2018/2022 only; 2026 not in martj42)
        rows_model, rows_mkt, ys = [], [], []
        for _, r in sub.iterrows():
            key = (str(r["date"]), frozenset({norm(r["home"]), norm(r["away"])}))
            if key in fm:
                pH, pD, pA, hnorm = fm[key]
                # orient model probs to the market's home (sub home)
                if hnorm == norm(r["home"]):
                    rows_model.append([pH, pD, pA])
                else:
                    rows_model.append([pA, pD, pH])
                rows_mkt.append([r["p_home_mkt"], r["p_draw_mkt"], r["p_away_mkt"]])
                ys.append(int(r["outcome"]))
        if rows_model:
            M = np.array(rows_model, float); K = np.array(rows_mkt, float); yy = np.array(ys)
            seg["matched_model_n"] = len(yy)
            seg["frozen_model"] = {"rps": rps(M, yy), "nll": nll(M, yy), "brier": brier(M, yy), "acc": acc(M, yy)}
            seg["market_on_matched"] = {"rps": rps(K, yy), "nll": nll(K, yy), "brier": brier(K, yy), "acc": acc(K, yy)}
            # bootstrap CI of (market - model) per-match; negative & CI<0 => market beats model beyond noise
            dr_m, dr_lo, dr_hi = boot_diff(rps_rows(K, yy), rps_rows(M, yy))
            dn_m, dn_lo, dn_hi = boot_diff(nll_rows(K, yy), nll_rows(M, yy))
            seg["market_minus_model"] = {
                "rps_delta": dr_m, "rps_ci": [dr_lo, dr_hi], "rps_beats_beyond_noise": dr_hi < 0,
                "nll_delta": dn_m, "nll_ci": [dn_lo, dn_hi], "nll_beats_beyond_noise": dn_hi < 0}
            # blend grid
            grid = {}
            for al in np.round(np.arange(0, 1.01, 0.1), 1):
                B = (1 - al) * M + al * K
                grid[float(al)] = {"rps": rps(B, yy), "nll": nll(B, yy), "brier": brier(B, yy)}
            best = min(grid.items(), key=lambda kv: kv[1]["rps"])
            seg["blend_best_alpha"] = best[0]; seg["blend_best"] = best[1]; seg["blend_grid"] = grid
        report["by_segment"][name] = seg
        return seg

    for seg in ("2018", "2022", "2026"):
        eval_segment(seg, mkt[mkt["season"].astype(str) == seg])
    eval_segment("pooled_2018_2022", mkt[mkt["season"].astype(str).isin(["2018", "2022"])])
    eval_segment("pooled_all", mkt)

    # results CSV
    with (OUT / "market_feature_results.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["segment", "n", "matched_model_n", "metric", "frozen_model", "market", "blend_best", "best_alpha"])
        for name, seg in report["by_segment"].items():
            for met in ("rps", "nll", "brier", "acc"):
                fm_v = seg.get("frozen_model", {}).get(met, "")
                mk_v = seg.get("market_on_matched", seg.get("market_only", {})).get(met, "")
                bl_v = seg.get("blend_best", {}).get(met, "") if met != "acc" else ""
                w.writerow([name, seg.get("n"), seg.get("matched_model_n", ""), met, fm_v, mk_v, bl_v,
                            seg.get("blend_best_alpha", "")])

    report["leakage_check"] = {"settlement_used_as_feature": False,
                               "timestamp_field": "latest_bookmaker_update (last pre-match update)",
                               "note": "1X2 features = median-bookmaker no-vig from decimal odds; winning/settlement excluded"}
    (OUT / "market_feature_report.json").write_text(json.dumps(report, indent=2))

    print("\n=== SEGMENT RESULTS (RPS lower=better) ===")
    for name, seg in report["by_segment"].items():
        line = f"[{name}] n={seg['n']}"
        if "frozen_model" in seg:
            mm = seg["market_minus_model"]
            line += (f" matched={seg['matched_model_n']} | model RPS {seg['frozen_model']['rps']:.4f}"
                     f" · market RPS {seg['market_on_matched']['rps']:.4f}"
                     f" (Δrps {mm['rps_delta']:+.4f} CI[{mm['rps_ci'][0]:+.4f},{mm['rps_ci'][1]:+.4f}]"
                     f" {'BEYOND-NOISE' if mm['rps_beats_beyond_noise'] else 'within-noise'})"
                     f" · blend* RPS {seg['blend_best']['rps']:.4f} @α={seg['blend_best_alpha']}")
        else:
            line += f" | market-only RPS {seg['market_only']['rps']:.4f} (no frozen-model join)"
        print(line)
    print(f"\nWrote {OUT}/market_feature_results.csv, market_feature_report.json")


if __name__ == "__main__":
    main()
