#!/usr/bin/env python
"""
P4 — Final public forecast chart.
Outputs: outputs/public/wc2026_final_forecast_chart.png
"""
from __future__ import annotations

import json
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

OUT = ROOT / "outputs" / "public"
OUT.mkdir(parents=True, exist_ok=True)

ELO_CSV    = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"
PARAMS     = ROOT / "data" / "elo_calibrated_params.json"


def main():
    df     = pd.read_csv(ELO_CSV)
    params = json.loads(PARAMS.read_text())
    beta   = params["beta_elo"]
    top12  = df.head(12)

    has_ci = "champion_ci_low" in df.columns
    teams  = top12["team"].tolist()
    probs  = (top12["champion_prob"] * 100).tolist()
    lows   = (top12["champion_ci_low"]  * 100).tolist() if has_ci else None
    highs  = (top12["champion_ci_high"] * 100).tolist() if has_ci else None

    # Sober dark background
    BG0   = "#06060a"
    BG1   = "#0c0c14"
    BG2   = "#12121e"
    TEAL  = "#2A9D8F"
    RED   = "#E63946"
    GOLD  = "#E9C46A"
    GREY  = "#888888"
    WHITE = "#e8e8f0"
    DIM   = "#555566"

    fig, ax = plt.subplots(figsize=(11, 7), facecolor=BG0)
    ax.set_facecolor(BG1)
    for spine in ax.spines.values():
        spine.set_color(DIM)
    ax.tick_params(colors=WHITE, labelsize=9)

    x = np.arange(len(teams))
    bar_colors = [GOLD if i == 0 else RED if i < 3 else TEAL for i in range(len(teams))]
    bars = ax.bar(x, probs, color=bar_colors, alpha=0.82, width=0.62, zorder=3)

    if has_ci:
        ax.errorbar(
            x, probs,
            yerr=[[p - l for p, l in zip(probs, lows)],
                  [h - p for p, h in zip(probs, highs)]],
            fmt="none", color=WHITE, lw=1.2, capsize=3, alpha=0.55, zorder=4,
        )

    # Value labels on bars
    for bar, p in zip(bars, probs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                f"{p:.1f}%", ha="center", va="bottom", color=WHITE, fontsize=8.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(teams, color=WHITE, fontsize=10)
    ax.set_ylabel("Champion probability (%)", color=GREY, fontsize=9)
    ax.set_ylim(0, max(probs) * 1.25)
    ax.yaxis.grid(True, color=DIM, lw=0.5, alpha=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Title
    ax.set_title(
        "WC2026 Champion Probability — Top 12",
        color=WHITE, fontsize=14, pad=14, fontweight="bold",
    )

    # Footer annotation
    footer = (
        f"100,000 Monte Carlo simulations · Elo-calibrated temperature-corrected model "
        f"(β={beta:.3f}) · Full Hybrid rejected after calibration degradation\n"
        "Probabilistic forecast — not a prediction. Exact 48-team WC2026 bracket mechanics."
    )
    fig.text(0.5, 0.01, footer, ha="center", va="bottom",
             color=GREY, fontsize=7.5, style="italic", wrap=True)

    # Legend
    patches = [
        mpatches.Patch(color=GOLD, label="Top favourite"),
        mpatches.Patch(color=RED,  label="Top 3"),
        mpatches.Patch(color=TEAL, label="Top 4–12"),
    ]
    ax.legend(handles=patches, facecolor=BG2, edgecolor=DIM,
              labelcolor=WHITE, fontsize=8, loc="upper right")

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    out_path = OUT / "wc2026_final_forecast_chart.png"
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight", facecolor=BG0)
    plt.close()
    print(f"  Chart saved → {out_path}")


if __name__ == "__main__":
    main()
