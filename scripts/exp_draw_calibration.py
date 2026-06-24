"""Phase 2F — OFFLINE draw-calibration experiment (READ-ONLY w.r.t. production).

Tests two monotone draw calibrators (A: single gamma; B: isotonic) against the uncalibrated baseline,
out-of-sample, via expanding walk-forward folds on the in-repo historical set (martj42 2010-2025).

ACCEPT a calibrator ONLY if OOS RPS *and* NLL improve beyond bootstrap noise, while Brier, ECE,
outcome accuracy, home/away calibration, and a champion proxy (aggregate W/D/L mass shift) do not
regress materially. Otherwise reject. Does not claim improvement unless that gate passes.

Reads production params/data READ-ONLY; builds distributions + calibrators in the scratch experimental
package (never imported by app.py); writes only to outputs/experiments/2F_draw_calibration/.

Run:  PYTHONPATH=src .venv/bin/python scripts/exp_draw_calibration.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat
from wc2026.experimental.draw_calibrators import apply_gamma, fit_gamma, IsotonicDrawCalibrator

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "data" / "elo_calibrated_params.json"
OUT_DIR = ROOT / "outputs" / "experiments" / "2F_draw_calibration"
G = 8
MU_LOW, MU_CAP = 0.15, 3.60
SEED = 20260625
N_BOOT = 4000
FOLDS = [2018, 2020, 2022, 2024]          # expanding: train < y, test in [y, y+1]
ACC_TOL, ECE_TOL, CALIB_TOL = 0.005, 0.005, 0.01   # guardrail materiality


def rps_ordered_vec(wdl: np.ndarray, outcomes: np.ndarray) -> np.ndarray:
    obs = np.zeros_like(wdl); obs[np.arange(len(wdl)), outcomes] = 1.0
    return np.sum((np.cumsum(wdl, 1) - np.cumsum(obs, 1)) ** 2, axis=1) / 2.0


def nll_vec(wdl: np.ndarray, outcomes: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(wdl[np.arange(len(wdl)), outcomes], 1e-12, 1.0))


def brier_vec(wdl: np.ndarray, outcomes: np.ndarray) -> np.ndarray:
    obs = np.zeros_like(wdl); obs[np.arange(len(wdl)), outcomes] = 1.0
    return np.sum((wdl - obs) ** 2, axis=1)


def top_label_ece(wdl: np.ndarray, outcomes: np.ndarray) -> float:
    conf = wdl.max(axis=1); pred = wdl.argmax(axis=1); correct = (pred == outcomes)
    ece = 0.0
    for lo in np.linspace(0, 1, 11)[:-1]:
        m = (conf >= lo) & (conf < lo + 0.1)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def build_base() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-match baseline DC-implied W/D/L, actual outcome, and year (deterministic)."""
    params = json.loads(PARAMS_PATH.read_text())
    log_base, beta, rho = float(params["log_base"]), float(params["beta_elo"]), float(params["rho"])
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    years = pd.to_datetime(df["date"]).dt.year.to_numpy()
    hg, ag = df["home_goals"].to_numpy(), df["away_goals"].to_numpy()
    wdl = np.empty((len(df), 3))
    for i, (h, a, d, n) in enumerate(zip(df["home_team"], df["away_team"], df["date"], df["neutral"])):
        ed = (elo.get_elo(h, before_date=d) + (0.0 if n else 100.0) - elo.get_elo(a, before_date=d)) / 400.0
        mu_a = min(max(np.exp(log_base + beta * ed), MU_LOW), MU_CAP)
        mu_b = min(max(np.exp(log_base - beta * ed), MU_LOW), MU_CAP)
        wdl[i] = wdl_from_flat(poisson_dc_flat(mu_a, mu_b, rho, G), G)
    outcomes = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
    return wdl, outcomes, years


