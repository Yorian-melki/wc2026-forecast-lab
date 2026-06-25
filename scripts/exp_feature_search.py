"""Phase 3A — OFFLINE evidence lab: can pre-match features beat the Elo-only baseline?

The production model's expected_goals is ELO-ONLY. This asks, out-of-sample (walk-forward on the
in-repo historical set), whether features derivable from match history (rolling form, goal rates, rest,
elo_sum) add genuine predictive signal over Elo alone — for (1) W/D/L outcome and (2) total goals (the
one real, high-total mis-specification flagged in Phase 2D).

Method: multinomial logistic (W/D/L) and Poisson GLM (total goals), baseline = [elo_diff] only vs
augmented = full feature set, standardised, fit on train, scored OOS, bootstrap CIs on per-match diffs.
A candidate "survives" only if OOS proper scores improve beyond noise without degrading.

READ-ONLY w.r.t. production: reads historical data + Elo engine; writes only to
outputs/experiments/3A_evidence_lab/. Nothing here is imported by app.py.

Run:  PYTHONPATH=src .venv/bin/python scripts/exp_feature_search.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.preprocessing import StandardScaler

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.match_features import build_rolling_features, FEATURES

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "experiments" / "3A_evidence_lab"
SEED, N_BOOT = 20260625, 4000
FOLDS = [2016, 2018, 2020, 2022, 2024]      # train < y, test [y, y+1]


def rps_rows(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    obs = np.zeros_like(P); obs[np.arange(len(y)), y] = 1.0
    return np.sum((np.cumsum(P, 1) - np.cumsum(obs, 1)) ** 2, axis=1) / 2.0


def logloss_rows(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1.0))


def brier_rows(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    obs = np.zeros_like(P); obs[np.arange(len(y)), y] = 1.0
    return np.sum((P - obs) ** 2, axis=1)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Building historical features (martj42 2010-2025)...")
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    df = df.sort_values("date").reset_index(drop=True)
    elo = RollingEloEngine(); elo.fit(df)
    feat = build_rolling_features(df, elo.get_elo)
    years = pd.to_datetime(df["date"]).dt.year.to_numpy()
    print(f"  {len(feat):,} matches · features {FEATURES}")

    X = feat[FEATURES].to_numpy()
    y = feat["outcome"].to_numpy()
    tot = feat["total_goals"].to_numpy().astype(float)

    # pooled OOS predictions
    base_P, aug_P, oos_y = [], [], []
    base_tot, aug_tot, oos_tot = [], [], []
    for yr in FOLDS:
        tr, te = years < yr, (years >= yr) & (years < yr + 2)
        if tr.sum() < 800 or te.sum() == 0:
            continue
        sc = StandardScaler().fit(X[tr])
        Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])
        elo_col = FEATURES.index("elo_diff")

        # W/D/L: baseline = elo only, augmented = all features
        b = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr[:, [elo_col]], y[tr])
        g = LogisticRegression(max_iter=2000, C=1.0).fit(Xtr, y[tr])
        base_P.append(_order(b, Xte[:, [elo_col]]))
        aug_P.append(_order(g, Xte))
        oos_y.append(y[te])

        # total goals: baseline = elo_diff only, augmented = all features
        pb = PoissonRegressor(max_iter=2000, alpha=1e-3).fit(Xtr[:, [elo_col]], tot[tr])
        pg = PoissonRegressor(max_iter=2000, alpha=1e-3).fit(Xtr, tot[tr])
        base_tot.append(pb.predict(Xte[:, [elo_col]]))
        aug_tot.append(pg.predict(Xte))
        oos_tot.append(tot[te])

    bP, aP, Y = np.vstack(base_P), np.vstack(aug_P), np.concatenate(oos_y)
    bT, aT, T = np.concatenate(base_tot), np.concatenate(aug_tot), np.concatenate(oos_tot)
    rng = np.random.default_rng(SEED)
    boot = rng.integers(0, len(Y), size=(N_BOOT, len(Y)))
    bootT = rng.integers(0, len(T), size=(N_BOOT, len(T)))

    rows = []
    for name, fn in [("logloss", logloss_rows), ("rps", rps_rows), ("brier", brier_rows)]:
        rb, ra = fn(bP, Y), fn(aP, Y)
        d = ra - rb                              # negative = augmented better
        bs = d[boot].mean(axis=1)
        rows.append({"metric": f"wdl_{name}", "baseline": float(rb.mean()), "augmented": float(ra.mean()),
                     "delta": float(d.mean()), "ci_lo": float(np.percentile(bs, 2.5)),
                     "ci_hi": float(np.percentile(bs, 97.5))})
    # total goals: Poisson deviance + MAE
    def pdev(mu):
        mu = np.clip(mu, 1e-9, None)
        return 2 * (T * np.log(np.clip(T / mu, 1e-9, None)) - (T - mu))
    for name, b_, a_ in [("tot_poisson_dev", pdev(bT), pdev(aT)),
                         ("tot_mae", np.abs(bT - T), np.abs(aT - T))]:
        d = a_ - b_; bs = d[bootT].mean(axis=1)
        rows.append({"metric": name, "baseline": float(b_.mean()), "augmented": float(a_.mean()),
                     "delta": float(d.mean()), "ci_lo": float(np.percentile(bs, 2.5)),
                     "ci_hi": float(np.percentile(bs, 97.5))})

    rdf = pd.DataFrame(rows)
    rdf.to_csv(OUT_DIR / "feature_search_oos.csv", index=False)

    # coefficient inspection (last fold's augmented W/D/L model, standardised)
    coef = pd.DataFrame(g.coef_, columns=FEATURES,
                        index=[f"class_{c}" for c in g.classes_])
    coef.to_csv(OUT_DIR / "wdl_coefficients.csv")

    verdict = decide(rdf)
    write_report(rdf, coef, verdict, len(Y))
    print("\nRESULTS:\n", rdf.to_string(index=False))
    print("\nVERDICT:", verdict)
    print(f"Wrote {OUT_DIR}/feature_search_oos.csv, wdl_coefficients.csv, report.md")


def _order(model, X) -> np.ndarray:
    """predict_proba reordered to columns [home=0, draw=1, away=2]."""
    P = model.predict_proba(X)
    out = np.zeros((len(X), 3))
    for j, c in enumerate(model.classes_):
        out[:, c] = P[:, j]
    return out


def decide(rdf: pd.DataFrame) -> str:
    def beats(m):
        r = rdf[rdf.metric == m].iloc[0]
        return r["ci_hi"] < 0          # whole CI improving (lower better)
    wdl = beats("wdl_logloss") and beats("wdl_rps")
    tot = beats("tot_poisson_dev")
    if wdl and tot:
        return "READY_FOR_MODEL_LAB — features beat Elo-only OOS on W/D/L *and* total goals"
    if wdl or tot:
        return ("RESEARCH — partial OOS signal (" +
                ("W/D/L" if wdl else "total-goals") + " improves beyond noise; the other does not)")
    # within noise?
    near = all(abs(rdf[rdf.metric == m].iloc[0]["delta"]) < 1e-3 for m in ["wdl_logloss", "wdl_rps"])
    return "WATCHLIST — no OOS improvement beyond noise" if near else "KILL — features do not help (or hurt) OOS"


def write_report(rdf, coef, verdict, n_oos) -> None:
    lines = [
        "# Phase 3A — Evidence Lab: do pre-match features beat Elo-only? (offline, walk-forward OOS)",
        "",
        f"In-repo historical set (martj42 competitive 2010-2025). Walk-forward folds {FOLDS} (train < y, "
        f"test [y, y+1]); **pooled OOS n = {n_oos:,}**. Production `expected_goals` is **Elo-only**, so the "
        "baseline is a logistic/Poisson on `elo_diff` alone; the augmented model adds rolling form, goal "
        f"rates, rest, and `elo_sum`. Features: {FEATURES}.",
        "",
        "## Acceptance",
        "A feature set **survives** only if OOS proper scores improve **beyond bootstrap noise** "
        "(95% CI of the per-match delta entirely < 0). W/D/L needs both log-loss AND RPS; the high-total "
        "lever needs total-goals Poisson deviance.",
        "",
        "## OOS results (delta = augmented − baseline; negative = better)",
        rdf.to_markdown(index=False, floatfmt=".5f"),
        "",
        "## Augmented W/D/L coefficients (standardised, last fold)",
        coef.to_markdown(floatfmt=".3f"),
        "",
        f"## Verdict: **{verdict}**",
        "",
        "_Offline research only. No production model/data/config/nav change. A surviving candidate would "
        "still require a separate, explicitly-approved Model-Lab integration phase._",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
