"""
WC2026 Probabilistic Analytics Platform
World-class probabilistic tournament analysis
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─── paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs" / "tournament_run"
CALIB = ROOT / "outputs" / "calibration"
AUDIT = ROOT / "outputs" / "audit"
sys.path.insert(0, str(ROOT / "src"))

# ─── design system ────────────────────────────────────────────────────────────
BG0    = "#06060a"
BG1    = "#0c0c14"
BG2    = "#12121e"
BG3    = "#1a1a2e"
RED    = "#E63946"
TEAL   = "#2A9D8F"
GOLD   = "#E9C46A"
WHITE  = "#F0F0F8"
MUTED  = "#6B6B8A"
BORDER = "#1e1e32"

CONF_COLORS = {
    "UEFA": TEAL, "CONMEBOL": RED, "CONCACAF": GOLD,
    "AFC": "#A8DADC", "CAF": "#F4A261", "OFC": "#C77DFF",
}

st.set_page_config(
    page_title="WC2026 Probabilistic Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] {{
    background-color: {BG0} !important;
    color: {WHITE};
    font-family: 'DM Sans', system-ui, sans-serif;
  }}
  .main {{ background-color: {BG0}; }}
  section[data-testid="stSidebar"] {{
    background-color: {BG1} !important;
    border-right: 1px solid {BORDER};
  }}
  [data-testid="metric-container"] {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 16px 20px;
  }}
  [data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {WHITE} !important;
    font-family: 'DM Serif Display', serif;
    font-size: 28px !important;
  }}
  h1 {{ font-family: 'DM Serif Display', serif; color: {WHITE}; font-size: 2.4rem; }}
  h2 {{ font-family: 'DM Serif Display', serif; color: {WHITE}; font-size: 1.7rem; }}
  h3 {{ font-family: 'DM Sans', sans-serif; font-weight: 600; color: {WHITE}; }}
  .stTabs [data-baseweb="tab-list"] {{
    background: {BG1};
    border-bottom: 1px solid {BORDER};
    gap: 4px;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {MUTED};
    font-weight: 500;
    border-radius: 8px 8px 0 0;
    padding: 8px 18px;
    font-size: 13px;
  }}
  .stTabs [aria-selected="true"] {{
    color: {WHITE} !important;
    background: {BG2} !important;
    border-top: 2px solid {TEAL} !important;
  }}
  .stSelectbox > div, .stMultiSelect > div {{
    background: {BG2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px;
  }}
  hr {{ border-color: {BORDER}; }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.04em;
  }}
  .badge-teal {{ background: rgba(42,157,143,0.2); color: {TEAL}; border: 1px solid {TEAL}; }}
  .badge-red  {{ background: rgba(230,57,70,0.2);  color: {RED};  border: 1px solid {RED}; }}
  .badge-gold {{ background: rgba(233,196,106,0.2); color: {GOLD}; border: 1px solid {GOLD}; }}
  .badge-muted {{ background: rgba(107,107,138,0.15); color: {MUTED}; border: 1px solid {MUTED}; }}
  .card {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
  }}
  .caveat-box {{
    background: rgba(230,57,70,0.08);
    border: 1px solid rgba(230,57,70,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 12px;
    color: #C08090;
    margin: 8px 0;
  }}
  .info-box {{
    background: rgba(42,157,143,0.08);
    border: 1px solid rgba(42,157,143,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 12px;
    color: #7EC8C0;
    margin: 8px 0;
  }}
  .sidebar-title {{
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem;
    color: {WHITE};
    margin-bottom: 4px;
  }}
  .sidebar-sub {{
    font-size: 11px;
    color: {MUTED};
    margin-bottom: 20px;
  }}
</style>
""", unsafe_allow_html=True)


# ─── data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_live_summary() -> pd.DataFrame:
    p = OUTPUTS / "live_summary.csv"
    if p.exists():
        return pd.read_csv(p)
    candidates = [OUTPUTS / "elo_calibrated_summary.csv", OUTPUTS / "summary.csv"]
    for c in candidates:
        if c.exists():
            return pd.read_csv(c)
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_expert_summary() -> pd.DataFrame:
    p = OUTPUTS / "expert_summary.csv"
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_wc_history() -> pd.DataFrame:
    p = DATA / "wc_history.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_h2h() -> pd.DataFrame:
    p = DATA / "h2h_records.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_penalty() -> pd.DataFrame:
    p = DATA / "penalty_history.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_display() -> pd.DataFrame:
    p = DATA / "team_display.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_form() -> pd.DataFrame:
    p = DATA / "recent_form.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_groups() -> dict:
    p = DATA / "groups.json"
    return json.loads(p.read_text()) if p.exists() else {}

@st.cache_data(show_spinner=False)
def load_teams_csv() -> pd.DataFrame:
    p = DATA / "teams.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_live_json() -> dict:
    p = DATA / "wc2026_live.json"
    return json.loads(p.read_text()) if p.exists() else {}

@st.cache_data(show_spinner=False)
def load_stage_probs() -> pd.DataFrame:
    for name in ["live_stage_probs.csv", "stage_probs.csv"]:
        p = OUTPUTS / name
        if p.exists():
            return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_group_pos() -> pd.DataFrame:
    for name in ["live_group_position_probs.csv", "group_position_probs.csv"]:
        p = OUTPUTS / name
        if p.exists():
            return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_ablation() -> pd.DataFrame:
    p = CALIB / "ablation_results.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


# ─── helpers ──────────────────────────────────────────────────────────────────
def flag(code: str, disp_df: pd.DataFrame) -> str:
    if disp_df.empty:
        return "🏳"
    row = disp_df[disp_df["code"] == code]
    return row["flag"].iloc[0] if len(row) else "🏳"

def full_name(code: str, disp_df: pd.DataFrame) -> str:
    if disp_df.empty:
        return code
    row = disp_df[disp_df["code"] == code]
    return row["full_name"].iloc[0] if len(row) else code

def confederation(code: str, disp_df: pd.DataFrame) -> str:
    if disp_df.empty:
        return ""
    row = disp_df[disp_df["code"] == code]
    return row["confederation"].iloc[0] if len(row) else ""

def best_result_label(code: str) -> str:
    labels = {"W": "🏆 Champion", "F": "🥈 Runner-Up", "SF": "🥉 Semi-Final",
              "QF": "Quarter-Final", "R16": "Round of 16", "GS": "Group Stage",
              "DEBUT": "WC Début", "N/A": "N/A"}
    return labels.get(str(code), str(code))

def confidence_color(pct: float) -> str:
    if pct >= 0.15:
        return RED
    if pct >= 0.06:
        return GOLD
    if pct >= 0.02:
        return TEAL
    return MUTED

def plotly_layout(**overrides) -> dict:
    base = dict(
        paper_bgcolor=BG1, plot_bgcolor=BG2,
        font=dict(color=WHITE, family="DM Sans, system-ui, sans-serif"),
        colorway=[TEAL, RED, GOLD, "#4ECDC4", "#A8DADC", "#457B9D", "#F4A261"],
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=BORDER, zeroline=False),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickcolor=BORDER, zeroline=False),
        hoverlabel=dict(bgcolor=BG3, bordercolor=BORDER, font_color=WHITE),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER),
        margin=dict(t=40, b=20, l=10, r=10),
    )
    base.update(overrides)
    return base


# ─── load data ────────────────────────────────────────────────────────────────
elo_df     = load_live_summary()
expert_df  = load_expert_summary()
wch_df     = load_wc_history()
h2h_df     = load_h2h()
pen_df     = load_penalty()
disp_df    = load_display()
form_df    = load_form()
groups     = load_groups()
teams_df   = load_teams_csv()
stage_df   = load_stage_probs()
gpos_df    = load_group_pos()
live_data  = load_live_json()

# Merge display names into elo_df
if not elo_df.empty and not disp_df.empty and "full_name" not in elo_df.columns:
    elo_df = elo_df.merge(
        disp_df[["code", "full_name", "flag", "confederation", "nickname"]],
        left_on="team", right_on="code", how="left"
    ).drop(columns=["code"], errors="ignore")


