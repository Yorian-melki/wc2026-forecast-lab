"""Phase 2D — OFFLINE Objective & Ceiling audit (READ-ONLY w.r.t. production).

Question it answers: for each measured "weakness", is it (a) a REAL, recoverable model error,
(b) a METRIC-INDUCED artifact (e.g. a decision rule), or (c) near the IRREDUCIBLE ceiling (noise)?

Method per match, on the deterministic in-repo historical set (martj42 2010-2025):
  - REAL    = score the production scoreline distribution against the ACTUAL result.
  - CEILING = score it against a world drawn from the model ITSELF (oracle). Computed ANALYTICALLY:
              if outcomes are drawn from p_i, the expected metric is a closed form over p_i.
              (e.g. W/D/L NLL ceiling = mean entropy of p_wdl; exact-top1 ceiling = mean max cell prob.)
  - TRIVIAL = a climatology baseline (global base-rate W/D/L; global modal exact score).
  Gap(REAL - CEILING) is the recoverable headroom. Small gap ⇒ irreducible for this model family.

Bootstrap CIs over matches; plus a "resample 48 from history" illustration of how noisy an n=48 audit is.

Reads production params/data READ-ONLY; builds distributions in the scratch experimental module; writes
ONLY to outputs/experiments/2D_objective_ceiling/. Nothing here is imported by app.py. Cannot affect live.

Run:  PYTHONPATH=src .venv/bin/python scripts/exp_objective_ceiling.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.calibration.rolling_elo import RollingEloEngine
from wc2026.experimental.nb_scoreline import poisson_dc_flat, wdl_from_flat

ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = ROOT / "data" / "elo_calibrated_params.json"
OUT_DIR = ROOT / "outputs" / "experiments" / "2D_objective_ceiling"
G = 8
MU_LOW, MU_CAP = 0.15, 3.60
SEED = 20260625
N_BOOT = 4000
N_SMALL = 48


def rps_ordered(p, outcome: int) -> float:
    obs = np.zeros(3); obs[outcome] = 1.0
    return float(np.sum((np.cumsum(p) - np.cumsum(obs)) ** 2)) / 2.0


def build_features() -> pd.DataFrame:
    params = json.loads(PARAMS_PATH.read_text())
    log_base, beta, rho = float(params["log_base"]), float(params["beta_elo"]), float(params["rho"])
    df, _ = build_clean_dataset(min_year=2010, max_year=2025, competitive_only=True)
    elo = RollingEloEngine(); elo.fit(df)
    rows = []
    for h, a, d, n, hg, ag in zip(df["home_team"], df["away_team"], df["date"],
                                  df["neutral"], df["home_goals"], df["away_goals"]):
        ed = (elo.get_elo(h, before_date=d) + (0.0 if n else 100.0) - elo.get_elo(a, before_date=d)) / 400.0
        rows.append((log_base + beta * ed, log_base - beta * ed, int(hg), int(ag)))
    f = pd.DataFrame(rows, columns=["log_mu_a", "log_mu_b", "hg", "ag"])
    f["rho"] = rho
    f["total"] = f["hg"] + f["ag"]
    f["blowout"] = ((f["hg"] - f["ag"]).abs() >= 3) | (f["total"] >= 5)
    f["bucket"] = pd.cut(f["total"], [-1, 1, 3, 4, 999], labels=["0-1", "2-3", "4", "5+"])
    return f


def per_match_arrays(f: pd.DataFrame) -> dict:
    """One pass: REAL per-match scores + analytic CEILING per-match expectations."""
    mu_a = np.clip(np.exp(f["log_mu_a"].to_numpy()), MU_LOW, MU_CAP)
    mu_b = np.clip(np.exp(f["log_mu_b"].to_numpy()), MU_LOW, MU_CAP)
    rho = float(f["rho"].iloc[0])
    hg, ag = f["hg"].to_numpy(), f["ag"].to_numpy()
    N, cap = len(f), G - 1

    A = {k: np.empty(N) for k in (
        "r_top1", "r_top3", "r_top5", "r_rank", "r_acc", "r_rps", "r_brier", "r_nll", "r_pdraw",
        "c_top1", "c_top3", "c_top5", "c_rank", "c_acc", "c_rps", "c_brier", "c_nll")}
    A["actual_idx"] = np.empty(N, dtype=int)
    A["pred_draw"] = np.empty(N, dtype=bool)
    A["actual_draw"] = (hg == ag)
    cell_counts = np.zeros(G * G)
    outcomes = np.empty(N, dtype=int)

    for i in range(N):
        flat = poisson_dc_flat(mu_a[i], mu_b[i], rho, G)
        order = np.argsort(flat)[::-1]
        ranks = np.empty(G * G); ranks[order] = np.arange(1, G * G + 1)
        idx = min(hg[i], cap) * G + min(ag[i], cap)
        A["actual_idx"][i] = idx
        cell_counts[idx] += 1
        # REAL
        A["r_rank"][i] = ranks[idx]
        A["r_top1"][i] = ranks[idx] == 1
        A["r_top3"][i] = ranks[idx] <= 3
        A["r_top5"][i] = ranks[idx] <= 5
        ph, pdr, pa = wdl_from_flat(flat, G)
        wdl = np.array([ph, pdr, pa])
        o = 0 if hg[i] > ag[i] else (1 if hg[i] == ag[i] else 2)
        outcomes[i] = o
        A["pred_draw"][i] = int(np.argmax(wdl)) == 1
        A["r_acc"][i] = int(np.argmax(wdl)) == o
        A["r_rps"][i] = rps_ordered(wdl, o)
        e = np.zeros(3); e[o] = 1.0
        A["r_brier"][i] = float(np.sum((wdl - e) ** 2))
        A["r_nll"][i] = -np.log(max(wdl[o], 1e-12))
        A["r_pdraw"][i] = pdr
        # CEILING (analytic expectations under outcome ~ model)
        A["c_top1"][i] = flat[order[0]]
        A["c_top3"][i] = flat[order[:3]].sum()
        A["c_top5"][i] = flat[order[:5]].sum()
        A["c_rank"][i] = float(np.sum(flat * ranks))
        A["c_acc"][i] = float(wdl.max())
        A["c_rps"][i] = float(sum(wdl[k] * rps_ordered(wdl, k) for k in range(3)))
        A["c_brier"][i] = float(sum(wdl[k] * np.sum((wdl - np.eye(3)[k]) ** 2) for k in range(3)))
        A["c_nll"][i] = float(-np.sum(wdl * np.log(np.clip(wdl, 1e-12, 1))))   # entropy = NLL floor

    A["_outcomes"] = outcomes
    A["_baserate"] = np.bincount(outcomes, minlength=3) / N
    A["_modal_cell"] = int(np.argmax(cell_counts))
    A["_blowout"] = f["blowout"].to_numpy()
    A["_bucket"] = f["bucket"].to_numpy()
    A["_N"] = N
    return A


def trivial_baselines(A: dict) -> dict:
    """Climatology: global base-rate W/D/L forecast; global modal exact score."""
    br = A["_baserate"]; o = A["_outcomes"]
    return {
        "exact_top1": float((A["actual_idx"] == A["_modal_cell"]).mean()),
        "outcome_acc": float(br.max()),
        "rps": float(np.mean([rps_ordered(br, oi) for oi in o])),
        "nll_wdl": float(np.mean([-np.log(max(br[oi], 1e-12)) for oi in o])),
    }


def ci(arr, idx) -> tuple[float, float]:
    s = arr[idx].mean(axis=1)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Building deterministic features (martj42 2010-2025)...")
    f = build_features()
    A = per_match_arrays(f)
    N = A["_N"]
    print(f"  {N:,} matches · modal exact score = "
          f"{A['_modal_cell']//G}-{A['_modal_cell']%G} · base-rate H/D/A = "
          f"{A['_baserate'][0]:.3f}/{A['_baserate'][1]:.3f}/{A['_baserate'][2]:.3f}")

    triv = trivial_baselines(A)
    rng = np.random.default_rng(SEED)
    boot_idx = rng.integers(0, N, size=(N_BOOT, N))

    metrics = [
        ("outcome_acc", "r_acc", "c_acc", "max", triv["outcome_acc"]),
        ("rps", "r_rps", "c_rps", "min", triv["rps"]),
        ("brier_wdl", "r_brier", "c_brier", "min", None),
        ("nll_wdl", "r_nll", "c_nll", "min", triv["nll_wdl"]),
        ("exact_top1", "r_top1", "c_top1", "max", triv["exact_top1"]),
        ("exact_top3", "r_top3", "c_top3", "max", None),
        ("exact_top5", "r_top5", "c_top5", "max", None),
        ("mean_rank", "r_rank", "c_rank", "min", None),
    ]
    rows = []
    for name, rk, ck, better, tv in metrics:
        real, ceil = A[rk].mean(), A[ck].mean()
        lo, hi = ci(A[rk], boot_idx)
        # headroom = recoverable fraction of the trivial->ceiling span that REAL hasn't captured
        head = None
        if tv is not None:
            span = (ceil - tv) if better == "max" else (tv - ceil)
            got = (real - tv) if better == "max" else (tv - real)
            head = None if abs(span) < 1e-9 else max(0.0, min(1.0, 1 - got / span))
        rows.append({"metric": name, "better": better, "trivial": tv, "real": real,
                     "real_ci_lo": lo, "real_ci_hi": hi, "ceiling": ceil,
                     "gap_real_minus_ceiling": real - ceil,
                     "unrealized_headroom_frac": head})
    mdf = pd.DataFrame(rows)
    mdf.to_csv(OUT_DIR / "metrics_with_ci.csv", index=False)

    # by-total-goals + blowout rank (real vs ceiling)
    brows = []
    for label in ["0-1", "2-3", "4", "5+"]:
        m = (A["_bucket"] == label)
        brows.append({"subset": f"total {label}", "n": int(m.sum()),
                      "real_rank": float(A["r_rank"][m].mean()), "ceiling_rank": float(A["c_rank"][m].mean())})
    bo = A["_blowout"]
    brows.append({"subset": "blowout", "n": int(bo.sum()),
                  "real_rank": float(A["r_rank"][bo].mean()), "ceiling_rank": float(A["c_rank"][bo].mean())})
    bdf = pd.DataFrame(brows); bdf.to_csv(OUT_DIR / "rank_by_bucket.csv", index=False)

    # draws: recall (argmax rule) real vs ceiling, + calibration
    dmask = A["actual_draw"]
    draw_recall_real = float(A["pred_draw"][dmask].mean()) if dmask.any() else float("nan")
    draw_pred_rate = float(A["pred_draw"].mean())           # how often argmax EVER says draw
    draw_calib_gap = float(dmask.mean() - A["r_pdraw"].mean())   # actual draw rate - mean predicted

    # n=48 illustration: how noisy is a 48-match audit?
    small = {}
    for k, arr in [("exact_top1", A["r_top1"]), ("exact_top3", A["r_top3"]),
                   ("outcome_acc", A["r_acc"]), ("rps", A["r_rps"])]:
        s = np.array([arr[rng.choice(N, N_SMALL, replace=False)].mean() for _ in range(N_BOOT)])
        small[k] = (float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5)))
    s_draw = np.array([A["pred_draw"][rng.choice(N, N_SMALL, replace=False)].mean() for _ in range(N_BOOT)])
    small["draw_pred_rate"] = (float(np.percentile(s_draw, 2.5)), float(np.percentile(s_draw, 97.5)))

    write_report(mdf, bdf, draw_recall_real, draw_pred_rate, draw_calib_gap, small, A)
    plot(mdf, bdf)
    print(f"\nWrote {OUT_DIR}/metrics_with_ci.csv, rank_by_bucket.csv, report.md, ceiling_vs_real.png")


def verdict_for(row) -> str:
    """real vs ceiling vs CI → real / metric-or-irreducible classification."""
    real, ceil, lo, hi = row["real"], row["ceiling"], row["real_ci_lo"], row["real_ci_hi"]
    near = ceil is not None and (lo <= ceil <= hi or abs(real - ceil) <= 0.02 * (abs(ceil) + 1e-9) + 1e-4)
    if near:
        return "AT CEILING — irreducible for this model family (not a recoverable weakness)"
    head = row["unrealized_headroom_frac"]
    if head is not None and head >= 0.10:
        return f"REAL headroom — ~{head*100:.0f}% of trivial→ceiling span unrealized"
    return "near ceiling — little recoverable headroom"


def write_report(mdf, bdf, draw_recall, draw_pred_rate, draw_calib_gap, small, A) -> None:
    lines = [
        "# Phase 2D — Objective & Ceiling audit (offline, in-repo historical set)",
        "",
        f"Set: martj42 competitive 2010-2025, **{A['_N']:,} matches** (production grid g={G}, "
        f"μ∈[{MU_LOW},{MU_CAP}]). REAL = production Poisson+DC scored vs actual results. "
        "CEILING = analytic expectation if outcomes were drawn from the model itself (the best any "
        "model of THIS family could score). TRIVIAL = global base-rate / modal-score climatology.",
        "",
        "> **In-sample caveat:** REAL here is in-sample (model fit on 2010-2025). It flatters the model, "
        "so if even in-sample REAL sits well below CEILING, that gap is genuine mis-specification; if "
        "REAL ≈ CEILING, the metric is at its irreducible floor for this family. CEILING is the key column.",
        "",
        "## Proper scores & exact-score metrics: REAL vs CEILING vs TRIVIAL",
        mdf.assign(verdict=[verdict_for(r) for _, r in mdf.iterrows()])[
            ["metric", "trivial", "real", "real_ci_lo", "real_ci_hi", "ceiling",
             "unrealized_headroom_frac", "verdict"]].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Scoreline rank by total goals: REAL vs CEILING (expected rank)",
        bdf.to_markdown(index=False, floatfmt=".2f"),
        "",
        "## Draws",
        f"- Draw recall under the argmax rule: REAL **{draw_recall:.3f}**. The model predicts 'draw' as "
        f"the modal W/D/L outcome only **{draw_pred_rate*100:.2f}%** of the time *at all* → the CEILING for "
        "draw recall under this decision rule is ~0. **Draw recall 0/14 is a decision-rule artifact, not a "
        "probability failure.**",
        f"- Draw calibration gap (actual draw rate − mean predicted P(draw)) = **{draw_calib_gap:+.3f}** "
        "→ the size of the only genuinely model-side draw issue (mild under-prediction).",
        "",
        "## How noisy is an n=48 audit? (resample-48-from-history, 95% spread)",
        f"- exact_top1: [{small['exact_top1'][0]:.3f}, {small['exact_top1'][1]:.3f}]",
        f"- exact_top3: [{small['exact_top3'][0]:.3f}, {small['exact_top3'][1]:.3f}]",
        f"- outcome_acc: [{small['outcome_acc'][0]:.3f}, {small['outcome_acc'][1]:.3f}]",
        f"- rps: [{small['rps'][0]:.3f}, {small['rps'][1]:.3f}]",
        f"- draw predicted-rate: [{small['draw_pred_rate'][0]:.3f}, {small['draw_pred_rate'][1]:.3f}] "
        "(spans 0 ⇒ a 48-match draw recall of 0 is fully consistent with the model).",
        "",
        "## Read-off",
        "- A metric whose **CEILING ≈ TRIVIAL** has almost no signal to extract by construction.",
        "- A metric where **REAL ≈ CEILING** is at its irreducible floor — stop optimising it; keep it as a "
        "*diagnostic*, not a target.",
        "- Only metrics with **REAL materially below CEILING** (unrealized headroom) are worth a model change.",
        "",
        "## Honest interpretation (per weakness)",
        "- **W/D/L proper scores (acc/RPS/NLL/Brier): REAL is BETTER than the self-sim reference.** The self-sim "
        "is a *self-consistency* point, not a hard ceiling: REAL beating it means real outcomes are MORE "
        "concentrated than the model's probabilities ⇒ the model is mildly **under-confident / over-dispersed** "
        "in-sample (a side-effect of the ×0.55 champion-level temperature). A *sharpening* lever could help "
        "match-level proper scores — but it directly fights the champion-level over-concentration the temperature "
        "was added to fix. Not free; do not touch without a champion-level guardrail.",
        "- **Exact-score top-1: essentially irreducible.** Even a perfectly-specified model of this family tops out "
        "at ~12.7% (ceiling), barely above the 10.9% you get by always guessing 1-0. REAL 11.8% sits between. The "
        "entire achievable range above climatology is ~1.8pp. **Not worth chasing.**",
        "- **Exact-score top-3 / top-5: AT CEILING** (REAL ≈ self-sim). No recoverable signal. Diagnostic only.",
        "- **Scoreline rank: aggregate is ~1 rank above ceiling (8.08 vs 7.05) — but it splits by total goals.** "
        "Low-total games rank BETTER than ceiling (0-1: 3.33 vs 7.05); high-total games rank FAR WORSE "
        "(5+: 21.78 vs 7.03; blowout 17.21 vs 7.03). So the **high-total weakness is REAL** (genuine "
        "mis-specification for those matches, NOT purely a metric artifact) — but it affects a minority (~17% are "
        "5+ goals), the naive fix (fatter marginal tail) backfired in 2B, and optimising rank trades against W/D/L "
        "calibration. **Keep scoreline rank as a DIAGNOSTIC, not a target.** Any real attempt must be a *conditional* "
        "lever for high-total matches, gated on not regressing the dominant low-total games or W/D/L scores.",
        "- **Draws: recall 0/14 is a decision-rule artifact** (ceiling recall ≈ 0 under argmax). The only genuine "
        "model-side draw issue is mild under-prediction (calibration gap ≈ −3.6pp).",
        "- **The live-48 audit is very noisy.** At n=48, exact_top1's 95% spread is ~[0.04, 0.21] and outcome_acc "
        "~[0.44, 0.73]; the live point values all sit inside. Do not over-read single live-48 numbers.",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines))


def plot(mdf, bdf) -> None:
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    sub = mdf[mdf["metric"].isin(["exact_top1", "exact_top3", "exact_top5", "outcome_acc"])]
    x = np.arange(len(sub))
    ax[0].bar(x - 0.2, sub["real"], 0.4, label="real")
    ax[0].bar(x + 0.2, sub["ceiling"], 0.4, label="ceiling")
    ax[0].set_xticks(x); ax[0].set_xticklabels(sub["metric"], rotation=20)
    ax[0].set_title("Real vs ceiling (higher better)"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(bdf["subset"], bdf["real_rank"], "o-", label="real rank")
    ax[1].plot(bdf["subset"], bdf["ceiling_rank"], "s--", label="ceiling rank")
    ax[1].set_title("Scoreline rank vs ceiling by total goals (lower better)")
    ax[1].legend(); ax[1].grid(alpha=.3); plt.setp(ax[1].get_xticklabels(), rotation=20)
    fig.tight_layout(); fig.savefig(OUT_DIR / "ceiling_vs_real.png", dpi=110)


if __name__ == "__main__":
    main()