def metrics(wdl, outc) -> dict:
    is_draw = (outc == 1)
    return {
        "rps": float(rps_ordered_vec(wdl, outc).mean()),
        "nll": float(nll_vec(wdl, outc).mean()),
        "brier": float(brier_vec(wdl, outc).mean()),
        "acc": float((wdl.argmax(1) == outc).mean()),
        "ece": top_label_ece(wdl, outc),
        "draw_gap": float(is_draw.mean() - wdl[:, 1].mean()),
        "home_gap": float((outc == 0).mean() - wdl[:, 0].mean()),
        "away_gap": float((outc == 2).mean() - wdl[:, 2].mean()),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Building deterministic baseline W/D/L (martj42 2010-2025)...")
    wdl, outc, years = build_base()
    print(f"  {len(wdl):,} matches · overall draw rate {(outc==1).mean():.3f} · "
          f"mean predicted P(draw) {wdl[:,1].mean():.3f}")

    # Out-of-sample pooled predictions via expanding walk-forward folds
    test_idx, base_oos, A_oos, B_oos, gammas = [], [], [], [], []
    for y in FOLDS:
        tr = years < y
        te = (years >= y) & (years < y + 2)
        if tr.sum() < 500 or te.sum() == 0:
            continue
        g = fit_gamma(wdl[tr], outc[tr]); gammas.append((y, g))
        iso = IsotonicDrawCalibrator().fit(wdl[tr][:, 1], (outc[tr] == 1).astype(float))
        idx = np.where(te)[0]
        test_idx.append(idx)
        base_oos.append(wdl[idx])
        A_oos.append(apply_gamma(wdl[idx], g))
        B_oos.append(iso.apply(wdl[idx]))
        print(f"  fold test {y}-{y+1}: n={te.sum():4d} train={tr.sum():5d} gamma={g:.2f}")

    idx = np.concatenate(test_idx)
    base = np.concatenate(base_oos); A = np.concatenate(A_oos); B = np.concatenate(B_oos)
    o = outc[idx]

    rng = np.random.default_rng(SEED)
    boot = rng.integers(0, len(o), size=(N_BOOT, len(o)))

    def diff_ci(cal_per, base_per):
        d = cal_per - base_per                  # negative = improvement (lower better)
        bs = d[boot].mean(axis=1)
        return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

    rows, verdicts = [], {}
    for name, cal in [("baseline", base), ("A_gamma", A), ("B_isotonic", B)]:
        m = metrics(cal, o)
        row = {"candidate": name, **m}
        if name != "baseline":
            for mk, fn in [("rps", rps_ordered_vec), ("nll", nll_vec)]:
                dm, lo, hi = diff_ci(fn(cal, o), fn(base, o))
                row[f"d_{mk}_mean"], row[f"d_{mk}_lo"], row[f"d_{mk}_hi"] = dm, lo, hi
            # champion proxy: how much W/D/L mass moved vs baseline
            row["wdl_mass_shift"] = float(np.abs(cal - base).sum(axis=1).mean() / 2)
        rows.append(row)

    bm = metrics(base, o)
    for name, cal, r in [("A_gamma", A, rows[1]), ("B_isotonic", B, rows[2])]:
        m = metrics(cal, o)
        rps_better = r["d_rps_hi"] < 0          # whole CI below 0
        nll_better = r["d_nll_hi"] < 0
        guards = (
            m["brier"] <= bm["brier"] + 1e-4
            and m["ece"] <= bm["ece"] + ECE_TOL
            and m["acc"] >= bm["acc"] - ACC_TOL
            and abs(m["home_gap"]) <= abs(bm["home_gap"]) + CALIB_TOL
            and abs(m["away_gap"]) <= abs(bm["away_gap"]) + CALIB_TOL
            and r["wdl_mass_shift"] <= 0.03      # champion proxy: <=3% mass moved
        )
        if rps_better and nll_better and guards:
            verdicts[name] = "PASS — OOS RPS & NLL improve beyond noise; guardrails hold"
        elif rps_better and nll_better:
            verdicts[name] = "FAIL — proper scores improve but a guardrail regressed"
        else:
            verdicts[name] = "INCONCLUSIVE/FAIL — RPS and/or NLL not beyond noise"

    rdf = pd.DataFrame(rows)
    rdf.to_csv(OUT_DIR / "oos_metrics.csv", index=False)
    write_report(rdf, verdicts, bm, len(o), gammas, (outc == 1).mean(), wdl[:, 1].mean())
    plot(base, A, B, o)
    print("\nVERDICTS:", verdicts)
    print(f"Wrote {OUT_DIR}/oos_metrics.csv, report.md, calibration.png")


def write_report(rdf, verdicts, bm, n_oos, gammas, draw_rate, pred_draw) -> None:
    cols = ["candidate", "rps", "nll", "brier", "acc", "ece", "draw_gap", "home_gap", "away_gap"]
    lines = [
        "# Phase 2F — Draw-calibration experiment (offline, walk-forward OOS)",
        "",
        f"In-repo historical set (martj42 2010-2025). Baseline = DC-implied W/D/L (no ML reweight — a "
        f"documented simplification; the shipped calibrator, if any, sits after the ML step). Expanding "
        f"walk-forward folds; **pooled OOS n = {n_oos:,}**. Overall draw rate {draw_rate:.3f} vs mean "
        f"predicted P(draw) {pred_draw:.3f} (full-set). Fitted gamma per fold: "
        + ", ".join(f"{y}->{g:.2f}" for y, g in gammas) + ".",
        "",
        "## Acceptance gate (pre-registered)",
        "PASS only if OOS **RPS and NLL** both improve **beyond noise** (95% bootstrap CI of the "
        "per-match difference entirely < 0), AND Brier, ECE, outcome accuracy, home/away calibration, "
        "and the champion proxy (W/D/L mass shift ≤ 3%) do not regress materially.",
        "",
        "## OOS metrics (lower better: rps/nll/brier/ece; gaps nearer 0 better)",
        rdf[cols].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Improvement vs baseline, with 95% bootstrap CI (negative = better)",
    ]
    for _, r in rdf.iterrows():
        if r["candidate"] == "baseline":
            continue
        lines.append(
            f"- **{r['candidate']}**: ΔRPS {r['d_rps_mean']:+.5f} [{r['d_rps_lo']:+.5f}, {r['d_rps_hi']:+.5f}] · "
            f"ΔNLL {r['d_nll_mean']:+.5f} [{r['d_nll_lo']:+.5f}, {r['d_nll_hi']:+.5f}] · "
            f"W/D/L mass shift {r['wdl_mass_shift']:.4f}")
    lines += ["", "## Verdict"]
    for k, v in verdicts.items():
        lines.append(f"- **{k}**: {v}")
    lines += ["", "_No production change. Shipping a passing calibrator would be a separate Phase 2G._"]
    (OUT_DIR / "report.md").write_text("\n".join(lines))


def plot(base, A, B, o) -> None:
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    bins = np.linspace(0, 0.5, 11)
    for name, cal, style in [("baseline", base, "o-"), ("A_gamma", A, "s--"), ("B_isotonic", B, "^-")]:
        xs, ys = [], []
        for lo, hi in zip(bins[:-1], bins[1:]):
            m = (cal[:, 1] >= lo) & (cal[:, 1] < hi)
            if m.sum() >= 20:
                xs.append(cal[m, 1].mean()); ys.append((o[m] == 1).mean())
        ax.plot(xs, ys, style, label=name)
    ax.plot([0, 0.5], [0, 0.5], "k:", alpha=.5, label="perfect")
    ax.set_xlabel("predicted P(draw)"); ax.set_ylabel("observed draw rate (OOS)")
    ax.set_title("Draw reliability (OOS)"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT_DIR / "calibration.png", dpi=110)


if __name__ == "__main__":
    main()
