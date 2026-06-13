#!/usr/bin/env python
"""
P3 comparison chart: Expert vs Elo-Calibrated champion probabilities.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT_PUBLIC = ROOT / "outputs" / "public"
OUT_PUBLIC.mkdir(parents=True, exist_ok=True)

EXPERT_CSV  = ROOT / "outputs" / "tournament_run" / "expert_summary.csv"
ELO_CSV     = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"


def main():
    expert = pd.read_csv(EXPERT_CSV)
    elo    = pd.read_csv(ELO_CSV)

    # Top 15 by Expert rank
    top15 = expert.head(15)["team"].tolist()
    elo_dict = dict(zip(elo["team"], elo["champion_prob"]))

    # Include confidence intervals if available
    has_ci = "champion_ci_low" in expert.columns

    teams     = top15
    ex_probs  = [expert[expert["team"]==t]["champion_prob"].values[0] for t in teams]
    elo_probs = [elo_dict.get(t, 0.0) for t in teams]
    ex_low    = [expert[expert["team"]==t]["champion_ci_low"].values[0] for t in teams] if has_ci else None
    ex_high   = [expert[expert["team"]==t]["champion_ci_high"].values[0] for t in teams] if has_ci else None

    # Figure
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor="#0c0c14")
    fig.suptitle(
        "WC2026 Monte Carlo — Champion Probability\nExpert Model vs Elo-Calibrated Backbone",
        color="white", fontsize=14, y=0.99,
    )

    # ── Left panel: side-by-side bar chart ──────────────────────────────────
    ax = axes[0]
    ax.set_facecolor("#12121e")
    for spine in ax.spines.values():
        spine.set_color("#444444")
    ax.tick_params(colors="#cccccc")

    x = np.arange(len(teams))
    w = 0.38
    bars_e = ax.barh(x + w/2, [p*100 for p in ex_probs],  height=w,
                     color="#2A9D8F", alpha=0.85, label="Expert model")
    bars_l = ax.barh(x - w/2, [p*100 for p in elo_probs], height=w,
                     color="#E63946", alpha=0.85, label="Elo-calibrated")

    if has_ci:
        for i, (t, lo, hi) in enumerate(zip(teams, ex_low, ex_high)):
            ax.errorbar(
                [ex_probs[i]*100], [x[i]+w/2],
                xerr=[[ex_probs[i]*100-lo*100], [hi*100-ex_probs[i]*100]],
                fmt="none", color="white", lw=1.2, capsize=3, alpha=0.7,
            )

    ax.set_yticks(x)
    ax.set_yticklabels(teams, color="#cccccc", fontsize=9)
    ax.set_xlabel("Champion Probability (%)", color="#cccccc")
    ax.set_title("Top 15 teams (by Expert rank)", color="white", pad=6, fontsize=11)
    ax.legend(facecolor="#0c0c14", edgecolor="#444444", labelcolor="#cccccc",
              loc="lower right")

    # Annotation
    ax.text(0.98, 0.02,
            "Full Hybrid Elo-DC rejected:\nP2.5 gate BORDERLINE_EXPERIMENTAL\nECE +17%, 0 clear_win splits",
            transform=ax.transAxes, ha="right", va="bottom", color="#888888",
            fontsize=7.5, style="italic")

    # ── Right panel: delta scatter plot ─────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor("#12121e")
    for spine in ax2.spines.values():
        spine.set_color("#444444")
    ax2.tick_params(colors="#cccccc")

    deltas = [(elo_dict.get(t, 0) - ex)*100 for t, ex in zip(teams, ex_probs)]
    colors = ["#E63946" if d > 0 else "#2A9D8F" for d in deltas]

    ax2.barh(x, deltas, color=colors, alpha=0.85)
    ax2.axvline(0, color="#888888", lw=1)
    ax2.set_yticks(x)
    ax2.set_yticklabels(teams, color="#cccccc", fontsize=9)
    ax2.set_xlabel("Elo - Expert (percentage points)", color="#cccccc")
    ax2.set_title("Probability shift: Elo vs Expert\n(red = Elo higher, teal = Expert higher)",
                  color="white", pad=6, fontsize=11)

    # Annotate biggest moves
    for i, (t, d) in enumerate(zip(teams, deltas)):
        if abs(d) >= 2.0:
            ax2.text(d + (0.3 if d > 0 else -0.3), x[i], f"{d:+.1f}pp",
                     va="center", ha="left" if d > 0 else "right",
                     color="white", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = OUT_PUBLIC / "wc2026_model_comparison_chart.png"
    plt.savefig(str(out), dpi=150, bbox_inches="tight", facecolor="#0c0c14")
    plt.close()
    print(f"  Chart saved → {out}")


if __name__ == "__main__":
    main()