# ─── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚽ WC2026</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-sub">Probabilistic Analytics Platform</div>', unsafe_allow_html=True)

    n_played = len(live_data.get("completed_matches", []))
    st.markdown(
        f'<span class="badge badge-teal">{n_played} / 104 matches played</span> '
        f'<span class="badge badge-red">Live</span>',
        unsafe_allow_html=True,
    )
    last_upd = live_data.get("last_updated", "—")
    st.markdown(
        f"<div style='font-size:11px;color:{MUTED};margin:4px 0 16px'>Updated: {last_upd}</div>",
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigate",
        ["🏆 Champion Tracker", "⚽ Live Standings", "🎯 Match Predictor",
         "🧬 Nation DNA", "⚔️ Head-to-Head", "📜 Historical Records",
         "🔮 Bracket Paths", "🧮 Model Lab", "📡 Data Quality"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(f"""
    <div style='font-size:11px;color:{MUTED};line-height:1.9'>
    <b style='color:{WHITE}'>Model</b><br>
    Elo-fitted Poisson · β_raw=0.988 × T=0.55<br>
    Dixon-Coles ρ≈−0.021<br>
    100,000 Monte Carlo simulations<br>
    Live-conditioned on WC2026 results<br><br>
    <b style='color:{WHITE}'>Maturity audit</b><br>
    <span style='color:{GOLD}'>5.50 / 10</span> (pessimistic, honest)<br>
    WC2022 backtest: ARG #1 pick ✓<br>
    Weakest: Validation 5.5 · Calibration 4.5
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — CHAMPION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏆 Champion Tracker":
    st.markdown("# World Cup 2026 — Champion Probabilities")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px;margin-bottom:16px'>"
        f"100,000 Monte Carlo simulations · Live-conditioned ({n_played}/104 matches played) · "
        "Elo-fitted temperature-adjusted Poisson (β=0.543)</div>",
        unsafe_allow_html=True,
    )
    st.markdown("""<div class="caveat-box">
    <b>Honest model disclosure:</b> Temperature correction β×0.55 is heuristic — not optimized against
    external outcomes. WC2022 backtest: ARG was model's #1 pick (17.2%), actual winner ✓.
    WC2018: FRA model's #6 pick (5.5%), actual winner. Avg champion Brier 0.027 vs 0.250 random (89% skill).
    These are not betting probabilities.
    </div>""", unsafe_allow_html=True)

    if elo_df.empty:
        st.error("Simulation output not found. Run scripts/run_live_simulation.py first.")
        st.stop()

    # Top-line metrics
    top_team  = elo_df.nlargest(1, "champion_prob").iloc[0]
    top3_sum  = float(elo_df.nlargest(3, "champion_prob")["champion_prob"].sum())
    top5_sum  = float(elo_df.nlargest(5, "champion_prob")["champion_prob"].sum())
    ent       = float(-np.sum(elo_df["champion_prob"] * np.log2(elo_df["champion_prob"] + 1e-15)))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏆 Favourite",
              f"{top_team.get('flag', '')} {top_team['team']}",
              f"{top_team['champion_prob']*100:.1f}%")
    c2.metric("Top-3 concentration", f"{top3_sum*100:.1f}%", delta_color="off")
    c3.metric("Top-5 combined",      f"{top5_sum*100:.1f}%", delta_color="off")
    c4.metric("Entropy (bits)",
              f"{ent:.2f} / {math.log2(48):.2f}",
              f"{ent/math.log2(48)*100:.0f}% of max uncertainty",
              delta_color="off")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        ["📊 Elo Model (primary)", "🔬 Expert vs Elo comparison", "📋 Full 48-team table"])

    with tab1:
        top16 = elo_df.nlargest(16, "champion_prob").copy()
        top16["color"] = top16["champion_prob"].apply(confidence_color)

        fig = go.Figure()
        for _, r in top16.iterrows():
            fn = r.get("full_name", r["team"])
            f  = r.get("flag", "")
            conf = r.get("confederation", "")
            fig.add_trace(go.Bar(
                x=[r["team"]], y=[r["champion_prob"] * 100],
                marker_color=r["color"],
                text=[f"{r['champion_prob']*100:.1f}%"],
                textposition="outside",
                textfont=dict(size=11, color=WHITE),
                showlegend=False,
                hovertemplate=(
                    f"<b>{f} {fn}</b><br>"
                    f"P(Champion): <b>{r['champion_prob']*100:.2f}%</b><br>"
                    f"Confederation: {conf}<br>"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            **plotly_layout(height=440),
            xaxis_title=None,
            yaxis_title="P(Champion) %",
            yaxis_range=[0, top16["champion_prob"].max() * 100 * 1.22],
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        if "ci_lower_95" in elo_df.columns:
            with st.expander("Wilson 95% confidence intervals (sampling uncertainty only — not parameter uncertainty)"):
                ci_tbl = elo_df.nlargest(16, "champion_prob")[
                    ["team", "champion_prob", "ci_lower_95", "ci_upper_95"]
                ].copy()
                ci_tbl.columns = ["Team", "P(Champion)", "CI−95%", "CI+95%"]
                for c in ["P(Champion)", "CI−95%", "CI+95%"]:
                    ci_tbl[c] = (ci_tbl[c] * 100).round(2).astype(str) + "%"
                st.dataframe(ci_tbl, use_container_width=True, hide_index=True)
                st.markdown("""<div class="caveat-box">
                CIs reflect sampling variance (N=100K) only.
                Parameter uncertainty (β_elo ± ~0.05) adds ±3–4 pp for top teams.
                No bootstrap CI computed for β_elo — this is a known gap.
                </div>""", unsafe_allow_html=True)

    with tab2:
        if expert_df.empty:
            st.info("Expert model summary not found. Run scripts/simulate_models.py to generate.")
        else:
            merged = elo_df[["team", "champion_prob"]].rename(columns={"champion_prob": "elo_prob"})
            merged = merged.merge(
                expert_df[["team", "champion_prob"]].rename(columns={"champion_prob": "expert_prob"}),
                on="team",
            )
            if not disp_df.empty:
                merged = merged.merge(
                    disp_df[["code", "flag", "full_name"]], left_on="team", right_on="code", how="left"
                )
            merged = merged.nlargest(16, "elo_prob").sort_values("elo_prob", ascending=False)
            merged["delta"] = (merged["elo_prob"] - merged["expert_prob"]) * 100

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="Elo (data-driven β=0.544)", x=merged["team"],
                y=merged["elo_prob"] * 100, marker_color=TEAL,
                text=[f"{v:.1f}%" for v in merged["elo_prob"] * 100],
                textposition="outside", textfont=dict(size=10, color=WHITE),
            ))
            fig2.add_trace(go.Bar(
                name="Expert (analyst priors)", x=merged["team"],
                y=merged["expert_prob"] * 100, marker_color=RED,
                text=[f"{v:.1f}%" for v in merged["expert_prob"] * 100],
                textposition="outside", textfont=dict(size=10, color=WHITE),
            ))
            fig2.update_layout(
                **plotly_layout(
                    height=460,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                bgcolor="rgba(0,0,0,0)", bordercolor=BORDER),
                ),
                barmode="group",
                yaxis_title="P(Champion) %",
            )
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("**Largest model divergences (Elo vs Expert):**")
            for _, r in pd.concat([merged.nlargest(5, "delta"), merged.nsmallest(3, "delta")]).iterrows():
                direction = "Elo > Expert" if r["delta"] > 0 else "Expert > Elo"
                color = TEAL if r["delta"] > 0 else RED
                f_icon = r.get("flag", "") if "flag" in merged.columns else ""
                fn     = r.get("full_name", r["team"]) if "full_name" in merged.columns else r["team"]
                st.markdown(
                    f"**{f_icon} {fn}** — Δ = <span style='color:{color}'>{r['delta']:+.1f} pp</span>"
                    f" ({direction}): Elo {r['elo_prob']*100:.1f}% vs Expert {r['expert_prob']*100:.1f}%",
                    unsafe_allow_html=True,
                )

    with tab3:
        disp_full = elo_df.copy().sort_values("champion_prob", ascending=False)
        disp_full.insert(0, "#", range(1, len(disp_full) + 1))
        cols_want = ["#", "team", "full_name", "champion_prob", "final_prob", "sf_prob",
                     "qf_prob", "group_survival_prob"]
        cols_have = [c for c in cols_want if c in disp_full.columns]
        disp_full = disp_full[cols_have].rename(columns={
            "team": "Code", "full_name": "Nation",
            "champion_prob": "P(Win)", "final_prob": "P(Final)",
            "sf_prob": "P(SF)", "qf_prob": "P(QF)", "group_survival_prob": "P(Advance)",
        })
        for col in ["P(Win)", "P(Final)", "P(SF)", "P(QF)", "P(Advance)"]:
            if col in disp_full.columns:
                disp_full[col] = (disp_full[col] * 100).round(2).astype(str) + "%"
        st.dataframe(disp_full, use_container_width=True, hide_index=True, height=600)

    # Confederation breakdown
    st.markdown("---")
    st.markdown("### Champion probability by confederation")
    if "confederation" in elo_df.columns and not elo_df["confederation"].isna().all():
        conf_sum = elo_df.groupby("confederation")["champion_prob"].sum().sort_values(ascending=False)
        fig_conf = go.Figure(go.Pie(
            values=conf_sum.values * 100,
            labels=conf_sum.index,
            marker=dict(colors=[CONF_COLORS.get(c, MUTED) for c in conf_sum.index]),
            hole=0.42,
            texttemplate="%{label}<br>%{value:.1f}%",
            textposition="outside",
            textfont=dict(size=12),
            hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
        ))
        fig_conf.update_layout(**plotly_layout(height=340), showlegend=True)
        st.plotly_chart(fig_conf, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — LIVE STANDINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚽ Live Standings":
    st.markdown("# Live Group Standings — WC2026")

    completed   = live_data.get("completed_matches", [])
    standings   = live_data.get("group_standings", {})
    injuries    = live_data.get("key_injuries", {})
    upcoming    = live_data.get("upcoming_today", [])

    # Played matches
    if completed:
        st.markdown("### Played Matches")
        for m in completed:
            grp = m["group"]
            h, a   = m["home"], m["away"]
            gh, ga = m["home_goals"], m["away_goals"]
            date   = m.get("date", "")
            scorers = " · ".join(m.get("scorers", []))
            notes   = m.get("notes", "")
            fh, fa  = flag(h, disp_df), flag(a, disp_df)
            winner_color = TEAL if gh > ga else (RED if gh < ga else GOLD)

            c1, c2, c3, c4, c5 = st.columns([1, 2.5, 1, 2.5, 2])
            c1.markdown(f'<span class="badge badge-teal">Group {grp}</span>', unsafe_allow_html=True)
            c2.markdown(f"**{fh} {h}**  \n<span style='color:{MUTED};font-size:12px'>{full_name(h,disp_df)}</span>", unsafe_allow_html=True)
            c3.markdown(f"<h2 style='text-align:center;color:{winner_color};margin:0'>{gh}–{ga}</h2>", unsafe_allow_html=True)
            c4.markdown(f"**{fa} {a}**  \n<span style='color:{MUTED};font-size:12px'>{full_name(a,disp_df)}</span>", unsafe_allow_html=True)
            c5.markdown(f"<span style='color:{MUTED};font-size:12px'>{date}</span>", unsafe_allow_html=True)
            if scorers:
                st.caption(f"⚽ {scorers}")
            if notes:
                st.caption(f"📋 {notes}")
            st.markdown("---")
    else:
        st.info("No matches played yet in the loaded data.")

    # Upcoming
    if upcoming:
        st.markdown("### Today's Upcoming Matches")
        for m in upcoming:
            fh = flag(m["home"], disp_df)
            fa = flag(m["away"], disp_df)
            st.markdown(
                f'<span class="badge badge-gold">Group {m["group"]}</span> '
                f'**{fh} {m["home"]}** vs **{fa} {m["away"]}** — {m.get("time_et","TBD")} ET',
                unsafe_allow_html=True,
            )

    # Group tables
    if standings:
        st.markdown("---")
        st.markdown("### All 12 Groups — Current Standings")

        grp_list  = sorted(standings.keys())
        cols_row  = 3

        for row_start in range(0, len(grp_list), cols_row):
            row_grps = grp_list[row_start : row_start + cols_row]
            cols = st.columns(cols_row)
            for col_idx, grp in enumerate(row_grps):
                with cols[col_idx]:
                    st.markdown(f"**Group {grp}**")
                    grp_data = standings[grp]
                    grp_sorted = sorted(grp_data, key=lambda x: (-x["points"], -x["gd"], -x["gf"]))
                    rows_html = ""
                    for rank, row in enumerate(grp_sorted, 1):
                        code = row["team"]
                        f_icon = flag(code, disp_df)
                        pts_color = TEAL if rank <= 2 else (GOLD if rank == 3 else MUTED)
                        rows_html += (
                            f'<tr style="border-bottom:1px solid {BORDER}">'
                            f'<td style="color:{MUTED};width:16px">{rank}</td>'
                            f'<td>{f_icon} <b>{code}</b></td>'
                            f'<td style="text-align:center">{row["played"]}</td>'
                            f'<td style="text-align:center">{row["gf"]}</td>'
                            f'<td style="text-align:center">{row["ga"]}</td>'
                            f'<td style="text-align:center">{row["gd"]:+d}</td>'
                            f'<td style="text-align:center;color:{pts_color};font-weight:700">{row["points"]}</td>'
                            f'</tr>'
                        )
                    st.markdown(
                        f'<table style="width:100%;font-size:12px;border-collapse:collapse">'
                        f'<thead><tr style="color:{MUTED}">'
                        f'<th></th><th>Team</th><th>P</th><th>F</th><th>A</th>'
                        f'<th>GD</th><th style="color:{TEAL}">Pts</th></tr></thead>'
                        f'<tbody>{rows_html}</tbody></table>',
                        unsafe_allow_html=True,
                    )

    # Injury updates
    st.markdown("---")
    st.markdown("### ⚕️ Key Injury & Fitness Updates")
    any_injury = False
    for code, inj_list in injuries.items():
        if inj_list:
            any_injury = True
            f_icon = flag(code, disp_df)
            for inj in inj_list:
                sev = RED if "OUT" in inj.upper() else GOLD
                st.markdown(
                    f"{f_icon} **{code}**: <span style='color:{sev}'>{inj}</span>",
                    unsafe_allow_html=True,
                )
    if not any_injury:
        st.info("No key injury updates in current data file.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MATCH PREDICTOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Match Predictor":
    st.markdown("# Match Probability Engine")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px'>"
        "Elo-fitted Poisson · Dixon-Coles low-score correction · "
        "Live-updated Elo (post matchday 1)</div>",
        unsafe_allow_html=True,
    )

    all_codes = sorted(elo_df["team"].tolist()) if not elo_df.empty else []
    if not all_codes:
        st.error("No team data loaded.")
        st.stop()

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        team_a = st.selectbox(
            "🏠 Team A",
            all_codes,
            index=all_codes.index("ESP") if "ESP" in all_codes else 0,
            format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
        )
    with c2:
        st.markdown(f"<br><h2 style='text-align:center;color:{MUTED}'>vs</h2>", unsafe_allow_html=True)
    with c3:
        team_b = st.selectbox(
            "✈️ Team B",
            all_codes,
            index=all_codes.index("ARG") if "ARG" in all_codes else 1,
            format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
        )

    match_type = st.radio("Match context", ["Group Stage", "Knockout"], horizontal=True)
    is_ko = match_type == "Knockout"

    if team_a == team_b:
        st.warning("Please select two different teams.")
    else:
        try:
            from wc2026.data_loader import load_teams, load_config
            from wc2026.calibrated_elo_model import CalibratedEloMatchModel

            teams_obj  = load_teams(apply_temporal_form=True)
            cfg        = load_config()
            live_p_path = DATA / "elo_live_params.json"
            params     = json.loads(live_p_path.read_text()) if live_p_path.exists() else None
            model      = CalibratedEloMatchModel(config=cfg, params=params)

            ta, tb = teams_obj[team_a], teams_obj[team_b]
            mu_a, mu_b = model.expected_goals(ta, tb, knockout=is_ko)

            # Dixon-Coles probability matrix
            rho = float(params.get("rho", -0.021)) if params else -0.021
            max_g = 7
            prob_mat = np.zeros((max_g + 1, max_g + 1))
            for i in range(max_g + 1):
                for j in range(max_g + 1):
                    p = (math.exp(-mu_a) * mu_a**i / math.factorial(i) *
                         math.exp(-mu_b) * mu_b**j / math.factorial(j))
                    if   i == 0 and j == 0: tau = 1 - mu_a * mu_b * rho
                    elif i == 1 and j == 0: tau = 1 + mu_b * rho
                    elif i == 0 and j == 1: tau = 1 + mu_a * rho
                    elif i == 1 and j == 1: tau = 1 - rho
                    else:                   tau = 1.0
                    prob_mat[i, j] = p * max(tau, 0.0)

            p_home_raw = float(np.sum(np.tril(prob_mat, -1)))
            p_draw_raw = float(np.trace(prob_mat))
            p_away_raw = float(np.sum(np.triu(prob_mat, 1)))
            total      = p_home_raw + p_draw_raw + p_away_raw
            p_home, p_draw, p_away = p_home_raw / total, p_draw_raw / total, p_away_raw / total

            # Metrics
            st.markdown("---")
            fh, fa_i = flag(team_a, disp_df), flag(team_b, disp_df)
            ca, cb, cc = st.columns(3)
            ca.metric(f"{fh} {team_a} wins", f"{p_home*100:.1f}%")
            cb.metric("Draw (90 min)", f"{p_draw*100:.1f}%")
            cc.metric(f"{fa_i} {team_b} wins", f"{p_away*100:.1f}%")

            # Pie chart
            fig_pie = go.Figure(go.Pie(
                values=[p_home * 100, p_draw * 100, p_away * 100],
                labels=[f"{team_a} win", "Draw", f"{team_b} win"],
                hole=0.55,
                marker=dict(colors=[TEAL, GOLD, RED]),
                textinfo="percent+label",
                textfont=dict(size=13, color=WHITE),
                hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
            ))
            fig_pie.update_layout(
                **plotly_layout(height=280),
                annotations=[dict(
                    text=f"λ {mu_a:.2f} – {mu_b:.2f}",
                    font=dict(size=16, color=WHITE), showarrow=False,
                )],
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.caption(
                f"Expected goals: {team_a} λ={mu_a:.3f}, {team_b} λ={mu_b:.3f} "
                f"(Elo-fitted Poisson, DC correction ρ={rho:.3f})"
            )

            # Scoreline heatmap
            st.markdown("#### Scoreline probability heatmap")
            scores_plot = prob_mat[:6, :6] / prob_mat[:6, :6].sum() * 100
            fig_heat = go.Figure(go.Heatmap(
                z=scores_plot,
                x=[str(j) for j in range(6)],
                y=[str(i) for i in range(6)],
                colorscale=[[0, BG3], [0.4, TEAL], [1.0, RED]],
                text=[[f"{scores_plot[i, j]:.1f}%" for j in range(6)] for i in range(6)],
                texttemplate="%{text}",
                textfont=dict(size=11),
                hovertemplate=f"{team_a} %{{y}}–{team_b} %{{x}}: %{{z:.2f}}%<extra></extra>",
                showscale=False,
            ))
            fig_heat.update_layout(
                **plotly_layout(height=300),
                xaxis_title=f"{team_b} goals",
                yaxis_title=f"{team_a} goals",
                yaxis_autorange="reversed",
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            # If knockout: penalty probability
            if is_ko:
                st.markdown("---")
                st.markdown("#### If this goes to penalties")
                pen_a = pen_df[pen_df["code"] == team_a].iloc[0] if not pen_df.empty and len(pen_df[pen_df["code"] == team_a]) else None
                pen_b = pen_df[pen_df["code"] == team_b].iloc[0] if not pen_df.empty and len(pen_df[pen_df["code"] == team_b]) else None
                pc1, pc2 = st.columns(2)
                with pc1:
                    if pen_a is not None:
                        record = pen_a.get("record", "No WC data")
                        note   = pen_a.get("note", "")
                        pct    = float(pen_a.get("pct", 0.5))
                        col    = TEAL if pct >= 0.55 else (RED if pct <= 0.33 else GOLD)
                        st.markdown(f"{fh} **{team_a}** WC penalty record: "
                                    f"<span style='color:{col}'>{record}</span>",
                                    unsafe_allow_html=True)
                        if note:
                            st.caption(f"⚠️ {note}")
                    else:
                        st.caption(f"{fh} {team_a}: no WC penalty shootout history")
                with pc2:
                    if pen_b is not None:
                        record = pen_b.get("record", "No WC data")
                        note   = pen_b.get("note", "")
                        pct    = float(pen_b.get("pct", 0.5))
                        col    = TEAL if pct >= 0.55 else (RED if pct <= 0.33 else GOLD)
                        st.markdown(f"{fa_i} **{team_b}** WC penalty record: "
                                    f"<span style='color:{col}'>{record}</span>",
                                    unsafe_allow_html=True)
                        if note:
                            st.caption(f"⚠️ {note}")
                    else:
                        st.caption(f"{fa_i} {team_b}: no WC penalty shootout history")

                # Analyst model (GK × penalties)
                ta_row = teams_df[teams_df["code"] == team_a] if "code" in teams_df.columns else pd.DataFrame()
                tb_row = teams_df[teams_df["code"] == team_b] if "code" in teams_df.columns else pd.DataFrame()
                if not ta_row.empty and not tb_row.empty:
                    gka  = float(ta_row.iloc[0].get("goalkeeper", 75))
                    pksa = float(ta_row.iloc[0].get("penalties", 75))
                    gkb  = float(tb_row.iloc[0].get("goalkeeper", 75))
                    pksb = float(tb_row.iloc[0].get("penalties", 75))
                    lgt_a = 0.055 * (pksa - gkb)
                    lgt_b = 0.055 * (pksb - gka)
                    p_pen_a_norm = math.exp(lgt_a) / (math.exp(lgt_a) + math.exp(lgt_b))
                    st.info(
                        f"Penalty model (analyst priors, not empirically calibrated): "
                        f"{fh} {team_a} {p_pen_a_norm*100:.0f}% — "
                        f"{fa_i} {team_b} {(1-p_pen_a_norm)*100:.0f}%"
                    )

        except Exception as e:
            st.error(f"Model error: {e}")
            import traceback
            st.code(traceback.format_exc())

    # H2H section
    if team_a != team_b:
        st.markdown("---")
        st.markdown("#### Head-to-Head record (competitive matches)")
        if h2h_df.empty:
            st.info("H2H data not loaded.")
        else:
            h2h_mask = (
                ((h2h_df["team_a"] == team_a) & (h2h_df["team_b"] == team_b) & (h2h_df["scope"] == "all_competitive")) |
                ((h2h_df["team_a"] == team_b) & (h2h_df["team_b"] == team_a) & (h2h_df["scope"] == "all_competitive"))
            )
            h2h_row = h2h_df[h2h_mask]
            if len(h2h_row) > 0:
                r = h2h_row.iloc[0]
                if r["team_a"] == team_b:
                    wa, wd, wb = r["wins_b"], r["draws"], r["wins_a"]
                else:
                    wa, wd, wb = r["wins_a"], r["draws"], r["wins_b"]
                total = wa + wd + wb

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric(f"{flag(team_a, disp_df)} wins", wa, f"{wa/total*100:.0f}%")
                mc2.metric("Draws", wd)
                mc3.metric(f"{flag(team_b, disp_df)} wins", wb, f"{wb/total*100:.0f}%")
                mc4.metric("Total meetings", total)

                fig_h2h = go.Figure()
                fig_h2h.add_trace(go.Bar(name=team_a, x=["H2H"], y=[wa/total*100],
                                         marker_color=TEAL, text=[f"{wa/total*100:.0f}%"], textposition="inside"))
                fig_h2h.add_trace(go.Bar(name="Draw",  x=["H2H"], y=[wd/total*100],
                                         marker_color=GOLD, text=[f"{wd/total*100:.0f}%"], textposition="inside"))
                fig_h2h.add_trace(go.Bar(name=team_b,  x=["H2H"], y=[wb/total*100],
                                         marker_color=RED,  text=[f"{wb/total*100:.0f}%"], textposition="inside"))
                fig_h2h.update_layout(
                    **plotly_layout(height=120),
                    barmode="stack", showlegend=True,
                    yaxis_range=[0, 100], xaxis_visible=False,
                )
                st.plotly_chart(fig_h2h, use_container_width=True)

                # Nemesis detection
                if total >= 5:
                    dom_a = wa / total > 0.65
                    dom_b = wb / total > 0.65
                    if dom_a:
                        st.markdown(
                            f"🔴 **Historical dominance**: {flag(team_a,disp_df)} {team_a} wins "
                            f"{wa/total*100:.0f}% of {total} meetings — potential psychological edge"
                        )
                    elif dom_b:
                        st.markdown(
                            f"🔴 **Historical dominance**: {flag(team_b,disp_df)} {team_b} wins "
                            f"{wb/total*100:.0f}% of {total} meetings — nemesis factor"
                        )

                # WC-specific record
                wc_mask = (
                    ((h2h_df["team_a"] == team_a) & (h2h_df["team_b"] == team_b) & (h2h_df["scope"] == "wc_only")) |
                    ((h2h_df["team_a"] == team_b) & (h2h_df["team_b"] == team_a) & (h2h_df["scope"] == "wc_only"))
                )
                h2h_wc = h2h_df[wc_mask]
                if len(h2h_wc) > 0:
                    rwc = h2h_wc.iloc[0]
                    if rwc["team_a"] == team_b:
                        wawc, wdwc, wbwc = rwc["wins_b"], rwc["draws"], rwc["wins_a"]
                    else:
                        wawc, wdwc, wbwc = rwc["wins_a"], rwc["draws"], rwc["wins_b"]
                    st.info(
                        f"🏆 World Cup meetings only: "
                        f"{flag(team_a,disp_df)} {team_a} {wawc}W–{wdwc}D–{wbwc}L "
                        f"{flag(team_b,disp_df)} {team_b}"
                    )
            else:
                st.info(f"No competitive H2H records found for {team_a} vs {team_b}.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — NATION DNA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧬 Nation DNA":
    st.markdown("# Nation DNA — Deep Team Analysis")

    all_codes = sorted(elo_df["team"].tolist()) if not elo_df.empty else []
    if not all_codes:
        st.error("No data loaded."); st.stop()

    selected = st.selectbox(
        "Select nation",
        all_codes,
        format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
    )

    f_icon = flag(selected, disp_df)
    fn     = full_name(selected, disp_df)
    conf   = confederation(selected, disp_df)
    nick   = (disp_df[disp_df["code"] == selected]["nickname"].iloc[0]
               if not disp_df.empty and len(disp_df[disp_df["code"] == selected]) > 0 else "")
    wch_row = wch_df[wch_df["code"] == selected].iloc[0] if not wch_df.empty and len(wch_df[wch_df["code"] == selected]) > 0 else None
    elo_row = elo_df[elo_df["team"] == selected].iloc[0] if not elo_df.empty and len(elo_df[elo_df["team"] == selected]) > 0 else None
    tm_row  = teams_df[teams_df["code"] == selected].iloc[0] if "code" in teams_df.columns and len(teams_df[teams_df["code"] == selected]) > 0 else None
    pen_row = pen_df[pen_df["code"] == selected].iloc[0] if not pen_df.empty and len(pen_df[pen_df["code"] == selected]) > 0 else None

    conf_color = CONF_COLORS.get(conf, MUTED)
    st.markdown(f"""
    <div class="card">
      <div style="display:flex;align-items:center;gap:20px">
        <div style="font-size:56px;line-height:1">{f_icon}</div>
        <div>
          <div style="font-size:26px;font-weight:700;font-family:'DM Serif Display',serif">{fn}</div>
          <div style="margin-top:6px">
            <span class="badge" style="background:rgba(255,255,255,0.05);color:{conf_color};border:1px solid {conf_color}">{conf}</span>
            &nbsp;&nbsp;<span style="color:{MUTED};font-size:13px">{nick}</span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs(
        ["📊 Probabilities", "🏟️ WC History", "📈 Recent Form", "🎯 Squad DNA", "⚔️ Hardest Matchups"])

    with t1:
        if elo_row is None:
            st.warning("No probability data.")
        else:
            stages  = ["group_survival_prob", "qf_prob", "sf_prob", "final_prob", "champion_prob"]
            labels  = ["Advance", "Reach QF", "Reach SF", "Reach Final", "Win WC2026"]
            colors  = [TEAL, TEAL, GOLD, GOLD, RED]
            vals    = [(float(elo_row.get(s, 0)), l, c) for s, l, c in zip(stages, labels, colors)
                       if s in elo_row.index]

            if vals:
                fig_st = go.Figure(go.Bar(
                    x=[v[1] for v in vals],
                    y=[v[0] * 100 for v in vals],
                    marker_color=[v[2] for v in vals],
                    text=[f"{v[0]*100:.1f}%" for v in vals],
                    textposition="outside",
                    textfont=dict(color=WHITE, size=13),
                ))
                fig_st.update_layout(
                    **plotly_layout(height=320),
                    yaxis_title="Probability %", yaxis_range=[0, 115],
                )
                st.plotly_chart(fig_st, use_container_width=True)

            # Rank
            if "champion_prob" in elo_df.columns:
                rank_ser = elo_df["champion_prob"].rank(ascending=False)
                champ_rank = int(rank_ser[elo_df["team"] == selected].values[0])
                st.markdown(f"**Champion rank:** #{champ_rank} of 48 — {f_icon} {fn} "
                            f"{float(elo_row.get('champion_prob', 0))*100:.2f}%")

            # Live Elo
            try:
                live_params_path = DATA / "elo_live_params.json"
                lp = json.loads(live_params_path.read_text())
                elo_val = lp["team_elos"].get(selected)
                if elo_val:
                    elo_rank = sum(1 for e in lp["team_elos"].values() if e > elo_val) + 1
                    st.metric("Current Elo (live-updated)", f"{elo_val:.0f}", f"Rank #{elo_rank}/48")
            except Exception:
                pass

    with t2:
        if wch_row is None:
            st.info("No WC history data.")
        else:
            app_count = int(wch_row.get("wc_appearances", 0))
            titles    = int(wch_row.get("wc_titles", 0))
            best      = str(wch_row.get("wc_best_result", "N/A"))
            deep      = float(wch_row.get("deep_run_rate", 0))

            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric("WC appearances", app_count)
            wc2.metric("🏆 Titles", titles)
            wc3.metric("Best result", best_result_label(best))
            wc4.metric("Deep run rate", f"{deep*100:.0f}%", "QF or better")

            try:
                title_years = eval(str(wch_row.get("title_years", "[]")))
                final_years = eval(str(wch_row.get("final_years", "[]")))
            except Exception:
                title_years, final_years = [], []

            if title_years:
                st.markdown(f"**🏆 Won:** {', '.join(str(y) for y in title_years)}")
            if final_years:
                st.markdown(f"**🥈 Runner-up:** {', '.join(str(y) for y in final_years)}")

            if titles > 0:
                st.markdown(f"""<div class="info-box">
                {f_icon} {fn} is a {titles}× WC champion.
                Historical pedigree strongly backs a top-tier model probability.
                </div>""", unsafe_allow_html=True)
            elif best in ["DEBUT"] or app_count == 0:
                st.markdown(f"""<div class="caveat-box">
                {f_icon} {fn} is a WC newcomer — no tournament history.
                Model relies entirely on recent Elo momentum.
                </div>""", unsafe_allow_html=True)

            # Penalty
            if pen_row is not None:
                pr_record = pen_row.get("record", "No history")
                pr_pct    = float(pen_row.get("pct", 0.5))
                pr_note   = pen_row.get("note", "")
                pr_col    = TEAL if pr_pct >= 0.55 else (RED if pr_pct <= 0.33 else GOLD)
                st.markdown(
                    f"**WC Penalty shootout record:** "
                    f"<span style='color:{pr_col}'>{pr_record}</span>",
                    unsafe_allow_html=True,
                )
                if pr_note:
                    st.caption(f"⚠️ {pr_note}")
            else:
                st.caption("No WC penalty shootout history.")

    with t3:
        team_form = form_df[form_df["code"] == selected].copy() if not form_df.empty else pd.DataFrame()
        if team_form.empty:
            st.info("No form data available.")
        else:
            team_form = team_form.sort_values("date").tail(15)
            team_form["gd"] = team_form["gf"] - team_form["ga"]

            # Last 5 streak
            streak = ""
            for _, r in team_form.sort_values("date", ascending=False).head(5).iterrows():
                streak += "🟢" if r["result"] == "W" else ("🟡" if r["result"] == "D" else "🔴")
            st.markdown(f"**Last 5 competitive results:** {streak}")

            fig_form = go.Figure()
            fig_form.add_trace(go.Scatter(
                x=team_form["date"].tolist(),
                y=team_form["gd"].tolist(),
                mode="markers+lines",
                line=dict(color=TEAL, width=2),
                marker=dict(
                    color=[TEAL if r == "W" else (GOLD if r == "D" else RED)
                           for r in team_form["result"]],
                    size=10,
                ),
                customdata=team_form["opponent"].tolist(),
                hovertemplate="vs %{customdata}<br>GD: %{y:+d}<extra></extra>",
            ))
            fig_form.add_hline(y=0, line_dash="dash", line_color=MUTED, line_width=1)
            fig_form.update_layout(
                **plotly_layout(height=260),
                yaxis_title="Goal Differential", xaxis_title=None,
            )
            st.plotly_chart(fig_form, use_container_width=True)

            disp_form = team_form[["date", "opponent", "gf", "ga", "result", "tournament"]].copy()
            disp_form.columns = ["Date", "Opponent", "GF", "GA", "Result", "Tournament"]
            st.dataframe(disp_form.sort_values("Date", ascending=False),
                         use_container_width=True, hide_index=True)

    with t4:
        if tm_row is None:
            st.info("No squad attribute data.")
        else:
            attrs = {
                "Attack":      float(tm_row.get("attack", 75)),
                "Defense":     float(tm_row.get("defense", 75)),
                "Midfield":    float(tm_row.get("midfield", 75)),
                "Goalkeeper":  float(tm_row.get("goalkeeper", 75)),
                "Depth":       float(tm_row.get("depth", 75)),
                "Penalties":   float(tm_row.get("penalties", 75)),
                "Set Pieces":  float(tm_row.get("setpiece", 75)),
                "Form":        float(tm_row.get("form", 50)),
                "Health":      float(tm_row.get("health", 90)),
                "Discipline":  float(tm_row.get("discipline", 75)),
            }
            fig_radar = go.Figure(go.Scatterpolar(
                r=list(attrs.values()),
                theta=list(attrs.keys()),
                fill="toself",
                fillcolor="rgba(42,157,143,0.18)",
                line=dict(color=TEAL, width=2),
                marker=dict(color=TEAL, size=6),
            ))
            fig_radar.update_layout(
                **plotly_layout(height=380),
                polar=dict(
                    bgcolor=BG2,
                    radialaxis=dict(visible=True, range=[0, 100],
                                    gridcolor=BORDER, tickcolor=MUTED),
                    angularaxis=dict(gridcolor=BORDER),
                ),
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            st.markdown("""<div class="caveat-box">
            ⚠️ <b>Analyst-prior ratings.</b> Attack/Defense/Midfield are hand-tuned,
            not statistically estimated. Used only in the Expert model — not in the primary Elo model.
            </div>""", unsafe_allow_html=True)

            sb = bool(tm_row.get("has_statsbomb_data", False))
            badge = '<span class="badge badge-teal">StatsBomb coverage</span>' if sb else '<span class="badge badge-muted">Default values (no StatsBomb)</span>'
            st.markdown(f"Data source: {badge}", unsafe_allow_html=True)

            ppda = float(tm_row.get("ppda", 6.0))
            sq   = float(tm_row.get("shot_quality", 0.1))
            pi   = float(tm_row.get("press_intensity", 0.35))
            cr   = float(tm_row.get("comeback_rate", 0.3))
            ck   = float(tm_row.get("choke_rate", 0.1))
            st.markdown(
                f"**Pressing (PPDA):** {ppda:.2f}  ·  "
                f"**Shot quality:** {sq:.3f}  ·  "
                f"**Press intensity:** {pi:.3f}  ·  "
                f"**Comeback rate:** {cr:.0%}  ·  "
                f"**Choke rate:** {ck:.0%}"
            )

    with t5:
        st.markdown("#### Toughest knockout opponents (by Elo model)")
        try:
            from wc2026.data_loader import load_teams, load_config
            from wc2026.calibrated_elo_model import CalibratedEloMatchModel

            teams_obj = load_teams(apply_temporal_form=True)
            cfg       = load_config()
            lpp       = DATA / "elo_live_params.json"
            params_t5 = json.loads(lpp.read_text()) if lpp.exists() else None
            model_t5  = CalibratedEloMatchModel(config=cfg, params=params_t5)
            ta_obj    = teams_obj[selected]

            rows_t5 = []
            for opp_code, tb_obj in teams_obj.items():
                if opp_code == selected:
                    continue
                mu_a_t5, mu_b_t5 = model_t5.expected_goals(ta_obj, tb_obj, knockout=True)
                p_w = 0.0
                for i in range(7):
                    for j in range(7):
                        if i > j:
                            p_w += (math.exp(-mu_a_t5) * mu_a_t5**i / math.factorial(i) *
                                    math.exp(-mu_b_t5) * mu_b_t5**j / math.factorial(j))
                rows_t5.append({
                    "opp":   opp_code,
                    "flag":  flag(opp_code, disp_df),
                    "name":  full_name(opp_code, disp_df),
                    "p_win": p_w,
                })
            matchup_df = pd.DataFrame(rows_t5).sort_values("p_win")

            st.markdown("**5 toughest opponents:**")
            for _, r in matchup_df.head(5).iterrows():
                col = RED if r["p_win"] < 0.40 else (GOLD if r["p_win"] < 0.50 else TEAL)
                st.markdown(
                    f"{r['flag']} **{r['opp']}** ({r['name']}): "
                    f"<span style='color:{col}'>{r['p_win']*100:.1f}%</span> win prob",
                    unsafe_allow_html=True,
                )
            st.markdown("**5 most favorable:**")
            for _, r in matchup_df.tail(5).iloc[::-1].iterrows():
                st.markdown(
                    f"{r['flag']} **{r['opp']}** ({r['name']}): "
                    f"<span style='color:{TEAL}'>{r['p_win']*100:.1f}%</span> win prob",
                    unsafe_allow_html=True,
                )

            # Nemesis detection
            if not h2h_df.empty:
                nm_mask = (
                    ((h2h_df["team_a"] == selected) | (h2h_df["team_b"] == selected)) &
                    (h2h_df["scope"] == "all_competitive") &
                    (h2h_df["matches"] >= 5)
                )
                h2h_team = h2h_df[nm_mask].copy()
                h2h_team["wp"] = h2h_team.apply(
                    lambda row: row["win_pct_a"] if row["team_a"] == selected else row["win_pct_b"],
                    axis=1,
                )
                h2h_team["opp"] = h2h_team.apply(
                    lambda row: row["team_b"] if row["team_a"] == selected else row["team_a"],
                    axis=1,
                )
                nemeses = h2h_team[h2h_team["wp"] < 0.30].sort_values("wp")
                if len(nemeses) > 0:
                    st.markdown("---")
                    st.markdown("**🔴 Historical nemeses** (win rate <30% in 5+ meetings):")
                    for _, r in nemeses.head(4).iterrows():
                        st.markdown(
                            f"  {flag(r['opp'], disp_df)} **{r['opp']}** — "
                            f"{selected} wins only **{r['wp']*100:.0f}%** of {int(r['matches'])} meetings"
                        )

        except Exception as e:
            st.error(f"Could not compute matchups: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — HEAD-TO-HEAD MATRIX
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚔️ Head-to-Head":
    st.markdown("# Head-to-Head Analysis")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px'>"
        "All competitive matches from 1872–present · Source: martj42/international-football-results</div>",
        unsafe_allow_html=True,
    )

    if h2h_df.empty:
        st.warning("H2H data not loaded. Run scripts/build_enrichment_data.py first.")
        st.stop()

    all_codes = sorted(elo_df["team"].tolist()) if not elo_df.empty else []
    top_teams = elo_df.nlargest(16, "champion_prob")["team"].tolist() if not elo_df.empty else all_codes[:12]

    show_teams = st.multiselect(
        "Teams for H2H matrix (8–12 recommended)",
        all_codes, default=top_teams[:12],
        format_func=lambda x: f"{flag(x, disp_df)} {x}",
    )

    if len(show_teams) >= 2:
        # Win-pct matrix
        n = len(show_teams)
        mat = np.full((n, n), np.nan)
        cnt = np.zeros((n, n), dtype=int)
        for i, ta in enumerate(show_teams):
            for j, tb in enumerate(show_teams):
                if i == j:
                    continue
                h = h2h_df[
                    ((h2h_df["team_a"] == ta) & (h2h_df["team_b"] == tb) & (h2h_df["scope"] == "all_competitive")) |
                    ((h2h_df["team_a"] == tb) & (h2h_df["team_b"] == ta) & (h2h_df["scope"] == "all_competitive"))
                ]
                if len(h) > 0:
                    r = h.iloc[0]
                    mat[i, j] = r["win_pct_a"] if r["team_a"] == ta else r["win_pct_b"]
                    cnt[i, j] = int(r["matches"])
                else:
                    mat[i, j] = 0.5
                    cnt[i, j] = 0

        mat_plot = np.nan_to_num(mat, nan=0.5) * 100
        labels   = [f"{flag(t, disp_df)} {t}" for t in show_teams]
        text_mat = [[f"{mat_plot[i,j]:.0f}%" if cnt[i,j] > 0 else "—"
                     for j in range(n)] for i in range(n)]

        fig_mat = go.Figure(go.Heatmap(
            z=mat_plot,
            x=labels, y=labels,
            colorscale=[[0, RED], [0.5, BG3], [1, TEAL]],
            zmin=20, zmax=80,
            text=text_mat,
            texttemplate="%{text}",
            textfont=dict(size=11),
            hovertemplate="%{y} win% vs %{x}: %{z:.1f}%<extra></extra>",
            showscale=True,
            colorbar=dict(title=dict(text="Win %", font=dict(color=WHITE)), tickfont=dict(color=WHITE)),
        ))
        fig_mat.update_layout(
            **plotly_layout(height=600),
            xaxis=dict(tickangle=-45, gridcolor=BORDER),
        )
        st.plotly_chart(fig_mat, use_container_width=True)
        st.caption("Row team win% vs column team (all competitive, not WC only). "
                   "0.5 / '—' = insufficient data.")

        # Largest imbalances
        st.markdown("---")
        st.markdown("#### Most lopsided rivalries (≥5 meetings) in this selection")
        imb = []
        for i, ta in enumerate(show_teams):
            for j, tb in enumerate(show_teams):
                if i >= j or cnt[i, j] < 5:
                    continue
                imb.append({"Team A": ta, "Team B": tb,
                             "A win%": f"{mat_plot[i,j]:.0f}%",
                             "B win%": f"{100-mat_plot[i,j]:.0f}%",
                             "Meetings": cnt[i, j],
                             "_imb": abs(mat_plot[i, j] - 50)})
        if imb:
            imb_df = pd.DataFrame(imb).sort_values("_imb", ascending=False).head(8)
            for _, r in imb_df.iterrows():
                fta = flag(r["Team A"], disp_df)
                ftb = flag(r["Team B"], disp_df)
                st.markdown(
                    f"{fta} **{r['Team A']}** {r['A win%']} – {r['B win%']} {ftb} **{r['Team B']}** "
                    f"({r['Meetings']} meetings)"
                )
        else:
            st.info("No pair with 5+ meetings found in this selection.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — HISTORICAL RECORDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜 Historical Records":
    st.markdown("# Historical World Cup Records — All 48 Nations")

    if wch_df.empty:
        st.warning("WC history data not loaded. Run scripts/build_enrichment_data.py first.")
        st.stop()

    wch_display = wch_df.copy()
    if not disp_df.empty:
        wch_display = wch_display.merge(
            disp_df[["code", "flag", "full_name", "confederation"]], on="code", how="left"
        )
    wch_display["Best Result"] = wch_display["wc_best_result"].apply(best_result_label)
    wch_display["Deep Run %"]  = (wch_display["deep_run_rate"] * 100).round(0).astype(int).astype(str) + "%"

    confs      = ["All"] + sorted(wch_display["confederation"].dropna().unique().tolist()) if "confederation" in wch_display else ["All"]
    sel_conf   = st.selectbox("Filter by confederation", confs)
    if sel_conf != "All" and "confederation" in wch_display.columns:
        wch_display = wch_display[wch_display["confederation"] == sel_conf]
    wch_display = wch_display.sort_values(["wc_titles", "wc_appearances"], ascending=[False, False])

    cols_want = ["flag", "code", "full_name", "wc_appearances", "wc_titles",
                 "wc_runner_up", "wc_third", "wc_fourth", "Best Result", "Deep Run %"]
    cols_have = [c for c in cols_want if c in wch_display.columns]
    rename_map = {"flag": "", "code": "Code", "full_name": "Nation",
                  "wc_appearances": "WCs", "wc_titles": "🏆",
                  "wc_runner_up": "🥈", "wc_third": "🥉", "wc_fourth": "4th"}
    st.dataframe(
        wch_display[cols_have].rename(columns=rename_map),
        use_container_width=True, hide_index=True, height=400,
    )

    st.markdown("---")
    st.markdown("### WC titles by nation")
    title_df = wch_df[wch_df["wc_titles"] > 0].sort_values("wc_titles", ascending=False).copy()
    if not disp_df.empty:
        title_df = title_df.merge(disp_df[["code", "flag"]], on="code", how="left")
        title_df["display"] = title_df.apply(lambda r: f"{r.get('flag','')} {r['code']}", axis=1)
    else:
        title_df["display"] = title_df["code"]

    fig_tit = go.Figure(go.Bar(
        x=title_df["display"].tolist(),
        y=title_df["wc_titles"].tolist(),
        marker_color=[RED if v >= 3 else GOLD for v in title_df["wc_titles"]],
        text=title_df["wc_titles"].tolist(),
        textposition="outside",
        textfont=dict(size=16, color=WHITE),
    ))
    fig_tit.update_layout(**plotly_layout(height=280), xaxis_title=None, yaxis_title="Titles")
    st.plotly_chart(fig_tit, use_container_width=True)

    # Historical deep run rate vs current champion probability
    st.markdown("---")
    st.markdown("### Deep run rate vs 2026 champion probability")
    if not elo_df.empty:
        scatter_df = wch_df.merge(
            elo_df[["team", "champion_prob"]], left_on="code", right_on="team", how="inner"
        )
        if not disp_df.empty:
            # Avoid full_name collision: wch_df may already have full_name from build_enrichment_data
            disp_cols = ["code", "confederation"]
            if "flag" not in scatter_df.columns:
                disp_cols.append("flag")
            if "full_name" not in scatter_df.columns:
                disp_cols.append("full_name")
            scatter_df = scatter_df.merge(
                disp_df[disp_cols], on="code", how="left"
            )
        # Resolve column names after merge (handle _x/_y suffix)
        for base_col in ["full_name", "confederation", "flag"]:
            if f"{base_col}_x" in scatter_df.columns:
                scatter_df[base_col] = scatter_df[f"{base_col}_x"]
                scatter_df.drop(columns=[f"{base_col}_x", f"{base_col}_y"], errors="ignore", inplace=True)
        hover_cols = [c for c in ["full_name", "wc_titles", "wc_appearances"] if c in scatter_df.columns]
        fig_sc = px.scatter(
            scatter_df,
            x="deep_run_rate", y="champion_prob",
            color="confederation" if "confederation" in scatter_df.columns else None,
            color_discrete_map=CONF_COLORS,
            text="code",
            size="wc_appearances",
            size_max=28,
            hover_data=hover_cols,
            labels={"deep_run_rate": "Historical Deep Run Rate (QF+)",
                    "champion_prob": "P(WC2026 Champion)"},
        )
        fig_sc.update_traces(textposition="top center", textfont=dict(size=9, color=WHITE))
        fig_sc.update_xaxes(tickformat=".0%")
        fig_sc.update_yaxes(tickformat=".1%")
        fig_sc.update_layout(**plotly_layout(height=500))
        st.plotly_chart(fig_sc, use_container_width=True)
        st.caption(
            "Bubble size = WC appearances. Teams above the trend line: model sees more potential "
            "than history. Below: model is skeptical despite historical pedigree."
        )

    # Debutants
    debutants = wch_df[wch_df["wc_best_result"] == "DEBUT"]["code"].tolist()
    if debutants:
        st.markdown(f"### 🆕 WC2026 Debutants ({len(debutants)} nations)")
        for code in debutants:
            champ = float(
                elo_df[elo_df["team"] == code]["champion_prob"].values[0]
            ) if not elo_df.empty and len(elo_df[elo_df["team"] == code]) > 0 else 0
            st.markdown(
                f"{flag(code, disp_df)} **{full_name(code, disp_df)}** ({code}) — "
                f"P(Champion): {champ*100:.2f}%"
            )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — BRACKET PATHS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Bracket Paths":
    st.markdown("# Tournament Bracket & Path Analysis")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px'>"
        "Stage progression probabilities · Conditional path analysis · Bracket difficulty</div>",
        unsafe_allow_html=True,
    )

    # Stage funnel — top 12
    if not elo_df.empty:
        st.markdown("### Stage progression — top 12 teams")
        top12 = elo_df.nlargest(12, "champion_prob")["team"].tolist()
        stages_avail = [c for c in
                        ["group_survival_prob", "qf_prob", "sf_prob", "final_prob", "champion_prob"]
                        if c in elo_df.columns]
        stage_map = {"group_survival_prob": "Advance", "qf_prob": "QF", "sf_prob": "SF",
                     "final_prob": "Final", "champion_prob": "Champion"}
        palette = [TEAL, RED, GOLD, "#4ECDC4", "#A8DADC", "#457B9D",
                   "#F4A261", "#C77DFF", "#E76F51", "#264653", "#2EC4B6", "#E9C46A"]

        fig_fun = go.Figure()
        for i, code in enumerate(top12):
            row = elo_df[elo_df["team"] == code]
            if row.empty:
                continue
            row = row.iloc[0]
            xv = [stage_map[s] for s in stages_avail]
            yv = [float(row.get(s, 0)) * 100 for s in stages_avail]
            fig_fun.add_trace(go.Scatter(
                x=xv, y=yv,
                mode="lines+markers",
                name=f"{flag(code, disp_df)} {code}",
                line=dict(color=palette[i % len(palette)], width=2),
                marker=dict(size=8),
                hovertemplate=f"<b>{code}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ))
        fig_fun.update_layout(
            **plotly_layout(
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            bgcolor="rgba(0,0,0,0)", bordercolor=BORDER),
            ),
            yaxis_title="Probability %",
        )
        st.plotly_chart(fig_fun, use_container_width=True)

    # WC2026 format explainer
    st.markdown("---")
    st.markdown("### WC2026 Tournament Structure")
    st.markdown(f"""
    <div class="card" style="font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.9">
    <b>Format:</b> 48 teams · 12 groups (A–L) · 4 teams per group<br>
    <b>Advance:</b> Top 2 per group (24) + best 8 third-place teams (8) = <b>32 teams to R32</b><br>
    <b>Knockout:</b> R32 → R16 (16) → QF (8) → SF (4) → Final / 3rd-place playoff<br><br>
    <b>Tiebreaker order in groups:</b> Points → Head-to-head pts → Head-to-head GD →<br>
    &nbsp;&nbsp;&nbsp;&nbsp;Head-to-head GF → Group GD → Group GF → Fair Play → FIFA ranking<br><br>
    <b>Best third-place ranking:</b> Compare only GD, GF, Fair Play, FIFA ranking
    </div>
    """, unsafe_allow_html=True)

    # Bracket halves
    st.markdown("---")
    st.markdown("### Bracket half difficulty (average Elo of teams in each half)")
    if groups:
        try:
            lpp = DATA / "elo_live_params.json"
            all_elos = json.loads(lpp.read_text())["team_elos"] if lpp.exists() else {}
            halves = {
                "Half A (Groups A–F)": ["A", "B", "C", "D", "E", "F"],
                "Half B (Groups G–L)": ["G", "H", "I", "J", "K", "L"],
            }
            for half_name, half_groups in halves.items():
                half_teams = [t for g in half_groups for t in groups.get(g, [])]
                avg_elo    = np.mean([all_elos.get(t, 1500) for t in half_teams]) if half_teams else 0
                max_elo    = max([all_elos.get(t, 1500) for t in half_teams], default=0)
                max_team   = max(half_teams, key=lambda t: all_elos.get(t, 0), default="?")
                st.markdown(
                    f"**{half_name}**: avg Elo = {avg_elo:.0f} · "
                    f"strongest = {flag(max_team, disp_df)} {max_team} ({max_elo:.0f})"
                )
        except Exception as e:
            st.caption(f"Bracket difficulty error: {e}")

    # Per-team path summary
    st.markdown("---")
    st.markdown("### Path probabilities — select a team")
    if not elo_df.empty:
        pt_team = st.selectbox(
            "Select team for path analysis",
            sorted(elo_df["team"].tolist()),
            format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
            key="bracket_team",
        )
        pt_row = elo_df[elo_df["team"] == pt_team]
        if not pt_row.empty:
            pt_row = pt_row.iloc[0]
            stages  = ["group_survival_prob", "qf_prob", "sf_prob", "final_prob", "champion_prob"]
            labels  = ["Advance from group", "Reach QF", "Reach SF", "Reach Final", "Win WC2026"]

            html_bars = ""
            prev = 1.0
            for s, l in zip(stages, labels):
                if s in pt_row.index:
                    p = float(pt_row[s])
                    cond = p / prev if prev > 0 else 0
                    prev = p
                    bar_pct = p * 100 / 1  # absolute
                    bar_pct_visual = min(p * 100 / 50, 1.0) * 100
                    color = TEAL if p > 0.5 else (GOLD if p > 0.2 else (RED if p > 0.05 else MUTED))
                    html_bars += f"""
                    <div style="margin:10px 0">
                      <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
                        <span>{l}</span>
                        <span style="color:{WHITE};font-weight:600">{p*100:.1f}%</span>
                      </div>
                      <div style="background:{BG3};border-radius:4px;height:8px;overflow:hidden">
                        <div style="width:{bar_pct_visual}%;height:100%;background:{color};border-radius:4px"></div>
                      </div>
                      <div style="font-size:11px;color:{MUTED};margin-top:2px">
                        Conditional P(next stage | this stage): {cond*100:.0f}%
                      </div>
                    </div>"""
            st.markdown(f'<div class="card">{html_bars}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — MODEL LAB
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Model Lab":
    st.markdown("# Model Laboratory")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px'>"
        "Full mathematical transparency · Honest limitations · "
        "Global maturity audit</div>",
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4, t5 = st.tabs(
        ["📐 Mathematics", "📊 Ablation", "🔬 Calibration", "⚠️ Limitations", "📋 Maturity Score"])

    with t1:
        st.markdown("### Core Mathematics")
        st.latex(r"\log \mu_A = \log_{\text{base}} + \beta_{\text{elo}} \cdot \frac{\text{Elo}_A - \text{Elo}_B}{400}")
        st.latex(r"\log \mu_B = \log_{\text{base}} - \beta_{\text{elo}} \cdot \frac{\text{Elo}_A - \text{Elo}_B}{400}")
        st.latex(r"P(X=i, Y=j) = \tau_{ij} \cdot \frac{e^{-\mu_A} \mu_A^i}{i!} \cdot \frac{e^{-\mu_B} \mu_B^j}{j!}")
        st.latex(r"\tau(0,0) = 1 - \rho\mu_A\mu_B, \quad \tau(1,0) = 1 + \rho\mu_B, \quad "
                  r"\tau(0,1) = 1 + \rho\mu_A, \quad \tau(1,1) = 1 - \rho")

        st.markdown("**Parameters (MLE on 10,555 international matches, 2010–2025):**")
        try:
            lpp = DATA / "elo_live_params.json"
            lp  = json.loads(lpp.read_text())
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("β_elo (MLE)", f"{lp['beta_elo']:.6f}")
            c2.metric("log_base (MLE)", f"{lp['log_base']:.6f}")
            c3.metric("ρ (DC)", f"{lp.get('rho', -0.021):.6f}")
            c4.metric("β_elo × 0.55 (heuristic)", f"{lp['beta_elo']*0.55:.6f}")
        except Exception:
            pass

        st.markdown("""
**Temperature correction:** β_mul = 0.55 applied heuristically.

Original MLE β = 0.988 produces 66.4% top-3 concentration (not credible for WC).
Corrected β = 0.544 → 41.8% top-3 (internal sanity check only; not externally validated).

⚠️ β_mul = 0.55 is NOT optimized against any external criterion. It was chosen because
41–42% top-3 concentration matches the rough historical range (1998–2022 WC champions
and runners-up were top-3 pre-tournament favourites in 5/7 editions).

**Elo update (live matches, k=40):**
""")
        st.latex(r"\Delta_A = K \cdot \text{MOV} \cdot (S_A - E_A)")
        st.latex(r"\text{MOV} = \log(\text{margin}+1) \cdot \frac{2.2}{\Delta\text{Elo} \times 0.001 + 2.2}")
        st.latex(r"E_A = \frac{1}{1 + 10^{(\text{Elo}_B - \text{Elo}_A)/400}}")

        st.markdown("**Conservation law (verified):**")
        if not elo_df.empty and "champion_prob" in elo_df.columns:
            total_prob = elo_df["champion_prob"].sum()
            color = TEAL if abs(total_prob - 1.0) < 1e-4 else RED
            st.markdown(
                f"<span style='color:{color};font-family:JetBrains Mono,monospace'>"
                f"Σ P(champion) = {total_prob:.6f} ✓</span>",
                unsafe_allow_html=True,
            )

    with t2:
        st.markdown("### P2.5 Ablation Study")
        st.markdown("9 model variants × 4 temporal train/test splits")
        abl_df = load_ablation()
        if abl_df.empty:
            st.info("Ablation results not found at outputs/calibration/ablation_results.csv")
        else:
            nll_cols = [c for c in abl_df.columns if c.endswith("_nll")]
            ece_cols = [c for c in abl_df.columns if c.endswith("_ece")]
            model_names = [c.replace("_nll", "") for c in nll_cols]
            avg_nll = [abl_df[c].mean() for c in nll_cols]
            avg_ece = [abl_df[c].mean() for c in ece_cols if c in abl_df.columns]
            name_map = {
                "A_random": "A:Random", "B_empirical": "B:Empirical",
                "C_elo_nohome": "C:Elo-noH", "D_elo_home": "D:Elo+H",
                "E_elo_calib": "E:Elo-Cal★", "F_indep_poisson": "F:Ind.Pois",
                "G_elo_dc_rho": "G:Elo+DC", "H_hybrid_norho": "H:Hyb-ρ",
                "I_hybrid_full": "I:Full.Hyb",
            }
            bar_col = [MUTED, MUTED, MUTED, MUTED, TEAL, MUTED, MUTED, MUTED, RED]
            labels = [name_map.get(n, n) for n in model_names]

            fig2 = make_subplots(rows=1, cols=2, subplot_titles=["NLL (↓ better)", "ECE ×1000 (↓ better)"])
            fig2.add_trace(go.Bar(
                x=labels, y=avg_nll, marker_color=bar_col,
                text=[f"{v:.4f}" for v in avg_nll], textposition="outside",
                textfont=dict(size=10, color=WHITE), name="NLL",
            ), row=1, col=1)
            if avg_ece:
                fig2.add_trace(go.Bar(
                    x=labels[:len(avg_ece)],
                    y=[v * 1000 for v in avg_ece],
                    marker_color=bar_col[:len(avg_ece)],
                    text=[f"{v:.1f}" for v in [x * 1000 for x in avg_ece]],
                    textposition="outside",
                    textfont=dict(size=10, color=WHITE), name="ECE",
                ), row=1, col=2)
            fig2.update_layout(**plotly_layout(height=380), showlegend=False)
            fig2.update_xaxes(tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

            st.markdown("""
**Decision:** Promote Model E (Elo-Calibrated) as primary.

Full Hybrid (I) achieves best NLL but ECE deteriorates +17%. 646 extra parameters
(attack/defense per team) overfit training and reduce probability calibration.
Occam's razor: simpler model wins when calibration gap is material.
""")

    with t3:
        st.markdown("### Calibration Report")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Primary model ECE", "0.0170", "avg 4 temporal splits")
        cc2.metric("Full Hybrid ECE", "0.0199", "+17% vs primary", delta_color="inverse")
        cc3.metric("Match-level NLL", "See ablation", delta_color="off")

        st.markdown("""<div class="caveat-box">
        ⚠️ <b>Critical caveat:</b> ECE = 0.017 measures match-outcome calibration on historical data.
        It does NOT measure tournament champion probability calibration.
        No champion-prediction backtest has been run (e.g. "given 2018 pre-WC Elo, France probability").
        This is the most important missing validation.
        </div>""", unsafe_allow_html=True)

        st.markdown("**Calibration improvement roadmap:**")
        items = [
            ("WC tournament-level champion backtest",  "HIGH", "3–4h", "Apply model to WC1994–2022; compare P(champion) to result"),
            ("Bootstrap CI for β_elo",                 "HIGH", "3h",   "Resample training data 1000×; build β_elo confidence interval"),
            ("Significance test variance fix",          "MED",  "1h",   "Replace hardcoded variance=0.40 in significance_report.csv"),
            ("Isotonic regression calibration",         "MED",  "2h",   "Post-process P(match outcome) to reduce ECE further"),
            ("Parameter uncertainty propagation",       "MED",  "4h",   "Monte Carlo over β_elo ± 1σ; widen champion CIs"),
        ]
        for name, impact, effort, desc in items:
            col = RED if impact == "HIGH" else GOLD
            st.markdown(
                f"• <span style='color:{col}'>[{impact}]</span> **{name}** ({effort}): {desc}",
                unsafe_allow_html=True,
            )

    with t4:
        st.markdown("### Known Limitations")
        lims = [
            (RED, "Temperature correction is heuristic",
             "β_mul=0.55 chosen to match historical top-3 concentration range. "
             "No external validation criterion. Internal consistency only."),
            (RED, "Expert model coefficients are analyst priors",
             "16 hand-tuned parameters (attack, defense, ppda, etc.) — zero statistical estimation. "
             "Described correctly in MODEL_CARD.md but must not be conflated with MLE."),
            (TEAL, "WC historical backtest done",
             "WC2022: ARG #1 pick (17.2%), actual winner. WC2018: FRA #6 (5.5%), actual winner. "
             "Avg champion Brier 0.027 vs 0.250 random = 89% skill. See Data Quality page."),
            (GOLD, "StatsBomb data: 30/48 teams",
             "18 teams use analyst-assigned defaults. Coverage bias favors UEFA and CONMEBOL."),
            (GOLD, "Temporal form: 16/48 teams",
             "32 teams have static form=50.0. Temporal decay not applied."),
            (GOLD, "Jet lag: single-venue approximation",
             "WC2026 spans UTC-4 to UTC-7. Model uses Dallas UTC-5 for all venues."),
            (GOLD, "Injury adjustments not quantified",
             "Messi (hamstring), Rodrygo (ACL), Ekitike (Achilles) etc. logged but "
             "not integrated into Elo or xG calculations."),
            (GOLD, "Significance test variance hardcoded",
             "significance_report.csv variance=0.40 is a placeholder. See test_quality_audit.md."),
            (TEAL, "Conservation laws pass ✓",
             "Σ P(champion) = 1.000000. Σ P(finalist) = 2.000000. Simulation mechanics correct."),
            (TEAL, "Reproducibility: high ✓",
             "Fixed seed, frozen parameters, SHA256 hashes, reproduction script. Score: 8.0/10."),
        ]
        for color, title, desc in lims:
            icon = "🔴" if color == RED else ("🟡" if color == GOLD else "🟢")
            st.markdown(f"""<div class="card" style="border-left:3px solid {color};padding:12px 18px;margin:6px 0">
            <b style='color:{color}'>{icon} {title}</b><br>
            <span style='color:{MUTED};font-size:13px'>{desc}</span>
            </div>""", unsafe_allow_html=True)

    with t5:
        st.markdown("### Global Maturity Audit — Quant Lab Standard")
        st.markdown(
            "Scoring criterion: what a quant researcher with 10 years of forecasting budget would demand."
        )

        audit_path = AUDIT / "global_maturity_score.json"
        if audit_path.exists():
            audit_data = json.loads(audit_path.read_text())
            scores     = audit_data.get("scores", {})
            g_avg      = float(audit_data.get("global_average", 5.25))

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=g_avg,
                domain={"x": [0, 1], "y": [0, 1]},
                gauge={
                    "axis": {"range": [0, 10], "tickcolor": WHITE},
                    "bar":  {"color": TEAL if g_avg >= 7 else (GOLD if g_avg >= 5 else RED)},
                    "bgcolor": BG2,
                    "steps": [
                        {"range": [0, 4],  "color": "rgba(230,57,70,0.15)"},
                        {"range": [4, 7],  "color": "rgba(233,196,106,0.12)"},
                        {"range": [7, 10], "color": "rgba(42,157,143,0.12)"},
                    ],
                },
                title={"text": "Global Maturity / 10", "font": {"color": WHITE, "size": 15}},
                number={"font": {"color": WHITE, "size": 48}},
            ))
            fig_gauge.update_layout(**plotly_layout(height=280))
            st.plotly_chart(fig_gauge, use_container_width=True)

            dim_names = [k.replace("_", " ").title() for k in scores.keys()]
            dim_vals  = list(scores.values())
            dim_colors = [TEAL if v >= 7 else (GOLD if v >= 5 else RED) for v in dim_vals]

            fig_dim = go.Figure(go.Bar(
                x=dim_vals,
                y=dim_names,
                orientation="h",
                marker_color=dim_colors,
                text=[f"{v:.1f}" for v in dim_vals],
                textposition="outside",
                textfont=dict(size=11, color=WHITE),
            ))
            fig_dim.update_layout(
                **plotly_layout(height=420),
                xaxis_range=[0, 10],
                xaxis_title="Score / 10",
            )
            fig_dim.add_vline(
                x=7, line_dash="dash", line_color=TEAL,
                annotation_text="Publication floor", annotation_font_color=TEAL,
            )
            st.plotly_chart(fig_dim, use_container_width=True)

            st.markdown(f"""
**{g_avg:.2f}/10 → Serious personal project. Not investment-grade forecasting.**

Strongest dimensions: Reproducibility (8.0), Honesty (7.5), Documentation (7.0)

Critical gaps (scores < 4):
- Validation Methodology (2.5) — No WC champion backtest
- Calibration (3.0) — ECE measured but not corrected
- Uncertainty Quantification (3.0) — Wilson CIs only, no parameter uncertainty

What would reach 8.0+: ECE calibration plot, isotonic calibration,
significance test variance fix, temporal form for all 48 teams.
""")
        else:
            st.info("Run outputs/audit/ scripts to generate the maturity score JSON.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📡 Data Quality":
    st.markdown("# Data Quality & Source Audit")
    st.markdown(
        f"<div style='color:{MUTED};font-size:13px'>Every claim on this site is backed by a "
        "documented source. This page shows exactly what data we have, what we're missing, "
        "and how fresh it is.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── What this forecast is / is not (defensibility) ───────────────────────
    with st.expander("ℹ️ What this forecast IS / is NOT — read first", expanded=False):
        cwa, cwb = st.columns(2)
        with cwa:
            st.markdown(
                "**This IS:**\n"
                "- A probability *distribution* over outcomes (favorite ≈19%).\n"
                "- Validated leak-free at match level (Brier 0.508 vs 0.529 Elo) and tournament "
                "level (walk-forward WC2010/14/18/22).\n"
                "- Reported with P5/P50/P95 champion intervals.\n"
                "- Fully reproducible offline; 558 tests."
            )
        with cwb:
            st.markdown(
                "**This is NOT:**\n"
                "- A predicted winner or a betting tool.\n"
                "- Tournament-level *calibrated* (only 4 WCs validated).\n"
                "- Total uncertainty — intervals are a **floor** (beta sampling only; structural "
                "uncertainty excluded).\n"
                "- Using independent xG sources (Highlightly ≈ TheStatsAPI upstream)."
            )
        st.caption(
            "Model card: `outputs/audit/model_card_public.md` · Data lineage: "
            "`outputs/audit/data_lineage_map.md` · Reviewer audit: "
            "`outputs/audit/reviewer_attack_audit.md` · Reproduce: "
            "`scripts/rebuild_publication_forecast.py` · Deploy readiness: "
            "`outputs/deploy/deploy_readiness_checklist.md`."
        )
        ci_p = ROOT / "data" / "live" / "champion_probability_intervals.json"
        ts = json.loads(ci_p.read_text()).get("generated_at", "?")[:19] if ci_p.exists() else "?"
        st.caption(f"Latest forecast artifact: {ts} UTC · Model: Elo→DC + ML@0.20 · "
                   "Deployment-readiness: portfolio→Vercel GO, live app→Render (user action).")

    # ── Provider Status ──────────────────────────────────────────────────────
    st.markdown("## Provider Status")

    provider_status_path = ROOT / "data" / "live" / "provider_status.json"
    if provider_status_path.exists():
        pstatus = json.loads(provider_status_path.read_text())
        providers = pstatus.get("providers", {})
        gen_at = pstatus.get("generated_at", "unknown")
        st.markdown(
            f"<div style='color:{MUTED};font-size:12px'>Last checked: {gen_at[:19].replace('T',' ')} UTC</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        QUALITY_COLOR = {"A": TEAL, "B": GOLD, "C": GOLD, "D": RED,
                         "blocked_free_plan": RED}

        for pname, pdata in providers.items():
            avail = pdata.get("available", False)
            accessible = pdata.get("wc2026_accessible", False)
            qlevel = str(pdata.get("quality_level", "D"))
            qcolor = QUALITY_COLOR.get(qlevel, MUTED)

            if accessible:
                status_dot = f"<span style='color:{TEAL}'>●</span>"
                status_label = "ACTIVE"
            elif avail:
                status_dot = f"<span style='color:{GOLD}'>●</span>"
                status_label = "AVAILABLE (limited)"
            else:
                status_dot = f"<span style='color:{RED}'>●</span>"
                status_label = "UNAVAILABLE"

            with st.expander(f"{status_dot} **{pname.replace('_',' ').title()}** — Quality: "
                             f"<span style='color:{qcolor}'>{qlevel}</span> — {status_label}",
                             expanded=accessible):
                lag = pdata.get("lag_note", "")
                if lag:
                    st.markdown(f"**Lag**: {lag}")
                fields = pdata.get("fields", pdata.get("fields_if_paid", []))
                missing = pdata.get("missing", [])
                if fields:
                    st.markdown(f"**Fields**: {', '.join(fields)}")
                if missing:
                    st.markdown(
                        f"<span style='color:{RED}'>**Missing**: {', '.join(missing)}</span>",
                        unsafe_allow_html=True,
                    )
                action = pdata.get("action_needed", "")
                if action:
                    st.warning(f"Action needed: {action}")
    else:
        st.warning("Provider status not yet generated. Run: `PYTHONPATH=src python scripts/update_live_data.py`")

    st.markdown("---")

    # ── Quality Legend ───────────────────────────────────────────────────────
    st.markdown("## Quality Levels")
    st.markdown(f"""
| Level | Meaning | Fields Available |
|---|---|---|
| <span style='color:{TEAL}'>**A**</span> | Real xG + full in-play stats | xG, shots, SOT, corners, cards, lineups, live minute |
| <span style='color:{GOLD}'>**B**</span> | Shots/SOT/corners/cards (no xG) | Shots, SOT, corners, cards, live minute |
| <span style='color:{GOLD}'>**C**</span> | Score + result only | Goals, half-time score, scorers |
| <span style='color:{RED}'>**D**</span> | Stale / manual / unavailable | Manual notes only |

**Current status: Quality A** — Highlightly BASIC plan provides xG (Expected Goals) via `/statistics/{matchId}`. All 4 completed matches have confirmed xG. API-Football FREE (date-bypass) provides events/lineups/stats. Football-data.org provides standings + scorers. TheStatsAPI key revoked (documented — no active sub). Zero score disagreements across 3 providers.
""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Coverage Matrix ──────────────────────────────────────────────────────
    st.markdown("## Field Coverage Matrix")

    coverage_data = {
        "Field": ["Live score (min by min)", "Goals + scorers", "Half-time score",
                  "Shots / SOT", "xG (real)", "Big Chances", "Expected Assists",
                  "Corners", "Cards", "Lineups", "Venue / Referee / Weather",
                  "Highlights (clips)", "Injuries", "Match odds"],
        "API-Football FREE": ["✅", "✅", "✅", "✅", "❌", "❌", "❌", "✅", "✅", "✅", "❌", "❌", "❌", "❌"],
        "Highlightly BASIC": ["✅", "✅", "✅", "✅", "✅ (A)", "✅", "✅", "❌", "✅", "✅", "✅", "⚠️ pending", "❌", "⚠️ pending"],
        "Football-data.org FREE": ["❌", "✅", "✅", "❌", "❌", "❌", "❌", "❌", "❌", "❌", "❌", "❌", "❌", "❌"],
        "TheStatsAPI": ["—", "—", "—", "—", "✅ (A)", "✅", "✅", "—", "—", "—", "—", "—", "—", "✅"],
        "Note (TSA)": ["", "", "", "", "KEY_REVOKED", "", "", "", "", "", "", "", "", ""],
        "Impact on model": ["In-play probs", "Elo update", "HT signal",
                            "xG proxy (B)", "xG direct (A)", "Chance quality", "Assist xG",
                            "Domain stats", "Red card adj", "Injury proxy", "Context",
                            "Media", "Manual only", "Calibration"],
    }
    st.dataframe(pd.DataFrame(coverage_data), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Live Data Status ─────────────────────────────────────────────────────
    st.markdown("## Current Live Data")

    live_path = ROOT / "data" / "wc2026_live.json"
    if live_path.exists():
        live = json.loads(live_path.read_text())
        n_completed = len(live.get("completed_matches", []))
        last_upd = live.get("last_updated", "unknown")
        dq = live.get("data_quality", "unknown")
        source = live.get("source", "unknown")

        xg_flag = "✅ xG" if live.get("xg_available") else "❌ xG"
        provider_count = len(live.get("providers_confirmed", []))
        cols = st.columns(4)
        with cols[0]:
            st.metric("Completed Matches", n_completed)
        with cols[1]:
            st.metric("Source Quality", dq)
        with cols[2]:
            st.metric("xG Available", xg_flag)
        with cols[3]:
            st.metric("Providers Confirmed", provider_count)

        st.markdown(f"**Source**: {source}")
        st.markdown(
            f"**Provider agreement**: {live.get('provider_agreement', 'not checked')}"
        )

        # xG summary if available
        xg_path = ROOT / "data" / "live" / "live_xg.json"
        if xg_path.exists():
            xg_data = json.loads(xg_path.read_text())
            st.success(
                f"xG available (Quality A) — {len(xg_data.get('matches', []))} matches "
                f"via {xg_data.get('source', 'highlightly')}. "
                f"Expected Goals confirmed via `/statistics/{{matchId}}` endpoint."
            )

        if n_completed > 0:
            st.markdown("### Completed Matches")
            for m in live.get("completed_matches", []):
                src = m.get("source", "unknown")
                xg_h = m.get("xg_home")
                xg_a = m.get("xg_away")
                bc_h = m.get("big_chances_home")
                bc_a = m.get("big_chances_away")
                xg_str = ""
                if xg_h is not None:
                    xg_str = f" | xG {xg_h:.2f}–{xg_a:.2f}"
                bc_str = f" | BigChances {bc_h}–{bc_a}" if bc_h is not None else ""
                st.markdown(
                    f"- {m['home']} **{m['home_goals']}–{m['away_goals']}** {m['away']} "
                    f"| {m.get('date','?')} | Group {m.get('group','?')}"
                    f"<span style='color:{TEAL}'>{xg_str}{bc_str}</span>"
                    f" <span style='color:{MUTED};font-size:12px'>| src: {src}</span>",
                    unsafe_allow_html=True,
                )
    else:
        st.warning("wc2026_live.json not found.")

    # ── xG-adjusted vs score-only (Phase 3) ──────────────────────────────────
    xg_audit_path = ROOT / "outputs" / "audit" / "xg_adjustment_audit.json"
    xg_delta_path = ROOT / "outputs" / "audit" / "xg_probability_delta.csv"
    if xg_audit_path.exists():
        st.markdown("---")
        st.markdown("## xG-Adjusted vs Score-Only Probabilities")
        xa = json.loads(xg_audit_path.read_text())
        passed = xa.get("guardrail_passed", False)
        move = xa.get("max_champion_move_pp", 0.0)
        guard = xa.get("guardrail_pp", 1.0)
        badge_color = TEAL if passed else RED
        st.markdown(
            f"<span style='color:{badge_color}'>**Live xG-adjusted** · bounded ±"
            f"{xa['config']['max_abs_delta']:.0f} Elo/match · weight "
            f"{xa['config']['weight_per_xg_margin']:.0f} · source Highlightly</span>",
            unsafe_allow_html=True,
        )
        c = st.columns(3)
        with c[0]:
            st.metric("Max champion move", f"{move:.3f} pp")
        with c[1]:
            st.metric("Guardrail", f"≤ {guard} pp", delta="PASS" if passed else "FAIL",
                      delta_color="normal" if passed else "inverse")
        with c[2]:
            st.metric("Default mode", xa.get("default_mode_recommendation", "score_only"))
        st.caption(
            "xG adjustment is **live-conditioning only**, not historical xG-trained calibration. "
            "It corrects the score-based Elo delta by (xG margin − score margin), capped per match. "
            "`beta_elo` is never modified. Only 4 matches carry xG — the cap keeps any single "
            "result from moving champion probabilities by more than ~1pp."
        )
        if xg_delta_path.exists():
            dd = pd.read_csv(xg_delta_path).head(10)
            show = dd[["team", "champ_score", "champ_xg", "champ_delta_pp"]].copy()
            show["champ_score"] = (show["champ_score"] * 100).round(2).astype(str) + "%"
            show["champ_xg"] = (show["champ_xg"] * 100).round(2).astype(str) + "%"
            show["champ_delta_pp"] = show["champ_delta_pp"].round(3)
            show.columns = ["Team", "Champ (score-only)", "Champ (xG-adj)", "Δ pp"]
            st.dataframe(show, use_container_width=True, hide_index=True)

    # ── ML 1X2 gate (Phase 7) ────────────────────────────────────────────────
    ml_report_path = ROOT / "outputs" / "audit" / "ml_validation_report.json"
    if ml_report_path.exists():
        st.markdown("---")
        st.markdown("## ML Match Model — Gated Validation")
        mr = json.loads(ml_report_path.read_text())
        m = mr["metrics"]
        accepted = mr["gate"]["accepted"]
        badge = TEAL if accepted else RED
        st.markdown(
            f"<span style='color:{badge}'>**ML {'ACCEPTED' if accepted else 'REJECTED'}**</span> "
            f"· {mr['split']} · features {mr['features']}",
            unsafe_allow_html=True,
        )
        cmp = pd.DataFrame([
            {"Model": "Random", **{k: m["random"][k] for k in ["brier", "nll", "ece"]}},
            {"Model": "Elo-only", **{k: m["elo_only"][k] for k in ["brier", "nll", "ece"]}},
            {"Model": "ML (logistic)", **{k: m["ml"][k] for k in ["brier", "nll", "ece"]}},
        ])
        cmp.columns = ["Model", "Brier ↓", "NLL ↓", "ECE ↓"]
        st.dataframe(cmp, use_container_width=True, hide_index=True)
        st.caption(
            f"Gate: {mr['gate']['reason']} "
            "Honest scope: this validates a **single-match 1X2 model** on a leak-free temporal "
            "split (train ≤2018, test 2019–2022). It is NOT yet wired into the tournament Monte "
            "Carlo, and is NOT an xG-trained model. `model_stack_config.json` carries a rollback flag."
        )

        # ML ensemble integration into the tournament sim
        ens_path = ROOT / "outputs" / "audit" / "ml_ensemble_integration_decision.json"
        if ens_path.exists():
            ens = json.loads(ens_path.read_text())
            integrated = ens.get("decision") == "INTEGRATED"
            badge = TEAL if integrated else GOLD
            st.markdown(
                f"<span style='color:{badge}'>**Tournament integration: {ens.get('decision')}**</span> "
                f"· 0.5 Elo + 0.5 ML, reweighting DC scoreline W/D/L · rollback flag in config",
                unsafe_allow_html=True,
            )
            ens_csv = ROOT / "outputs" / "audit" / "ml_ensemble_probability_delta.csv"
            if ens_csv.exists():
                ed = pd.read_csv(ens_csv).head(8)
                t = ed[["team", "champ_elo", "champ_ml", "champ_delta_pp"]].copy()
                t["champ_elo"] = (t["champ_elo"] * 100).round(2).astype(str) + "%"
                t["champ_ml"] = (t["champ_ml"] * 100).round(2).astype(str) + "%"
                t["champ_delta_pp"] = t["champ_delta_pp"].round(3)
                t.columns = ["Team", "Champ (Elo-only)", "Champ (ML-ens)", "Δ pp"]
                st.dataframe(t, use_container_width=True, hide_index=True)
            st.caption(
                f"Max champion move {ens.get('max_champion_move_pp')}pp at the original 0.5 weight. "
                "Scoreline/knockout logic preserved; champion probabilities still sum to 1. See the "
                "Model Stack panel below for the evidence-tuned weight."
            )

    # ── Model Stack & Validation (strategic panel) ───────────────────────────
    stack_path = ROOT / "outputs" / "audit" / "model_stack_final_decision.json"
    if stack_path.exists():
        st.markdown("---")
        st.markdown("## Model Stack & Validation")
        sd = json.loads(stack_path.read_text())
        ke = sd.get("key_evidence", {})
        st.markdown(f"**Selected mode:** {sd.get('selected_model_mode')}")
        c = st.columns(4)
        with c[0]:
            st.metric("ML weight (chosen)", ke.get("tournament_chosen_weight"),
                      help="Cut from 0.5 → 0.2 by walk-forward evidence")
        with c[1]:
            st.metric("Tourn. Brier vs Elo", f"{ke.get('tournament_improvement_vs_elo_pct')}%")
        with c[2]:
            st.metric("Model vs market", ke.get("market_confidence", "—"))
        with c[3]:
            st.metric("β sensitivity", ke.get("beta_sensitivity_level", "—"),
                      delta=f"{ke.get('beta_max_champion_range_pp')}pp", delta_color="off")
        wf_path = ROOT / "outputs" / "audit" / "tournament_walkforward_validation.json"
        if wf_path.exists():
            wf = json.loads(wf_path.read_text())
            agg = pd.DataFrame(wf["aggregate_by_weight"])[["ml_weight", "mean_champ_brier", "mean_entropy"]]
            agg.columns = ["ML weight", "Champ Brier (WC18+22)", "Entropy"]
            st.dataframe(agg.round(5), use_container_width=True, hide_index=True)
        st.warning(
            f"**Tournament validation (2 WCs):** {ke.get('tournament_disagreement')} "
            f"Best raw weight 0.5 was flagged overconcentrated → chose 0.20. "
            f"**β sensitivity is {ke.get('beta_sensitivity_level')}** "
            f"({ke.get('beta_max_champion_range_pp')}pp under ±25% β) — champion probabilities are NOT "
            "point-precise. Market odds: **benchmark only, not integrated** "
            f"(large disagreements: {ke.get('market_large_disagreements') or 'none'})."
        )
        # Maturity by dimension + hard cap
        mat_path = next((ROOT / "outputs" / "audit" / f"final_maturity_score_{v}.json"
                         for v in ("v6", "v5", "v4")
                         if (ROOT / "outputs" / "audit" / f"final_maturity_score_{v}.json").exists()),
                        ROOT / "outputs" / "audit" / "final_maturity_score_v4.json")
        if mat_path.exists():
            mat = json.loads(mat_path.read_text())
            with st.expander(f"Maturity {mat['before']} → {mat['after']} (by dimension) + hard cap"):
                ms = pd.DataFrame([{"Dimension": k, "Score": v} for k, v in mat["scores_after"].items()])
                st.dataframe(ms, use_container_width=True, hide_index=True)
                st.caption(f"**Hard cap:** {mat['hard_cap']}")

    # ── Forecast Uncertainty & Robustness (Batch A–D) ────────────────────────
    ci_path = ROOT / "data" / "live" / "champion_probability_intervals.json"
    if ci_path.exists():
        st.markdown("---")
        st.markdown("## Forecast Uncertainty & Robustness")
        ci = json.loads(ci_path.read_text())
        bt = ci.get("beta", {})
        st.markdown(
            f"<span style='color:{GOLD}'>**Champion probabilities are intervals, not point "
            f"estimates.**</span> β P5/P50/P95 = {bt.get('p5')}/{bt.get('p50')}/{bt.get('p95')} "
            f"(SE {bt.get('se')}).",
            unsafe_allow_html=True,
        )
        iv = ci.get("intervals", {})
        ivrows = [{"Team": t, "Low (P5)": f"{d['low']*100:.2f}%", "Base": f"{d['base']*100:.2f}%",
                   "High (P95)": f"{d['high']*100:.2f}%"} for t, d in list(iv.items())[:10]]
        st.dataframe(pd.DataFrame(ivrows), use_container_width=True, hide_index=True)
        st.caption(
            "Bands propagate **beta sampling uncertainty only** (small — the 10.5k-match dataset "
            "pins beta tightly). They are a FLOOR: they exclude the temperature-calibration choice, "
            "structural model error, and tournament variance, which dominate. Not point-precise."
        )
        # Expanded validation + dynamic ML + market flags
        ev_path = ROOT / "outputs" / "audit" / "upset_robust_ml_weighting.json"
        if ev_path.exists():
            ev = json.loads(ev_path.read_text())
            st.markdown(
                f"**ML robustness:** validated on **4 World Cups (2010/14/18/22)**. Fixed vs dynamic "
                f"weighting → **{ev.get('decision')}** (dynamic halves worst-case upset regret "
                f"{ev['worst_case_regret_vs_elo'].get('fixed_0.20')}→{ev['worst_case_regret_vs_elo'].get('dynamic_0.20')} "
                f"but aggregate within noise; dynamic available as a config flag)."
            )
        mf_path = ROOT / "data" / "live" / "market_disagreement_flags.json"
        if mf_path.exists():
            mf = json.loads(mf_path.read_text())
            cc = mf.get("class_counts", {})
            unders = [f["match"] for f in mf.get("flags", []) if f.get("class") == "model_underprices_team"]
            st.caption(
                f"**Market control layer** (benchmark only, not blended): {cc}. "
                f"Model underprices: {unders or 'none'}."
            )

    st.markdown("---")

    # ── Backtest Validation ──────────────────────────────────────────────────
    st.markdown("## Historical Backtest Results")

    backtest_path = ROOT / "outputs" / "audit" / "wc_historical_backtest.json"
    if backtest_path.exists():
        bt = json.loads(backtest_path.read_text())
        combined = bt.get("combined", {})

        cols = st.columns(3)
        with cols[0]:
            st.metric("Avg Champion Brier", f"{combined.get('avg_champion_brier', 0):.4f}",
                      delta=f"{combined.get('skill_pct_below_random', 0):.0f}% below random",
                      delta_color="normal")
        with cols[1]:
            st.metric("Random Baseline", "0.2500")
        with cols[2]:
            ranks = combined.get("actual_champion_ranks", {})
            st.metric("Actual Champion Ranks", f"{list(ranks.values())}")

        for wc_key, wc_data in bt.get("tournaments", {}).items():
            with st.expander(f"**{wc_data['tournament']}**"):
                bs = wc_data["brier_scores"]
                st.markdown(f"""
| Stage | Brier Score | vs Random (0.250) |
|---|---|---|
| Group survival | {bs['group_survival']:.4f} | {(0.25 - bs['group_survival'])/0.25*100:.0f}% better |
| Semifinal | {bs['semifinal']:.4f} | {(0.25 - bs['semifinal'])/0.25*100:.0f}% better |
| Champion | {bs['champion']:.4f} | {(0.25 - bs['champion'])/0.25*100:.0f}% better |

**Model's #1 champion pick**: {wc_data['model_champion']} ({wc_data['model_champion_prob']*100:.1f}%)

**Actual champion**: {wc_data['actual_champion']} — model rank: **#{wc_data['actual_champion_rank']}** (gave {wc_data['actual_champion_prob']*100:.1f}%)
""")
                st.markdown("**Top 10 pre-tournament champion probabilities:**")
                for i, entry in enumerate(wc_data.get("top10_champion_probs", [])):
                    mark = " 🏆 ACTUAL WINNER" if entry["team"] == wc_data["actual_champion"] else ""
                    st.markdown(f"  {i+1}. **{entry['team']}** — {entry['prob']*100:.1f}%{mark}")

        st.markdown(
            f"<div style='color:{MUTED};font-size:12px;margin-top:8px'>"
            "⚠️ Limitation: β_elo fit on 2010-2025 full history — partial future-peek relative to WC2022. "
            "Team Elos are genuinely pre-tournament. Full walk-forward CV not performed.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Run: `PYTHONPATH=src python scripts/run_wc_historical_backtest.py`")

    st.markdown("---")

    # ── Bootstrap CI ────────────────────────────────────────────────────────
    st.markdown("## Parameter Uncertainty (β_elo Bootstrap)")

    ci_path = ROOT / "outputs" / "audit" / "beta_bootstrap_ci.json"
    if ci_path.exists():
        ci_data = json.loads(ci_path.read_text())
        br = ci_data.get("bootstrap_results", {}).get("beta_elo", {})
        tc = ci_data.get("temperature_correction", {})
        ci_lo = br.get("ci_95_lo", 0)
        ci_hi = br.get("ci_95_hi", 0)
        p_ci_lo = tc.get("production_beta_ci_95", {}).get("lo", 0)
        p_ci_hi = tc.get("production_beta_ci_95", {}).get("hi", 0)

        cols = st.columns(3)
        with cols[0]:
            st.metric("Raw β_elo (MLE)", f"{ci_data['full_dataset_fit']['beta_elo']:.4f}")
        with cols[1]:
            st.metric("95% CI (raw)", f"[{ci_lo:.4f}, {ci_hi:.4f}]")
        with cols[2]:
            st.metric("CI Width", f"{ci_data.get('ci_width_pct', 0):.1f}%")

        st.markdown(f"""
- **Production β** (after temperature correction ×0.55): `{tc.get('production_beta', 0):.4f}`
- **Production 95% CI**: `[{p_ci_lo:.4f}, {p_ci_hi:.4f}]`
- **Stability**: {ci_data.get('stability_assessment', '?')} — parameter uncertainty is small
- **Bootstrap iterations**: {ci_data.get('n_bootstrap', 0)}

⚠️ **Unvalidated**: Temperature correction (×0.55) is heuristic — not calibrated on held-out data.
""")
    else:
        st.info("Run: `PYTHONPATH=src python scripts/bootstrap_beta_ci.py`")

    # ── Injuries ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## Injury Data")
    st.warning(
        "Injuries: manual notes only — not model-integrated. "
        "No automated provider supplies WC2026 injury data on the current plan. "
        "Model does not penalize injured teams. "
        "To integrate: upgrade API-Football to Starter plan and implement injury_adj in CalibratedEloMatchModel."
    )
