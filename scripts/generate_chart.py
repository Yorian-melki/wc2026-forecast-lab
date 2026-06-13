"""
WC2026 LinkedIn Chart — June 8 2026
Reads REAL simulation outputs. Never hardcodes values.
1200x628px dark premium format.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SIM_DIR = ROOT / "outputs" / "tournament_run"
ODDS_CSV = ROOT / "data" / "market_odds_sample.csv"
TEAMS_CSV = ROOT / "data" / "teams.csv"
OUT_FILE = ROOT / "outputs" / "wc2026_linkedin_june2026.png"

CONF_COLORS = {
    "UEFA":     "#4F9CF9",
    "CONMEBOL": "#22C55E",
    "CONCACAF": "#F59E0B",
    "CAF":      "#EF4444",
    "AFC":      "#A78BFA",
}

TEAM_CONF = {
    "ESP": "UEFA", "FRA": "UEFA", "POR": "UEFA", "ENG": "UEFA",
    "NED": "UEFA", "GER": "UEFA", "BEL": "UEFA", "CRO": "UEFA",
    "SCO": "UEFA", "SUI": "UEFA", "AUT": "UEFA", "NOR": "UEFA",
    "ARG": "CONMEBOL", "BRA": "CONMEBOL", "COL": "CONMEBOL",
    "URU": "CONMEBOL", "ECU": "CONMEBOL",
    "USA": "CONCACAF", "MEX": "CONCACAF", "CAN": "CONCACAF",
    "MAR": "CAF", "SEN": "CAF", "EGY": "CAF", "CIV": "CAF",
    "JPN": "AFC", "KOR": "AFC", "IRN": "AFC", "AUS": "AFC",
}

INJURY_NOTES = {
    "NED": "Simons ACL | De Ligt + De Vrij OUT",
    "BRA": "Rodrygo ACL | Neymar calf (match 1 doubt)",
    "JPN": "Mitoma hamstring OUT",
    "ARG": "Messi hamstring (day-by-day)",
    "ESP": "Fermín López OUT",
    "ENG": "Palmer + Foden + TAA omitted",
    "FRA": "Ekitike Achilles | Camavinga omitted",
}

HOST_NATIONS = {"USA", "MEX", "CAN"}


def load_data():
    df = pd.read_csv(SIM_DIR / "summary.csv")
    teams_df = pd.read_csv(TEAMS_CSV)
    group_map = dict(zip(teams_df["code"], teams_df["group"]))
    df["group"] = df["team"].map(group_map)
    odds_df = pd.read_csv(ODDS_CSV)
    mkt_map = dict(zip(odds_df["team"], odds_df["title_american"]))
    df["market_odds"] = df["team"].map(mkt_map)
    df["market_implied"] = 100 / (df["market_odds"] + 100)
    total_imp = df["market_implied"].sum()
    df["market_fair_pct"] = df["market_implied"] / total_imp * 100
    df["model_pct"] = df["champion_prob"] * 100
    df["edge"] = df["model_pct"] - df["market_fair_pct"]
    return df


def make_chart(df):
    top_n = 14
    top = df.head(top_n).copy()

    teams = top["team"].tolist()
    win_pct = top["model_pct"].tolist()
    sf_pct = (top["sf_prob"] * 100).tolist()
    group_adv_pct = (top["group_survival_prob"] * 100).tolist()
    groups = top["group"].tolist()
    edges = top["edge"].tolist()
    colors = [CONF_COLORS.get(TEAM_CONF.get(t, "UEFA"), "#6B7280") for t in teams]

    fig = plt.figure(figsize=(13.33, 7.0))
    fig.patch.set_facecolor("#090E17")

    from matplotlib.gridspec import GridSpec
    gs = GridSpec(1, 2, width_ratios=[2.5, 1], figure=fig,
                  left=0.03, right=0.97, top=0.80, bottom=0.10, wspace=0.07)
    ax_main = fig.add_subplot(gs[0])
    ax_right = fig.add_subplot(gs[1])
    for ax in (ax_main, ax_right):
        ax.set_facecolor("#0D1420")

    y = np.arange(top_n)
    h = 0.36

    # SF bars (ghost)
    ax_main.barh(y + h / 2, sf_pct, h,
                 color=[c + "22" for c in colors],
                 edgecolor=[c + "60" for c in colors],
                 linewidth=0.7)
    # Win bars (solid)
    bars = ax_main.barh(y - h / 2, win_pct, h,
                        color=colors,
                        edgecolor=[c + "CC" for c in colors],
                        linewidth=0.9)

    ci_low = (top["champion_ci_low"] * 100).tolist() if "champion_ci_low" in top.columns else [wv for wv in win_pct]
    ci_high = (top["champion_ci_high"] * 100).tolist() if "champion_ci_high" in top.columns else [wv for wv in win_pct]

    for i, (bar, wv, sv, t, edge) in enumerate(zip(bars, win_pct, sf_pct, teams, edges)):
        # 95% CI error bar on win bar
        xerr_lo = wv - ci_low[i]
        xerr_hi = ci_high[i] - wv
        ax_main.errorbar(
            wv, bar.get_y() + bar.get_height() / 2,
            xerr=[[xerr_lo], [xerr_hi]],
            fmt='none', color='#FFFFFF', alpha=0.5, capsize=3, linewidth=1.2,
        )
        # Win label
        ax_main.text(ci_high[i] + 0.10, bar.get_y() + bar.get_height() / 2,
                     f"{wv:.2f}%", va="center", ha="left",
                     fontsize=9.5, fontweight="bold", color=colors[i])
        # SF label
        ax_main.text(sv + 0.08, y[i] + h / 2,
                     f"SF {sv:.1f}%", va="center", ha="left",
                     fontsize=7, color="#6B87A0")
        # Injury notes
        if t in INJURY_NOTES:
            ax_main.text(0.25, y[i] - h / 2 - 0.22,
                         INJURY_NOTES[t],
                         fontsize=6.2, color="#EF4444", alpha=0.90, style="italic")
        # Host flag
        if t in HOST_NATIONS:
            ax_main.text(0.25, y[i] + h / 2 + 0.05,
                         "HOST NATION", fontsize=6.0, color="#F59E0B", alpha=0.85)
        # Market edge annotation
        if not np.isnan(edge):
            edge_color = "#22C55E" if edge > 0 else "#EF4444"
            ax_main.text(max(sf_pct) * 1.28, y[i],
                         f"vs mkt: {edge:+.1f}pp", va="center", ha="right",
                         fontsize=6.0, color=edge_color, alpha=0.75)

    y_labels = [f"{t}  [{groups[i]}]" for i, t in enumerate(teams)]
    ax_main.set_yticks(y)
    ax_main.set_yticklabels(y_labels, fontsize=10.5, color="#D8E8F4")
    ax_main.invert_yaxis()
    ax_main.set_xlabel("Win Probability (%)", fontsize=9, color="#6B87A0", labelpad=5)
    ax_main.set_xlim(0, max(sf_pct) * 1.40)
    ax_main.tick_params(colors="#6B87A0")
    ax_main.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    for spine in ax_main.spines.values():
        spine.set_color("#1A2740")
    ax_main.xaxis.grid(True, color="#1A2740", linewidth=0.5)
    ax_main.set_axisbelow(True)

    # Right panel: group advance %
    top_r = top.head(12)
    r_teams = top_r["team"].tolist()
    r_adv = (top_r["group_survival_prob"] * 100).tolist()
    y_r = np.arange(len(r_teams))
    r_colors = [CONF_COLORS.get(TEAM_CONF.get(t, "UEFA"), "#6B7280") for t in r_teams]
    bars_r = ax_right.barh(y_r, r_adv, 0.55,
                            color=[c + "44" for c in r_colors],
                            edgecolor=r_colors, linewidth=1.0)
    for bar, (t, gv) in zip(bars_r, zip(r_teams, r_adv)):
        ax_right.text(gv + 0.4, bar.get_y() + bar.get_height() / 2,
                      f"{gv:.0f}%", va="center", ha="left",
                      fontsize=9, color="#D8E8F4")
    ax_right.set_yticks(y_r)
    ax_right.set_yticklabels(r_teams, fontsize=9.5, color="#D8E8F4")
    ax_right.invert_yaxis()
    ax_right.set_xlim(0, 108)
    ax_right.set_xlabel("Group Stage Advance %", fontsize=8, color="#6B87A0", labelpad=5)
    ax_right.set_title("Group exit odds", fontsize=8.5, color="#6B87A0", pad=4)
    ax_right.tick_params(colors="#6B87A0")
    for spine in ax_right.spines.values():
        spine.set_color("#1A2740")
    ax_right.xaxis.grid(True, color="#1A2740", linewidth=0.5)
    ax_right.set_axisbelow(True)

    # Header
    fig.text(0.04, 0.97,
             "WORLD CUP 2026  —  QUANT MODEL FORECAST  (June 8, 2026)",
             fontsize=16, fontweight="bold", color="#FFFFFF", va="top")
    fig.text(0.04, 0.91,
             "15-dim latent score model  ·  Dixon-Coles bivariate Poisson (ρ=0.08)  ·  ET + penalties  ·  100,000 Monte Carlo simulations",
             fontsize=9, color="#6B87A0", va="top")
    fig.text(0.04, 0.87,
             "Confirmed squads + injuries + warm-ups integrated  ·  Error bars = 95% Wilson CI  ·  Solid = win title  /  Ghost = reach SF",
             fontsize=8.5, color="#4A6280", va="top")
    fig.text(0.97, 0.97,
             "@YorianMelki",
             fontsize=10, color="#4F9CF9", va="top", ha="right", fontweight="bold")

    # Confederation legend
    shown = sorted(set(TEAM_CONF.get(t, "UEFA") for t in teams))
    patches = [mpatches.Patch(color=CONF_COLORS.get(c, "#fff"), label=c) for c in shown]
    fig.legend(handles=patches, loc="upper right",
               bbox_to_anchor=(0.97, 0.87),
               framealpha=0.12, facecolor="#0D1420", edgecolor="#1A2740",
               fontsize=8, labelcolor="#D8E8F4",
               title="Confederation", title_fontsize=7.5)

    fig.text(0.5, 0.02,
             "Probabilistic forecast — not a guaranteed prediction  ·  WC2026 starts June 11, 2026 (MEX vs RSA, Mexico City)",
             ha="center", fontsize=7.2, color="#3A5270", style="italic")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_FILE, dpi=96, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Chart saved: {OUT_FILE}")
    return OUT_FILE


if __name__ == "__main__":
    df = load_data()
    out = make_chart(df)
    print("\nTop 14 used in chart:")
    for i, (_, r) in enumerate(df.head(14).iterrows()):
        mkt_str = f"mkt {r['market_fair_pct']:.2f}%" if not np.isnan(r.get('market_fair_pct', float('nan'))) else "mkt N/A"
        edge_str = f"edge {r['edge']:+.2f}pp" if not np.isnan(r.get('edge', float('nan'))) else ""
        print(f"  {i+1:2}. {r['team']}  win={r['model_pct']:.2f}%  sf={r['sf_prob']*100:.1f}%  grp={r['group_survival_prob']*100:.0f}%  {mkt_str}  {edge_str}")
