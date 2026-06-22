"""
WC2026 Probabilistic Analytics Platform
World-class probabilistic tournament analysis
"""
from __future__ import annotations

import json
import math
import os
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

# ─── live engine (auto-updating scores/standings) ──────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass
try:
    from wc2026.live_engine import fetch_live_state, merge_and_persist, build_standings
    _LIVE_ENGINE = True
except Exception:
    _LIVE_ENGINE = False

try:
    from wc2026.web_analytics import inject as _inject_analytics
except Exception:
    def _inject_analytics(_st):  # analytics must never break the app
        return False

LIVE_REFRESH = max(20, int(os.getenv("LIVE_REFRESH_SECONDS", "45")))
# Auto-refresh only when a live provider key is available (offline/deploy = static snapshot).
AUTO_LIVE = _LIVE_ENGINE and bool(os.getenv("API_FOOTBALL_KEY"))


@st.cache_data(ttl=LIVE_REFRESH, show_spinner=False)
def cached_live_state(_bucket: int):
    """TTL-cached provider fetch. `_bucket` lets fragment reruns share a fetch within the TTL."""
    return fetch_live_state()

# ─── design system ────────────────────────────────────────────────────────────
BG0    = "#06060a"
BG1    = "#0c0c14"
BG2    = "#12121e"
BG3    = "#1a1a2e"
RED    = "#E63946"
TEAL   = "#2A9D8F"
GOLD   = "#E9C46A"
WHITE  = "#F0F0F8"
MUTED  = "#9C9CBD"   # readability patch: lifted from #6B6B8A for small/secondary text contrast
BORDER = "#2a2a42"   # readability patch: lifted from #1e1e32 so cards/gridlines separate from bg

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

# ─── premium UI layer (additive overrides; existing classes preserved above) ────
st.markdown(f"""<style>:root{{
  --bg0:{BG0};--bg1:{BG1};--bg2:{BG2};--bg3:{BG3};
  --red:{RED};--teal:{TEAL};--gold:{GOLD};--white:{WHITE};--muted:{MUTED};--border:{BORDER};
}}</style>""", unsafe_allow_html=True)

st.markdown("""<style>
/* hide raw-Streamlit chrome for a product feel */
header[data-testid="stHeader"]{background:transparent;height:0;overflow:visible!important}
[data-testid="stToolbarActions"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer{display:none!important}
/* keep the sidebar re-open arrow reachable even though the header is height:0 (else collapsing
   the sidebar leaves no way to reopen it) — float it top-left, on top, when Streamlit shows it. */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"],
header[data-testid="stHeader"] [data-testid="stBaseButton-headerNoPadding"]{
  position:fixed!important;top:10px;left:10px;z-index:2147483000!important;
  display:flex!important;opacity:1!important;visibility:visible!important;pointer-events:auto!important;
  background:var(--bg2)!important;border:1px solid var(--border)!important;border-radius:9px!important}
[data-testid="stExpandSidebarButton"] *{opacity:1!important;visibility:visible!important}
/* content rhythm + ambient depth */
.block-container{max-width:1320px;padding-top:1.4rem;padding-bottom:4rem}
.stApp{background:radial-gradient(1100px 560px at 82% -12%, rgba(42,157,143,0.06), transparent 60%), var(--bg0)}
h1{letter-spacing:-0.02em;line-height:1.08}
/* eyebrow + page description */
.eyebrow{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:var(--teal);display:block;margin-bottom:4px}
.page-desc{color:var(--muted);font-size:14px;max-width:780px;line-height:1.6;margin:2px 0 18px}
/* hero */
.hero{border:1px solid var(--border);border-radius:18px;padding:26px 30px;margin:2px 0 16px;background:linear-gradient(180deg,rgba(255,255,255,0.025),transparent),var(--bg1)}
.hero-title{font-family:'DM Serif Display',serif;font-size:2.5rem;line-height:1.04;color:var(--white);margin:0}
.hero-sub{color:var(--muted);font-size:15px;line-height:1.6;max-width:700px;margin-top:10px}
.kpi-row{display:flex;flex-wrap:wrap;gap:12px;margin-top:20px}
.kpi{flex:1;min-width:118px;border:1px solid var(--border);border-radius:13px;padding:14px 16px;background:var(--bg2)}
.kpi .v{font-family:'DM Serif Display',serif;font-size:1.65rem;color:var(--white);line-height:1}
.kpi .l{font-size:10px;letter-spacing:0.1em;text-transform:uppercase;color:var(--muted);margin-top:7px;font-weight:600}
/* favourite strip */
.fav-strip{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px}
.fav-card{border:1px solid var(--border);border-radius:13px;padding:11px 15px;min-width:106px;background:var(--bg2);transition:.15s}
.fav-card:hover{border-color:var(--teal);transform:translateY(-2px)}
.fav-rank{font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}
.fav-team{font-size:15px;font-weight:600;color:var(--white);margin:3px 0 1px}
.fav-prob{font-family:'DM Serif Display',serif;font-size:1.3rem;color:var(--teal)}
/* pills */
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 11px;border-radius:999px;font-size:11px;font-weight:600;font-family:'JetBrains Mono',monospace;letter-spacing:0.03em}
.pill-live{background:rgba(230,57,70,0.14);color:#ff6b78;border:1px solid rgba(230,57,70,0.4)}
.pill-snap{background:rgba(107,107,138,0.14);color:var(--muted);border:1px solid var(--border)}
.pill-ok{background:rgba(42,157,143,0.14);color:var(--teal);border:1px solid rgba(42,157,143,0.4)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.dot-live{background:#ff6b78;animation:pulse 1.8s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,107,120,.6)}70%{box-shadow:0 0 0 6px rgba(255,107,120,0)}100%{box-shadow:0 0 0 0 rgba(255,107,120,0)}}
/* trust chips */
.trust-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.trust-chip{font-size:11.5px;color:var(--muted);border:1px solid var(--border);border-radius:999px;padding:4px 12px;background:var(--bg2)}
.trust-chip b{color:var(--white)}
/* premium metric cards */
[data-testid="stMetric"]{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:15px 18px;transition:.15s}
[data-testid="stMetric"]:hover{border-color:rgba(42,157,143,0.45)}
[data-testid="stMetricValue"]{font-family:'DM Serif Display',serif!important}
.card{border-radius:14px}.caveat-box{border-radius:12px;line-height:1.55}.info-box{border-radius:12px;line-height:1.55}
/* sidebar */
section[data-testid="stSidebar"]{background:var(--bg1)!important}
.side-brand{font-family:'DM Serif Display',serif;font-size:1.5rem;color:var(--white);letter-spacing:-0.01em}
.side-tag{font-size:11px;color:var(--muted);margin:2px 0 12px;line-height:1.5}
.side-card{border:1px solid var(--border);border-radius:12px;padding:12px 14px;background:var(--bg2);font-size:11.5px;color:var(--muted);line-height:1.7;margin-top:8px}
.side-card b{color:var(--white)}
.side-label{font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:var(--muted);font-weight:600;margin:14px 0 6px}
/* nav radio -> clean menu */
section[data-testid="stSidebar"] div[role="radiogroup"]{gap:2px}
section[data-testid="stSidebar"] div[role="radiogroup"] label{padding:6px 10px;border-radius:9px;transition:.12s;border:1px solid transparent}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:var(--bg2)}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:var(--bg2);border-color:var(--border)}
section[data-testid="stSidebar"] div[role="radiogroup"] label p{font-size:13.5px!important;font-weight:500}
section[data-testid="stSidebar"] div[role="radiogroup"] label>div:first-child{display:none}
/* links + scrollbar + focus */
a,a:visited{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#23233a;border-radius:8px}::-webkit-scrollbar-track{background:transparent}
::selection{background:rgba(42,157,143,0.3)}:focus-visible{outline:2px solid var(--teal);outline-offset:2px}
/* ── readability patch: contrast + card separation (surgical, not overbright) ── */
/* captions / small secondary text — lift off dark-on-dark */
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p,[data-testid="stCaptionContainer"] *{color:#A7A7C8!important}
.page-desc,.hero-sub,.side-tag,.side-card,.trust-chip{color:#A7A7C8}
.side-card b,.trust-chip b{color:var(--white)}
.fav-rank,.kpi .l{color:#A7A7C8}
.side-label{color:#8C8CB0}
/* lift card surfaces slightly + soft shadow so they read as panels, not flat dark */
.card,.kpi,.fav-card,.side-card,[data-testid="stMetric"]{background:#15151f;box-shadow:0 6px 18px rgba(0,0,0,0.30)}
.hero{box-shadow:0 10px 30px rgba(0,0,0,0.34)}
[data-testid="stMetricLabel"]{color:#A7A7C8!important}
/* dataframes / tables: readable header + cell text on dark */
[data-testid="stDataFrame"] *{color:#E6E6F2}
/* expander + tab labels a touch brighter */
.streamlit-expanderHeader,details summary{color:#D7D7E6}
</style>""", unsafe_allow_html=True)


# ─── bilingual layer (EN/FR) ───────────────────────────────────────────────────
st.session_state.setdefault("lang_code", "EN")

TXT = {
    "EN": {
        "brand_tag": "World Cup 2026 · Forecast Lab",
        "lang_label": "Language",
        "nav_section": "Explore",
        "nav_overview": "🚀 Overview", "nav_champion": "🏆 Champion Tracker",
        "nav_live": "⚽ Live Standings", "nav_predictor": "🎯 Match Predictor",
        "nav_dna": "🧬 Nation DNA", "nav_h2h": "⚔️ Head-to-Head",
        "nav_history": "📜 Historical Records", "nav_bracket": "🔮 Bracket Paths",
        "nav_modellab": "🧮 Model Lab", "nav_data": "📡 Data Quality",
        "matches_played": "{n} / 104 matches played",
        "updated": "Updated", "model": "Model",
        "model_body": "Calibrated Elo → Dixon-Coles Poisson<br>+ ML 1X2 ensemble @ weight 0.20<br>100,000 Monte Carlo simulations<br>Live-conditioned on WC2026 results",
        "trust_label": "Trust",
        "trust_tests": "{n} tests passing", "trust_val": "4 World Cups validated",
        "trust_oss": "Open source on GitHub",
        "disclaimer": "Probabilities, not predictions. Not a betting product.",
        # Overview / hero
        "ov_eyebrow": "World Cup 2026 · Live forecast",
        "ov_title": "Tournament Command Center",
        "ov_sub": "Who's most likely to win the 2026 World Cup? Live winning chances for all 48 teams, updated automatically after every match. It's a probability — not a prediction.",
        "kpi_fav": "Favourite", "kpi_live": "Matches played", "kpi_sims": "Simulations",
        "kpi_tests": "Tests passing", "kpi_val": "World Cups validated",
        "ov_topfav": "Top contenders", "ov_links": "Project & links",
        "ov_data": "Data & providers", "ov_model": "Model & validation",
        "ov_uncert": "Uncertainty & honesty", "ov_deploy": "Deployment",
        "ov_status": "Public release · live",
        "ov_data_sum": "Four providers cross-checked; live scores from API-Football.",
        "ov_model_sum": "Calibrated Elo → Dixon-Coles with a leak-free ML layer at weight 0.20.",
        "ov_uncert_sum": "Champion figures are P5/P50/P95 intervals — a floor, not total uncertainty.",
        "ov_deploy_sum": "Live on Render; open source on GitHub; portfolio on Vercel.",
        "lk_live": "Live app", "lk_oss": "Open source", "lk_portfolio": "Portfolio",
        # Champion Tracker
        "ct_eyebrow": "Title race", "ct_title": "Champion Probabilities",
        "ct_desc": "100,000 Monte Carlo simulations · live-conditioned ({n}/104 played) · calibrated Elo→Dixon-Coles (β=0.544) with ML@0.20.",
        "ct_fav": "Favourite", "ct_top3": "Top-3 concentration", "ct_top5": "Top-5 combined", "ct_entropy": "Entropy (bits)",
        "ct_fav_help": "The single most likely winner — but far from certain.",
        "ct_top3_help": "Combined chance the winner is one of the 3 favourites. Higher = the race is concentrated.",
        "ct_top5_help": "Combined chance the winner is in the top 5 — a quick read on how open it is.",
        "ct_entropy_help": "How open the race is, in bits. Higher = more teams have a real shot (more uncertainty).",
        "ct_takeaway": "👉 <b>{flag} {team}</b> is the model's favourite at <b>{p}% to win</b> — but far from a lock: the top 5 teams share only <b>{top5}%</b> of the title between them. A probability, not a prediction.",
        "ct_caveat_title": "How to read this · honest limits",
        "ct_caveat_body": "**Honest model disclosure:** Temperature correction β×0.55 is heuristic — not optimized against external outcomes. WC2022 backtest: ARG was the model's #1 pick (19.3%), actual winner ✓. WC2018: FRA the #5 pick (5.6%), actual winner. At champion granularity the model's mean-Brier (~0.027) is on par with a uniform 1/48 null — the edge is in narrowing the field, not pinpointing one winner (n=2 backtested WCs). These are not betting probabilities.",
        # Live Standings
        "ls_eyebrow": "Group stage · live", "ls_title": "Live Group Standings",
        "ls_desc": "Auto-updating group tables. Live scores tick in; a result locks into the standings at full time.",
        "ls_live_now": "Live now", "ls_played": "Played matches",
        "ls_upcoming": "Today's upcoming matches", "ls_groups": "All 12 groups — current standings",
        "ls_injuries": "Key injury & fitness updates",
        "ls_predict": "Predict", "ls_pred": "model", "ls_pred_live": "model gave this score",
        "ls_rank": "rank", "ls_calendar": "Full calendar — all upcoming",
        "ls_predict_past": "👁️ See pre-match prediction", "ls_predict_fut": "🎯 Predict",
        "ls_see_all": "📅 See all upcoming matches", "ls_kickoff_in": "kick-off in",
        "ls_next_up": "Next up", "ls_prematch": "Pre-match", "ls_live_vs": "live score vs pre-match prediction",
        "ls_result_ok": "result called right", "ls_result_no": "result missed",
        "ls_col_past": "Played", "ls_col_std": "Standings", "ls_col_fut": "Upcoming", "ls_kickoff": "KICK-OFF",
        "ls_kickoff_passed": "kicked off · live score syncing", "ls_live_short": "LIVE",
        "ls_halftime": "HALF-TIME", "ls_extratime": "EXTRA TIME", "ls_penalties": "PENALTIES",
        "src_live": "live providers", "src_snap": "offline snapshot (set API_FOOTBALL_KEY for live auto-update)",
        # Data Quality
        "dq_eyebrow": "Sources & audit", "dq_title": "Data Quality & Source Audit",
        "dq_desc": "Every figure on this site is backed by a documented source. This page shows exactly what data we have, what we are missing, and how fresh it is.",
        "ls_takeaway": "👉 <b>{n}/104</b> group matches played. Top 2 of each group (plus the 8 best 3rd-placed teams) reach the knockouts. Scores update live.",
        "ml_takeaway": "👉 In plain words: Elo rates each team, Dixon-Coles turns ratings into score probabilities, a small ML layer (20%) sharpens it, then 100,000 simulations produce the odds. Everything below is the proof — dive in or skip it.",
        "dq_takeaway": "👉 Every number on this site is sourced. 4 live providers cross-checked, zero score disagreements. Below: what we have, what's missing, how fresh — skip unless you want the receipts.",
        "nav_scorecard": "📊 Scorecard",
        "sc_eyebrow": "Track record", "sc_title": "Model Scorecard",
        "sc_desc": "How the model's pre-match forecasts have actually held up, match by match — updated live, never cherry-picked.",
        "sc_take": "👉 Over <b>{n}</b> played matches, the model called <b>{acc}%</b> of results right and put on average <b>{p}%</b> on the exact final score. Judged on its full ranked forecast — not just its #1 pick.",
        "sc_acc": "Results called right", "sc_p": "Avg % on exact score",
        "sc_t1": "Exact score = #1 pick", "sc_t3": "Exact score in top 3",
        "sc_rps": "RPS (model)", "sc_rps_base": "RPS (coin-flip)", "sc_rank": "Avg rank of real score",
        "sc_best": "Best-called match", "sc_worst": "Biggest surprise",
        "sc_table": "Every match — forecast vs reality", "sc_live": "LIVE (provisional)",
        "sc_note": "RPS = the standard proper score for football forecasts (lower is better); shown next to the same-matches coin-flip (1/3-1/3-1/3) baseline — no inflated 'skill %'. Early on, small samples swing hard, so this can sit above the baseline before settling.",
        "sc_empty": "No finished matches yet — the scorecard fills as the tournament plays.",
        "sc_cols": "match · real score · model's top scores · % on real score · rank · result",
        "sc_comp_title": "Across competitions — same model, scored the same way",
        "sc_comp_note": "The Elo→Dixon-Coles core scored on every competition since 2010 (rolling pre-match Elos). 'WC2026 (live)' is this tournament so far. Lower RPS = better; every competition beats the coin-flip baseline.",
        "empty_same_team": "Please select two different teams.",
        "empty_no_prob": "No probability data.",
        "empty_no_wc_hist": "No WC history data.",
        "empty_no_pen": "No WC penalty shootout history.",
        "empty_no_form": "No form data available.",
        "empty_no_squad": "No squad attribute data.",
        "empty_no_pair": "No pair with 5+ meetings found in this selection.",
        # Model Lab
        "ml_eyebrow": "Methodology", "ml_title": "Model Laboratory",
        "ml_desc": "Full mathematical transparency, honest limitations, and a self-assessed maturity audit.",
        "ml_hint": "💡 The \"show-your-work\" section — the math and honest limits behind the forecast. Curious? Dive in. In a hurry? You can skip it.",
        "dq_hint": "💡 Where every number comes from — sources, freshness and honest caveats. Skip it unless you want to check the receipts.",
        # other page headers
        "mp_eyebrow": "Single match", "mp_title": "Match Probability Engine",
        "mp_desc": "Win / draw / loss and scoreline probabilities for any pairing, from the same calibrated engine.",
        "mp_dna": "DNA matchup — both squads overlaid", "mp_dna_full": "Full DNA:",
        "mp_dna_note": "Analyst-prior squad ratings (Expert model only) — not used in the live probability forecast.",
        "dna_eyebrow": "Team profiles", "dna_title": "Nation DNA",
        "dna_desc": "Style and rating fingerprints for every qualified nation.",
        "h2h_eyebrow": "Rivalries", "h2h_title": "Head-to-Head",
        "h2h_desc": "Historical meetings and the model's read on any matchup.",
        "hist_eyebrow": "Archive", "hist_title": "Historical Records",
        "hist_desc": "World Cup winners, hosts and records since 1930.",
        "br_eyebrow": "Knockout map", "br_title": "Bracket & Path Analysis",
        "br_desc": "Stage-by-stage progression and the road each contender must travel.",
    },
    "FR": {
        "brand_tag": "Coupe du monde 2026 · Labo de prévision",
        "lang_label": "Langue",
        "nav_section": "Explorer",
        "nav_overview": "🚀 Vue d'ensemble", "nav_champion": "🏆 Course au titre",
        "nav_live": "⚽ Classements en direct", "nav_predictor": "🎯 Prédiction de match",
        "nav_dna": "🧬 ADN des nations", "nav_h2h": "⚔️ Confrontations",
        "nav_history": "📜 Palmarès historique", "nav_bracket": "🔮 Parcours & tableau",
        "nav_modellab": "🧮 Labo du modèle", "nav_data": "📡 Qualité des données",
        "matches_played": "{n} / 104 matchs joués",
        "updated": "Mis à jour", "model": "Modèle",
        "model_body": "Elo calibré → Poisson Dixon-Coles<br>+ ensemble ML 1X2 (poids 0,20)<br>100 000 simulations Monte-Carlo<br>Conditionné en direct sur les résultats CDM2026",
        "trust_label": "Confiance",
        "trust_tests": "{n} tests au vert", "trust_val": "4 Coupes du monde validées",
        "trust_oss": "Open source sur GitHub",
        "disclaimer": "Des probabilités, pas des prédictions. Ce n'est pas un outil de paris.",
        "ov_eyebrow": "Coupe du monde 2026 · Prévision en direct",
        "ov_title": "Centre de commande du tournoi",
        "ov_sub": "Qui a le plus de chances de gagner la Coupe du monde 2026 ? Les chances de victoire des 48 équipes, en direct, mises à jour automatiquement après chaque match. Une probabilité — pas une prédiction.",
        "kpi_fav": "Favori", "kpi_live": "Matchs joués", "kpi_sims": "Simulations",
        "kpi_tests": "Tests au vert", "kpi_val": "Coupes du monde validées",
        "ov_topfav": "Principaux prétendants", "ov_links": "Projet & liens",
        "ov_data": "Données & fournisseurs", "ov_model": "Modèle & validation",
        "ov_uncert": "Incertitude & honnêteté", "ov_deploy": "Déploiement",
        "ov_status": "Version publique · en ligne",
        "ov_data_sum": "Quatre fournisseurs recoupés ; scores en direct via API-Football.",
        "ov_model_sum": "Elo → Dixon-Coles calibré avec une couche ML sans fuite, poids 0,20.",
        "ov_uncert_sum": "Les chiffres de titre sont des intervalles P5/P50/P95 — un plancher, pas l'incertitude totale.",
        "ov_deploy_sum": "En ligne sur Render ; open source sur GitHub ; portfolio sur Vercel.",
        "lk_live": "Appli en direct", "lk_oss": "Open source", "lk_portfolio": "Portfolio",
        "ct_eyebrow": "Course au titre", "ct_title": "Probabilités de titre",
        "ct_desc": "100 000 simulations Monte-Carlo · conditionné en direct ({n}/104 joués) · Elo→Dixon-Coles calibré (β=0,544) avec ML@0,20.",
        "ct_fav": "Favori", "ct_top3": "Concentration top-3", "ct_top5": "Cumul top-5", "ct_entropy": "Entropie (bits)",
        "ct_fav_help": "Le vainqueur le plus probable — mais loin d'être certain.",
        "ct_top3_help": "Probabilité cumulée que le vainqueur soit l'un des 3 favoris. Plus c'est haut, plus la course est resserrée.",
        "ct_top5_help": "Probabilité cumulée que le vainqueur soit dans le top 5 — un coup d'œil sur l'ouverture de la course.",
        "ct_entropy_help": "À quel point la course est ouverte, en bits. Plus c'est haut, plus d'équipes ont une vraie chance.",
        "ct_takeaway": "👉 <b>{flag} {team}</b> est le favori du modèle à <b>{p}% de chances</b> — mais loin d'être plié : les 5 premiers ne cumulent que <b>{top5}%</b> du titre à eux tous. Une probabilité, pas une prédiction.",
        "ct_caveat_title": "Comment lire ça · limites honnêtes",
        "ct_caveat_body": "**Divulgation honnête :** la correction de température β×0,55 est heuristique — non optimisée sur des résultats externes. Backtest CDM2022 : ARG était le favori du modèle (19,3%), vainqueur réel ✓. CDM2018 : FRA était le 5e choix (5,6%), vainqueur réel. Au niveau du titre, le mean-Brier du modèle (~0,027) équivaut à un tirage uniforme 1/48 — l'avantage est de resserrer le peloton, pas de désigner le vainqueur unique (n=2 CDM backtestées). Ce ne sont pas des probabilités de paris.",
        "ls_eyebrow": "Phase de groupes · direct", "ls_title": "Classements de groupe en direct",
        "ls_desc": "Tableaux de groupes mis à jour automatiquement. Les scores défilent en direct ; un résultat est verrouillé au classement au coup de sifflet final.",
        "ls_live_now": "En direct", "ls_played": "Matchs joués",
        "ls_upcoming": "Matchs du jour à venir", "ls_groups": "Les 12 groupes — classement actuel",
        "ls_injuries": "Blessures & infos forme",
        "ls_predict": "Prédire", "ls_pred": "modèle", "ls_pred_live": "le modèle donnait ce score",
        "ls_rank": "rang", "ls_calendar": "Calendrier complet — tous les prochains",
        "ls_predict_past": "👁️ Voir prédiction avant match", "ls_predict_fut": "🎯 Prédire",
        "ls_see_all": "📅 Voir tous les futurs matchs", "ls_kickoff_in": "coup d'envoi dans",
        "ls_next_up": "Prochains matchs", "ls_prematch": "Avant-match", "ls_live_vs": "score en direct vs prédiction d'avant-match",
        "ls_result_ok": "résultat bien vu", "ls_result_no": "résultat manqué",
        "ls_col_past": "Matchs joués", "ls_col_std": "Classements", "ls_col_fut": "Matchs à venir", "ls_kickoff": "COUP D’ENVOI",
        "ls_kickoff_passed": "coup d’envoi donné · score en direct imminent", "ls_live_short": "EN DIRECT",
        "ls_halftime": "MI-TEMPS", "ls_extratime": "PROL.", "ls_penalties": "TIRS AU BUT",
        "src_live": "fournisseurs en direct", "src_snap": "instantané hors-ligne (définir API_FOOTBALL_KEY pour le direct)",
        "dq_eyebrow": "Sources & audit", "dq_title": "Qualité des données & audit des sources",
        "dq_desc": "Chaque chiffre de ce site repose sur une source documentée. Cette page montre exactement les données disponibles, ce qui manque, et leur fraîcheur.",
        "ls_takeaway": "👉 <b>{n}/104</b> matchs de poule joués. Les 2 premiers de chaque groupe (plus les 8 meilleurs 3es) filent en élimination directe. Scores en direct.",
        "ml_takeaway": "👉 En clair : Elo note chaque équipe, Dixon-Coles transforme ça en probabilités de score, une petite couche ML (20%) affine, puis 100 000 simulations donnent les cotes. Tout ce qui suit est la preuve — plonge ou passe.",
        "dq_takeaway": "👉 Chaque chiffre du site est sourcé. 4 fournisseurs recoupés, zéro désaccord de score. Ci-dessous : ce qu'on a, ce qui manque, la fraîcheur — à sauter sauf si tu veux les preuves.",
        "nav_scorecard": "📊 Bulletin",
        "sc_eyebrow": "Bilan réel", "sc_title": "Bulletin du modèle",
        "sc_desc": "Comment les prévisions d'avant-match tiennent vraiment, match par match — en direct, jamais trié sur le volet.",
        "sc_take": "👉 Sur <b>{n}</b> matchs joués, le modèle a vu juste sur <b>{acc}%</b> des résultats et a misé en moyenne <b>{p}%</b> sur le score exact final. Jugé sur sa prévision classée complète — pas seulement son 1er choix.",
        "sc_acc": "Résultats vus juste", "sc_p": "% moyen sur le score exact",
        "sc_t1": "Score exact = 1er choix", "sc_t3": "Score exact dans le top 3",
        "sc_rps": "RPS (modèle)", "sc_rps_base": "RPS (pile ou face)", "sc_rank": "Rang moyen du vrai score",
        "sc_best": "Match le mieux vu", "sc_worst": "Plus grosse surprise",
        "sc_table": "Chaque match — prévu vs réalité", "sc_live": "EN DIRECT (provisoire)",
        "sc_note": "RPS = le score de référence pour les prévisions foot (plus bas = mieux) ; affiché à côté du baseline pile-ou-face (1/3-1/3-1/3) sur les mêmes matchs — aucun « % de skill » gonflé. Au début, les petits échantillons font tout bouger, donc ça peut dépasser le baseline avant de se stabiliser.",
        "sc_empty": "Aucun match terminé pour l'instant — le bulletin se remplit au fil du tournoi.",
        "sc_cols": "match · score réel · meilleurs scores du modèle · % sur le score réel · rang · résultat",
        "sc_comp_title": "Sur les compétitions — même modèle, même mesure",
        "sc_comp_note": "Le cœur Elo→Dixon-Coles mesuré sur chaque compétition depuis 2010 (Elos roulants d'avant-match). « CDM2026 (live) » = ce tournoi jusqu'ici. RPS plus bas = mieux ; chaque compétition bat le pile-ou-face.",
        "empty_same_team": "Choisis deux équipes différentes.",
        "empty_no_prob": "Pas de données de probabilité.",
        "empty_no_wc_hist": "Pas de données d'historique Coupe du monde.",
        "empty_no_pen": "Pas d'historique de tirs au but en Coupe du monde.",
        "empty_no_form": "Pas de données de forme disponibles.",
        "empty_no_squad": "Pas de données d'attributs d'effectif.",
        "empty_no_pair": "Aucune paire avec 5+ confrontations dans cette sélection.",
        "ml_eyebrow": "Méthodologie", "ml_title": "Laboratoire du modèle",
        "ml_desc": "Transparence mathématique complète, limites assumées, et un audit de maturité auto-évalué.",
        "ml_hint": "💡 La section \"on montre nos calculs\" — les maths et les limites assumées derrière la prévision. Curieux ? Plonge. Pressé ? Tu peux passer.",
        "dq_hint": "💡 D'où vient chaque chiffre — sources, fraîcheur et limites assumées. À sauter, sauf si tu veux vérifier nos sources.",
        "mp_eyebrow": "Match unique", "mp_title": "Moteur de probabilités de match",
        "mp_desc": "Probabilités victoire / nul / défaite et de score pour toute affiche, depuis le même moteur calibré.",
        "mp_dna": "ADN croisé — les deux squads superposés", "mp_dna_full": "ADN complet :",
        "mp_dna_note": "Notes analystes des effectifs (modèle Expert) — non utilisées dans la prévision live.",
        "dna_eyebrow": "Profils d'équipe", "dna_title": "ADN des nations",
        "dna_desc": "Empreintes de style et de niveau pour chaque nation qualifiée.",
        "h2h_eyebrow": "Rivalités", "h2h_title": "Confrontations",
        "h2h_desc": "Rencontres historiques et la lecture du modèle sur chaque affiche.",
        "hist_eyebrow": "Archives", "hist_title": "Palmarès historique",
        "hist_desc": "Vainqueurs, hôtes et records de la Coupe du monde depuis 1930.",
        "br_eyebrow": "Tableau final", "br_title": "Tableau & analyse des parcours",
        "br_desc": "Progression étape par étape et la route que chaque prétendant doit parcourir.",
    },
}

def t(key: str, **kw) -> str:
    """Bilingual lookup with EN fallback; never raises on a missing key."""
    lang = st.session_state.get("lang_code") or "EN"
    s = TXT.get(lang, TXT["EN"]).get(key)
    if s is None:
        s = TXT["EN"].get(key, key)
    return s.format(**kw) if kw else s

def page_header(eyebrow_key: str, title_key: str, desc_key: Optional[str] = None, **kw) -> None:
    """Consistent premium page header: eyebrow + title + optional description."""
    st.markdown(f"<span class='eyebrow'>{t(eyebrow_key)}</span>", unsafe_allow_html=True)
    st.markdown(f"# {t(title_key)}")
    if desc_key:
        st.markdown(f"<div class='page-desc'>{t(desc_key, **kw)}</div>", unsafe_allow_html=True)

def takeaway(html: str) -> None:
    """Plain one-line 'answer first' banner — instant payoff before any dense content."""
    st.markdown(
        f"<div style='font-size:15.5px;line-height:1.55;background:{BG2};border:1px solid {BORDER};"
        f"border-left:3px solid {TEAL};border-radius:10px;padding:12px 16px;margin:2px 0 14px'>"
        f"{html}</div>", unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def _score_engine():
    """Cached production model + pre-tournament teams, for live per-match score predictions."""
    from wc2026.scorecard import get_model_and_teams
    return get_model_and_teams()

@st.cache_data(ttl=900, show_spinner=False)
def _full_schedule():
    """All 104 WC2026 fixtures with real dates + kick-off times (offline OpenFootball schedule).
    The reliable forward source for 'next matches' + countdowns — independent of the live feed."""
    try:
        from wc2026.providers.router import ProviderRouter
        return ProviderRouter().get_full_schedule() or []
    except Exception:
        return []

@st.cache_resource(show_spinner=False)
def _predictor_model():
    """Cached (teams, config, params, model) for the Match Predictor — built ONCE, not on every
    selectbox change (was reloading teams + rebuilding the model on each keystroke → page lag)."""
    from wc2026.data_loader import load_teams, load_config
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    teams_obj = load_teams(apply_temporal_form=True)
    cfg = load_config()
    _lp = DATA / "elo_live_params.json"
    params = json.loads(_lp.read_text()) if _lp.exists() else None
    return teams_obj, cfg, params, CalibratedEloMatchModel(config=cfg, params=params)

@st.cache_data(ttl=3600, show_spinner=False)
def _csc(home, away, ha, ab, knockout):
    """Memoised score_match — the Live Standings renders ~40 finished matches per refresh; without
    this each render recomputes every scoreline distribution (the main on-Render lag)."""
    from wc2026.scorecard import score_match
    model, teams = _score_engine()
    return score_match(model, teams, home, away, ha, ab, knockout=knockout)

@st.cache_data(ttl=3600, show_spinner=False)
def _cpred(home, away, k, knockout):
    """Memoised predicted_scores for upcoming fixtures (static → cache hard)."""
    from wc2026.scorecard import predicted_scores
    model, teams = _score_engine()
    return predicted_scores(model, teams, home, away, k=k, knockout=knockout)

# Cross-page navigation: a button sets st.session_state["_goto"] (a NON-widget key) + reruns;
# this transfers it onto the nav radio BEFORE that widget is created (Streamlit forbids setting
# a widget's state after it renders). Used by "click a match → Match Predictor".
if st.session_state.get("_goto"):
    st.session_state["page_nav"] = st.session_state.pop("_goto")


# Consent-gated PostHog analytics (no-op unless POSTHOG_KEY is set in env). Privacy-first:
# nothing loads or tracks until the visitor clicks Accept. See src/wc2026/web_analytics.py.
_inject_analytics(st)


# ─── data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_live_summary() -> pd.DataFrame:
    # Displayed forecast = the CALIBRATED model (Elo→Dixon-Coles + ML@0.20).
    # Order: live-conditioned calibrated → pre-tournament calibrated. We deliberately do NOT
    # fall back to summary.csv (that is the legacy EXPERT analyst-prior model — different favourite)
    # so the dashboard can never silently display a different model. See outputs/tournament_run/ARTIFACTS.md.
    p = OUTPUTS / "live_summary.csv"
    if p.exists():
        return pd.read_csv(p)
    cal = OUTPUTS / "elo_calibrated_summary.csv"
    if cal.exists():
        return pd.read_csv(cal)
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

# The headline match counter (sidebar, hero, Champion Tracker) must reflect the LIVE state —
# not the persisted snapshot, which only updates when a visitor opens Live Standings. Without
# this, "/104" stays frozen on the committed snapshot. Failure-safe; falls back to the snapshot.
def _live_count_and_updated():
    if AUTO_LIVE:
        try:
            import time as _t
            from datetime import datetime as _dt, timezone as _tz
            _s = cached_live_state(int(_t.time() // LIVE_REFRESH))
            if _s.get("ok"):
                return len(_s.get("all_completed", [])), "live · " + _dt.now(_tz.utc).strftime("%H:%M UTC")
        except Exception:
            pass
    return len(live_data.get("completed_matches", [])), live_data.get("last_updated", "—")

n_played, last_upd_global = _live_count_and_updated()

# Merge display names into elo_df
if not elo_df.empty and not disp_df.empty and "full_name" not in elo_df.columns:
    elo_df = elo_df.merge(
        disp_df[["code", "full_name", "flag", "confederation", "nickname"]],
        left_on="team", right_on="code", how="left"
    ).drop(columns=["code"], errors="ignore")


# ─── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="side-brand">⚽ WC2026</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-tag">{t("brand_tag")}</div>', unsafe_allow_html=True)

    # Language selector (EN / FR). Stored in session_state["lang_code"]; t() reads it.
    st.segmented_control(t("lang_label"), ["EN", "FR"], key="lang_code",
                         label_visibility="collapsed")

    live_pill = ('<span class="pill pill-live"><span class="dot dot-live"></span>LIVE</span>'
                 if AUTO_LIVE else '<span class="pill pill-snap">SNAPSHOT</span>')
    st.markdown(
        f'<div style="margin:10px 0 2px">'
        f'<span class="pill pill-ok">{t("matches_played", n=n_played)}</span> {live_pill}</div>',
        unsafe_allow_html=True,
    )
    last_upd = last_upd_global
    st.markdown(
        f"<div style='font-size:11px;color:{MUTED};margin:6px 0 12px'>{t('updated')}: {last_upd}</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="side-label">{t("nav_section")}</div>', unsafe_allow_html=True)
    # Stable dispatch keys (left) → translated display labels (right). The page body
    # dispatch below still matches on the stable key, so translation is display-only.
    NAV = {
        "🚀 Release Status": t("nav_overview"), "🏆 Champion Tracker": t("nav_champion"),
        "📊 Scorecard": t("nav_scorecard"),
        "⚽ Live Standings": t("nav_live"), "🎯 Match Predictor": t("nav_predictor"),
        "🧬 Nation DNA": t("nav_dna"), "⚔️ Head-to-Head": t("nav_h2h"),
        "📜 Historical Records": t("nav_history"), "🔮 Bracket Paths": t("nav_bracket"),
        "🧮 Model Lab": t("nav_modellab"), "📡 Data Quality": t("nav_data"),
    }
    page = st.radio("nav", list(NAV.keys()), format_func=lambda k: NAV[k],
                    label_visibility="collapsed", key="page_nav")

    st.markdown(f'<div class="side-label">{t("model")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="side-card">{t("model_body")}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="side-label">{t("trust_label")}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="side-card">
        <b>{t("trust_tests", n=574)}</b> · <span style='color:{GOLD}'>6.93 / 10</span> maturity (self, honest)<br>
        {t("trust_val")} · Elo→Dixon-Coles + Monte Carlo<br>
        <a href="https://github.com/Yorian-melki/wc2026-forecast-lab" target="_blank">{t("trust_oss")}</a>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:10.5px;color:{MUTED};margin-top:12px;line-height:1.5'>{t('disclaimer')}</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 0 — RELEASE STATUS (v6 public release)
# ══════════════════════════════════════════════════════════════════════════════
if page == "🚀 Release Status":
    # ── hero cockpit ──────────────────────────────────────────────────────────
    live_pill = ('<span class="pill pill-live"><span class="dot dot-live"></span>LIVE</span>'
                 if AUTO_LIVE else '<span class="pill pill-snap">SNAPSHOT</span>')
    fav_val, contenders_html = "—", ""
    if not elo_df.empty and "champion_prob" in elo_df.columns:
        top = elo_df.nlargest(1, "champion_prob").iloc[0]
        fav_val = f"{flag(top['team'], disp_df)} {top['team']}"
        fav_sub = f"{top['champion_prob']*100:.1f}% · {t('kpi_fav')}"
        for i, (_, r) in enumerate(elo_df.nlargest(6, "champion_prob").iterrows(), 1):
            contenders_html += (
                f"<div class='fav-card'><div class='fav-rank'>#{i}</div>"
                f"<div class='fav-team'>{flag(r['team'], disp_df)} {r['team']}</div>"
                f"<div class='fav-prob'>{r['champion_prob']*100:.1f}%</div></div>")
    else:
        fav_sub = t("kpi_fav")

    st.markdown(
        f"""<div class="hero">
          <span class="eyebrow">{t('ov_eyebrow')}</span>&nbsp;&nbsp;{live_pill}
          <div class="hero-title">{t('ov_title')}</div>
          <div class="hero-sub">{t('ov_sub')}</div>
          <div class="kpi-row">
            <div class="kpi"><div class="v">{fav_val}</div><div class="l">{fav_sub}</div></div>
            <div class="kpi"><div class="v">{n_played} / 104</div><div class="l">{t('kpi_live')}</div></div>
            <div class="kpi"><div class="v">100K</div><div class="l">{t('kpi_sims')}</div></div>
            <div class="kpi"><div class="v">574</div><div class="l">{t('kpi_tests')}</div></div>
            <div class="kpi"><div class="v">4</div><div class="l">{t('kpi_val')}</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

    # ── top contenders strip ──────────────────────────────────────────────────
    if contenders_html:
        st.markdown(f"<span class='eyebrow'>{t('ov_topfav')}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='fav-strip'>{contenders_html}</div>", unsafe_allow_html=True)

    # ── trust chips ───────────────────────────────────────────────────────────
    st.markdown(
        f"""<div class="trust-row">
          <span class="trust-chip"><b>574</b> {t('trust_tests', n='').strip()}</span>
          <span class="trust-chip"><b>4</b> {t('kpi_val')}</span>
          <span class="trust-chip"><b>6.93</b> / 10 maturity</span>
          <span class="trust-chip">Elo → Dixon-Coles + ML@0.20</span>
          <span class="trust-chip">100,000 Monte Carlo</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("")

    # ── info cards (2×2): data · model · uncertainty · deployment ──────────────
    def _card(title_key, sum_key, facts_html):
        return (f"<div class='card'><div class='eyebrow'>{t(title_key)}</div>"
                f"<div style='color:{WHITE};font-size:13.5px;margin:2px 0 8px'>{t(sum_key)}</div>"
                f"<div style='color:{MUTED};font-size:12px;line-height:1.7'>{facts_html}</div></div>")

    r1 = st.columns(2)
    r1[0].markdown(_card("ov_data", "ov_data_sum",
        "● TheStatsAPI — shotmap xG · odds · stats (active, trial)<br>"
        "● API-Football — live score / events / lineups<br>"
        "● Highlightly — team xG · ● football-data.org — standings<br>"
        "<i>xG caveat: Highlightly ≈ TheStatsAPI upstream — not independent.</i>"), unsafe_allow_html=True)
    r1[1].markdown(_card("ov_model", "ov_model_sum",
        "Leak-free ML 1X2 (Brier 0.508 vs 0.529) wired at weight 0.20.<br>"
        "0.50 weight rejected — over-concentrated favourites.<br>"
        "Walk-forward: WC2010 / 2014 / 2018 / 2022.<br>"
        "Market odds = benchmark, not blended."), unsafe_allow_html=True)
    r2 = st.columns(2)
    r2[0].markdown(_card("ov_uncert", "ov_uncert_sum",
        "Champion bands propagate β sampling only — a documented floor.<br>"
        "Not tournament-calibrated (4 WCs). Not a betting product.<br>"
        "Audit trail: model card · data lineage · reviewer attack audit."), unsafe_allow_html=True)
    r2[1].markdown(_card("ov_deploy", "ov_deploy_sum",
        "✅ Live app — wc2026.yorian-melki.com (Render)<br>"
        "✅ Open source — github.com/Yorian-melki/wc2026-forecast-lab<br>"
        "✅ Portfolio — yorian-melki.com (Vercel)"), unsafe_allow_html=True)

    # ── links row ─────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='margin-top:6px;font-size:13px'>"
        f"🌐 <a href='https://wc2026.yorian-melki.com' target='_blank'>{t('lk_live')}</a> &nbsp;·&nbsp; "
        f"🧪 <a href='https://github.com/Yorian-melki/wc2026-forecast-lab' target='_blank'>{t('lk_oss')}</a> &nbsp;·&nbsp; "
        f"💼 <a href='https://www.yorian-melki.com' target='_blank'>{t('lk_portfolio')}</a></div>",
        unsafe_allow_html=True)
    st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — CHAMPION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏆 Champion Tracker":
    page_header("ct_eyebrow", "ct_title", "ct_desc", n=n_played)

    if elo_df.empty:
        st.error("Forecast output not found. Run `PYTHONPATH=src python scripts/run_live_simulation.py` to (re)generate it.")
        st.stop()

    # Top-line metrics
    top_team  = elo_df.nlargest(1, "champion_prob").iloc[0]
    top3_sum  = float(elo_df.nlargest(3, "champion_prob")["champion_prob"].sum())
    top5_sum  = float(elo_df.nlargest(5, "champion_prob")["champion_prob"].sum())
    ent       = float(-np.sum(elo_df["champion_prob"] * np.log2(elo_df["champion_prob"] + 1e-15)))

    # Plain one-line takeaway FIRST — instant payoff for any reader (the TDAH-friendly TL;DR).
    st.markdown(
        f"<div style='font-size:15.5px;line-height:1.55;background:{BG2};border:1px solid {BORDER};"
        f"border-left:3px solid {TEAL};border-radius:10px;padding:12px 16px;margin:2px 0 14px'>"
        + t("ct_takeaway", flag=top_team.get('flag', ''), team=top_team['team'],
            p=f"{top_team['champion_prob']*100:.0f}", top5=f"{top5_sum*100:.0f}")
        + "</div>",
        unsafe_allow_html=True)

    # Honest caveats — COLLAPSED (depth on demand for quants; everyone else just skips it).
    with st.expander("ℹ️ " + t("ct_caveat_title")):
        st.markdown(t("ct_caveat_body"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"🏆 {t('ct_fav')}",
              f"{top_team.get('flag', '')} {top_team['team']}",
              f"{top_team['champion_prob']*100:.1f}%", help=t("ct_fav_help"))
    c2.metric(t("ct_top3"), f"{top3_sum*100:.1f}%", delta_color="off", help=t("ct_top3_help"))
    c3.metric(t("ct_top5"),      f"{top5_sum*100:.1f}%", delta_color="off", help=t("ct_top5_help"))
    c4.metric(t("ct_entropy"),
              f"{ent:.2f} / {math.log2(48):.2f}",
              f"{ent/math.log2(48)*100:.0f}% of max uncertainty",
              delta_color="off", help=t("ct_entropy_help"))

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
        st.plotly_chart(fig, width="stretch")

        if "champion_ci_low" in elo_df.columns:
            with st.expander("Wilson 95% confidence intervals (sampling uncertainty only — not parameter uncertainty)"):
                ci_tbl = elo_df.nlargest(16, "champion_prob")[
                    ["team", "champion_prob", "champion_ci_low", "champion_ci_high"]
                ].copy()
                ci_tbl.columns = ["Team", "P(Champion)", "CI−95%", "CI+95%"]
                for c in ["P(Champion)", "CI−95%", "CI+95%"]:
                    ci_tbl[c] = (ci_tbl[c] * 100).round(2).astype(str) + "%"
                st.dataframe(ci_tbl, width="stretch", hide_index=True)
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
            st.plotly_chart(fig2, width="stretch")

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
        st.dataframe(disp_full, width="stretch", hide_index=True, height=600)

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
        st.plotly_chart(fig_conf, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1b — MODEL SCORECARD (live track record: forecast vs reality)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Scorecard":
    page_header("sc_eyebrow", "sc_title", "sc_desc")
    import time as _t
    from wc2026.scorecard import compute_scorecard
    _state = cached_live_state(int(_t.time() // LIVE_REFRESH)) if AUTO_LIVE else {}
    if _state.get("ok"):
        _completed, _live = _state.get("all_completed", []), _state.get("live", [])
    else:
        _completed, _live = live_data.get("completed_matches", []), []
    sc = compute_scorecard(_completed, live=_live or None)
    s = sc["summary"]
    if s["n_matches"] == 0:
        st.info(t("sc_empty")); st.stop()

    takeaway(t("sc_take", n=s["n_matches"],
              acc=f"{s['outcome_accuracy']*100:.0f}", p=f"{s['mean_prob_actual_score']*100:.0f}"))
    a1, a2, a3, a4 = st.columns(4)
    a1.metric(t("sc_acc"), f"{s['outcome_accuracy']*100:.0f}%")
    a2.metric(t("sc_p"), f"{s['mean_prob_actual_score']*100:.1f}%")
    a3.metric(t("sc_t1"), f"{s['exact_hit_top1']*100:.0f}%")
    a4.metric(t("sc_t3"), f"{s['exact_hit_top3']*100:.0f}%")
    b1, b2, b3 = st.columns(3)
    rps_better = s["mean_rps"] <= s["rps_baseline_uniform"]
    b1.metric(t("sc_rps"), f"{s['mean_rps']:.3f}",
              delta=("✓ beats coin-flip" if rps_better else "✗ below coin-flip"),
              delta_color="normal" if rps_better else "inverse")
    b2.metric(t("sc_rps_base"), f"{s['rps_baseline_uniform']:.3f}", delta_color="off")
    b3.metric(t("sc_rank"), f"{s['mean_score_rank']:.1f}", delta_color="off")

    bst, wst = sc["best"], sc["worst"]
    if bst and wst:
        cb, cw = st.columns(2)
        cb.markdown(
            f"<div class='card'><div class='eyebrow'>{t('sc_best')}</div>"
            f"<div style='font-size:15px'>{flag(bst['home'],disp_df)} {bst['home']} "
            f"<b>{bst['score']}</b> {bst['away']} {flag(bst['away'],disp_df)}</div>"
            f"<div style='color:{TEAL};font-size:13px'>{bst['p_actual']*100:.1f}% on that exact score · rank {bst['rank']}</div></div>",
            unsafe_allow_html=True)
        cw.markdown(
            f"<div class='card'><div class='eyebrow'>{t('sc_worst')}</div>"
            f"<div style='font-size:15px'>{flag(wst['home'],disp_df)} {wst['home']} "
            f"<b>{wst['score']}</b> {wst['away']} {flag(wst['away'],disp_df)}</div>"
            f"<div style='color:{RED};font-size:13px'>only {wst['p_actual']*100:.1f}% · rank {wst['rank']}</div></div>",
            unsafe_allow_html=True)

    st.markdown(f"### {t('sc_table')}")
    st.caption(t("sc_cols"))
    table = []
    for m in sc["matches"]:
        tops = " · ".join(f"{x['s']} {x['p']*100:.0f}%" for x in m["top_scores"][:3])
        table.append({
            "·": (f"🔴 {m['minute']}'" if m.get("minute") else "🔴") if m["live"] else "",
            "Match": f"{flag(m['home'],disp_df)} {m['home']}–{m['away']} {flag(m['away'],disp_df)}",
            "Score": m["score"],
            "Model's top scores": tops,
            "% real": f"{m['p_actual']*100:.1f}%",
            "Rank": m["rank"],
            "Result": "✅" if m["outcome_ok"] else "❌",
        })
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
    st.caption(t("sc_note"))

    # ── across competitions (backtest comparison) ─────────────────────────────
    comp_path = AUDIT / "competition_backtest.json"
    if comp_path.exists():
        st.markdown(f"### {t('sc_comp_title')}")
        comp = json.loads(comp_path.read_text())
        crows = [{
            "Competition": "🔴 WC2026 (live)", "Matches": s["n_matches"],
            "Outcome %": f"{s['outcome_accuracy']*100:.0f}%", "RPS": f"{s['mean_rps']:.3f}",
            "vs coin-flip": f"{s['rps_baseline_uniform']:.3f}", "Top-3 exact": f"{s['exact_hit_top3']*100:.0f}%",
        }]
        for name, r in comp.get("competitions", {}).items():
            crows.append({
                "Competition": name, "Matches": r["n"],
                "Outcome %": f"{r['outcome_accuracy']*100:.0f}%", "RPS": f"{r['mean_rps']:.3f}",
                "vs coin-flip": f"{r['rps_uniform']:.3f}", "Top-3 exact": f"{r['exact_top3']*100:.0f}%",
            })
        st.dataframe(pd.DataFrame(crows), hide_index=True, width="stretch")
        st.caption(t("sc_comp_note"))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — LIVE STANDINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚽ Live Standings":
    @st.fragment(run_every=(LIVE_REFRESH if AUTO_LIVE else None))
    def _live_standings():
        import time as _t
        import re as _re
        from datetime import datetime as _dt2, timedelta as _td2, timezone as _tz2
        import streamlit.components.v1 as _components
        from wc2026.scorecard import score_match, predicted_scores
        model, teams = _score_engine()

        state = cached_live_state(int(_t.time() // LIVE_REFRESH)) if AUTO_LIVE else {"ok": False}
        if state.get("ok"):
            mg = merge_and_persist(state)              # lock finished results into standings
            if mg.get("changed"):
                load_live_json.clear()
            live_now  = state.get("live", [])
            completed = sorted(state.get("all_completed", []),
                               key=lambda c: (c.get("date", ""), c["home"]), reverse=True)
            standings = build_standings(state.get("all_completed", []))
            src = f"{t('src_live')} · {datetime.now().strftime('%H:%M:%S')}"
            ok_live = True
        else:
            ld = load_live_json()
            live_now, ok_live = [], False
            completed = list(reversed(ld.get("completed_matches", [])))
            standings = ld.get("group_standings", {})
            src = t("src_snap")
        meta     = load_live_json()
        injuries = meta.get("key_injuries", {})
        _done_or_live = {(m["home"], m["away"]) for m in completed} | {(m["home"], m["away"]) for m in live_now}

        # ── helpers ──────────────────────────────────────────────────────────
        def _fmt_pct(p):
            v = p * 100
            return "<0.1%" if 0 < v < 0.1 else f"{v:.1f}%"

        def _predict_btn(h, a, key, label):
            if st.button(label, key=key, width="stretch"):   # fill the block → centered, consistent
                st.session_state["_goto"] = "🎯 Match Predictor"
                st.session_state["mp_prefill"] = (h, a)
                st.rerun()

        def _live_label(m, kdt=None):
            # friendly in-play status across providers (min'/half-time/extra time/penalties).
            # Prefer the provider's real minute/phase; if none, estimate from the official kick-off
            # time (marked ~) so a minute always shows.
            s = (m.get("status") or "").upper()
            mn = m.get("minute")
            if s in ("HT", "PAUSED", "PAUS", "PEN_LIVE_BREAK") or "HALF TIME" in s or s.startswith("HALF"):
                return t("ls_halftime")
            if s in ("P", "PEN", "PENALTIES", "PENALTY_SHOOTOUT"):
                return t("ls_penalties")
            if s in ("ET", "BT", "AET", "ETB") or "EXTRA" in s:
                return f"{t('ls_extratime')} {mn}'" if mn else t("ls_extratime")
            if mn:
                return f"{mn}'"
            if kdt is not None:                          # estimate from kick-off (no provider minute)
                el = int((_now - kdt).total_seconds() // 60)
                if 0 <= el <= 48:
                    return f"~{el}'"
                if 48 < el <= 63:
                    return t("ls_halftime")
                if 63 < el <= 125:
                    return f"~{el - 15}'"
            return t("ls_live_short")   # in-play but no minute/known phase → just "LIVE"

        _now = _dt2.now(_tz2.utc)
        def _kickoff_dt(m):
            # full schedule rows carry date='YYYY-MM-DD' + time='HH:MM UTC-6' (real kick-off) — exact.
            ds, ts = (m.get("date") or "").strip(), (m.get("time") or m.get("time_utc") or "").strip()
            mt = _re.match(r"(\d{1,2}):(\d{2})\s*UTC\s*([+-]\d{1,2})?", ts)
            if not ds or not mt:
                return None
            hh, mm, off = int(mt.group(1)), int(mt.group(2)), int(mt.group(3) or 0)
            try:
                return _dt2.strptime(ds, "%Y-%m-%d").replace(tzinfo=_tz2.utc, hour=hh, minute=mm) - _td2(hours=off)
            except Exception:
                return None

        def _cd_text(kdt):
            # returns the FULL kick-off line (so a passed kick-off reads "🔴 kicked off…", not
            # "kick-off in KICK-OFF").
            secs = int((kdt - _now).total_seconds())
            if secs <= 0:
                return f"🔴 {t('ls_kickoff_passed')}"
            d = (f"{secs // 86400}j {(secs % 86400) // 3600}h" if secs >= 86400
                 else f"{secs // 3600}h {(secs % 3600) // 60:02d}m")
            return f"⏱ {t('ls_kickoff_in')} {d}"

        # The forward schedule (all 104 fixtures, real kick-off times) is the reliable source for
        # "next matches" — independent of the live feed, so the countdown always shows.
        upc = []
        for m in _full_schedule():
            if m.get("status") == "FT" or (m.get("home"), m.get("away")) in _done_or_live:
                continue
            kdt = _kickoff_dt(m)
            if kdt is None or kdt < _now - _td2(minutes=10):   # >10min past kick-off & not live → gone (finished/handled by live feed)
                continue
            upc.append((kdt, m))
        upc.sort(key=lambda x: x[0])
        # kick-off time of every fixture (incl. live ones) → lets us estimate a live minute when
        # the provider doesn't send one.
        _sched_kick = {}
        for _sm in _full_schedule():
            _sk = _kickoff_dt(_sm)
            if _sk:
                _sched_kick[(_sm.get("home"), _sm.get("away"))] = _sk

        # ── COMPACT BANNER (the whole top folded into one strip) ──────────────
        _badge = (f"<span style='color:{RED};font-weight:700'>● {t('ls_live_now').upper()}</span>"
                  if ok_live else f"<span style='color:{MUTED};font-weight:700'>● SNAPSHOT</span>")
        _refresh = f" · auto-refresh {LIVE_REFRESH}s" if AUTO_LIVE else ""
        st.markdown(
            f"<div style='margin:-1.7rem -2.6rem 10px;padding:7px 2.6rem 8px;border-bottom:1px solid {BORDER};"
            f"background:linear-gradient(180deg,{BG2},{BG0})'>"
            f"<span style='color:{GOLD};font-size:10px;letter-spacing:1.4px;text-transform:uppercase'>{t('ls_eyebrow')}</span>"
            f"<span style='font-size:17px;font-weight:700;margin-left:9px'>{t('ls_title')}</span>"
            f"<span style='color:{MUTED};font-size:11px;margin-left:10px'>{t('ls_desc')}</span>"
            f"<div style='font-size:11px;margin-top:2px'><span style='color:{WHITE}'>{t('ls_takeaway', n=len(completed))}</span>"
            f"<span style='color:{MUTED}'> &nbsp;·&nbsp; {_badge} · {src}{_refresh}</span></div>"
            f"</div>", unsafe_allow_html=True)

        # ── 🔝 SPOTLIGHT (centered): live score(s) vs prediction + the two next kick-offs with
        #    live, ticking RED countdowns. One HTML/JS card so it ticks per second.
        # ── 🔝 SPOTLIGHT (broadcaster-style): each fixture is its OWN bordered block, with the
        #    "see prediction" button INSIDE it, right under its red countdown. Countdowns tick
        #    per-second via a 0-height JS component reaching the parent DOM (same trick as analytics).
        if live_now or upc[:2]:
            _sl, _sc_col, _sr = st.columns([1.25, 2.1, 1.25])
            with _sc_col:
                for m in live_now:
                    gh = m["home_goals"] if m.get("home_goals") is not None else 0
                    ga = m["away_goals"] if m.get("away_goals") is not None else 0
                    mn = _live_label(m, _sched_kick.get((m["home"], m["away"])))
                    r = _csc(m["home"], m["away"], gh, ga, not m.get("group"))
                    _extra = ""
                    if r:
                        pw = r["p_wdl"]
                        _extra = (f"<div style='font-size:11px;color:{MUTED};margin-top:3px'>{t('ls_live_vs')}: "
                                  f"<b style='color:{TEAL}'>{m['home']} {pw['home']*100:.0f}%</b> · "
                                  f"{pw['draw']*100:.0f}% · <b style='color:{TEAL}'>{m['away']} {pw['away']*100:.0f}%</b> · {r['top_scores'][0]['s']}</div>")
                    _scl = " · ".join(m.get("scorers", []) or [])
                    if _scl:
                        _extra = f"<div style='font-size:11px;color:{GOLD};margin-top:2px'>⚽ {_scl}</div>" + _extra
                    with st.container(border=True):
                        st.markdown(
                            f"<div style='text-align:center'>"
                            f"<div style='color:{RED};font-weight:700;font-size:11px'>● {t('ls_live_now').upper()} · {mn}</div>"
                            f"<div style='font-size:26px;font-weight:800;line-height:1.1'>{flag(m['home'],disp_df)} {m['home']} "
                            f"<span style='color:{RED}'>{gh}–{ga}</span> {m['away']} {flag(m['away'],disp_df)}</div>"
                            f"{_extra}</div>", unsafe_allow_html=True)
                        _predict_btn(m["home"], m["away"], f"livespot_{m['home']}_{m['away']}", t("ls_predict_fut"))
                # A kick-off that has already passed but isn't in the live feed yet must NOT show a
                # dead countdown — render it as kicked-off (live-pending). Started first, then future.
                _slots = [(k, m) for (k, m) in upc[:2] if k <= _now] + [(k, m) for (k, m) in upc if k > _now]
                _cd_js = ""
                _ci = 0
                for _pos, (kdt, m) in enumerate(_slots[:2]):
                    _big = (_pos == 0 and not live_now)
                    _aff = 26 if _big else 18
                    _csz = 18 if _big else 14
                    if kdt <= _now:                      # kicked off → 0–0 scoreboard until the feed syncs
                        _mid = f"<span style='color:{RED}'>0–0</span>"
                        _line = (f"<div style='color:{RED};font-size:{_csz}px;font-weight:800;margin-top:2px'>"
                                 f"🔴 {t('ls_kickoff_passed')}</div>")
                    else:                                # future → live ticking countdown
                        _mid = f"<span style='color:{MUTED};font-weight:500'>vs</span>"
                        _cid = f"wccd{_ci}"; _ci += 1
                        _line = (f"<div id='{_cid}' style='color:{RED};font-size:{_csz}px;font-weight:800;margin-top:2px'>"
                                 f"⏱ {t('ls_kickoff_in')} —</div>")
                        _cd_js += f"wcCountdown('{_cid}',{int(kdt.timestamp()*1000)});"
                    with st.container(border=True):
                        st.markdown(
                            f"<div style='text-align:center'>"
                            f"<div style='font-size:{_aff}px;font-weight:800;line-height:1.1'>{flag(m['home'],disp_df)} {m['home']} "
                            f"{_mid} {m['away']} {flag(m['away'],disp_df)}</div>"
                            f"{_line}</div>", unsafe_allow_html=True)
                        _predict_btn(m["home"], m["away"], f"spot_{_pos}", t("ls_predict_fut"))
                if _cd_js:
                    import json as _json
                    _kw, _lw = _json.dumps("⏱ " + t('ls_kickoff_in') + " "), _json.dumps("🔴 " + t('ls_live_short'))
                    _js = ("<script>function wcCountdown(id,target){function u(){"
                           "var el=window.parent.document.getElementById(id);if(!el)return;"
                           "var d=target-Date.now();if(d<=0){el.innerHTML=" + _lw + ";return;}"
                           "var dd=Math.floor(d/86400000),h=Math.floor((d%86400000)/3600000),"
                           "mm=Math.floor((d%3600000)/60000),s=Math.floor((d%60000)/1000);"
                           "el.innerHTML=" + _kw + "+((dd>0?dd+'j ':'')+(h<10?'0':'')+h+':'+(mm<10?'0':'')+mm+':'+(s<10?'0':'')+s);}"
                           "u();setInterval(u,1000);}" + _cd_js + "</script>")
                    _components.html(_js, height=0)

        # ── 3 COLUMNS: played | standings (center) | upcoming ─────────────────
        _cpast, _cstd, _cfut = st.columns([1.05, 1.25, 1.05], gap="medium")

        with _cstd:
            st.markdown(f"#### {t('ls_col_std')}")
            for grp in sorted(standings.keys()):
                grp_sorted = sorted(standings[grp], key=lambda x: (-x["points"], -x["gd"], -x["gf"]))
                _rows = ""
                for _rnk, row in enumerate(grp_sorted, 1):
                    _pc = TEAL if _rnk <= 2 else (GOLD if _rnk == 3 else MUTED)
                    _rows += (f'<tr style="border-bottom:1px solid {BORDER}">'
                              f'<td style="color:{MUTED};width:14px">{_rnk}</td>'
                              f'<td>{flag(row["team"],disp_df)} <b>{row["team"]}</b></td>'
                              f'<td style="text-align:center">{row["played"]}</td>'
                              f'<td style="text-align:center">{row["gd"]:+d}</td>'
                              f'<td style="text-align:center;color:{_pc};font-weight:700">{row["points"]}</td></tr>')
                st.markdown(
                    f'<div style="font-weight:700;font-size:12px;margin-top:9px;color:{GOLD}">Group {grp}</div>'
                    f'<table style="width:100%;font-size:11px;border-collapse:collapse">'
                    f'<thead><tr style="color:{MUTED}"><th></th><th>Team</th><th>P</th><th>GD</th>'
                    f'<th style="color:{TEAL}">Pts</th></tr></thead><tbody>{_rows}</tbody></table>',
                    unsafe_allow_html=True)
            if not standings:
                st.caption("—")

        with _cpast:
            st.markdown(f"#### {t('ls_col_past')}")
            _np = 0
            for _i, m in enumerate(completed):
                gh, ga = m.get("home_goals"), m.get("away_goals")
                if gh is None:
                    continue
                _np += 1
                r = _csc(m["home"], m["away"], gh, ga, not m.get("group"))
                _wc = TEAL if gh > ga else (RED if gh < ga else GOLD)
                _verdict = ""
                if r:
                    _mark = ("✅ " + t("ls_result_ok")) if r["outcome_ok"] else ("❌ " + t("ls_result_no"))
                    _verdict = (f"<div style='font-size:10px;color:{MUTED};margin-top:2px'>"
                                f"{t('ls_prematch')} {r['top_scores'][0]['s']} · {_mark} "
                                f"<span style='opacity:.65'>(P {_fmt_pct(r['p_actual'])}, {t('ls_rank')} {r['rank']})</span></div>")
                st.markdown(
                    f"<div style='border:1px solid {BORDER};border-radius:9px;padding:6px 9px;margin-bottom:5px'>"
                    f"<span style='font-size:9px;color:{MUTED}'>Grp {m.get('group','?')} · {m.get('date','')}</span><br>"
                    f"<span style='font-size:13px'>{flag(m['home'],disp_df)} <b>{m['home']}</b> "
                    f"<span style='color:{_wc};font-weight:700;font-size:15px'>{gh}–{ga}</span> "
                    f"<b>{m['away']}</b> {flag(m['away'],disp_df)}</span>{_verdict}</div>", unsafe_allow_html=True)
                _predict_btn(m["home"], m["away"], f"pp_{_i}", t("ls_predict_past"))
            if not _np:
                st.caption("—")

        with _cfut:
            st.markdown(f"#### {t('ls_col_fut')}")
            _show_all = st.session_state.get("_show_all_up", False)
            _list = upc if _show_all else upc[:6]
            def _fut_card(kdt, m, key):
                preds = _cpred(m["home"], m["away"], 2, not m.get("group"))
                _ps = " · ".join(f"{pp['s']} {pp['p']*100:.0f}%" for pp in preds)
                st.markdown(
                    f"<div style='border:1px solid {BORDER};border-radius:9px;padding:6px 9px;margin-bottom:5px'>"
                    f"<span style='font-size:9px;color:{MUTED}'>Grp {m.get('group','?')} · {m.get('date','')}</span><br>"
                    f"<span style='font-size:13px'>{flag(m['home'],disp_df)} <b>{m['home']}</b> "
                    f"<span style='color:{MUTED}'>vs</span> <b>{m['away']}</b> {flag(m['away'],disp_df)}</span>"
                    f"<div style='font-size:11px;color:{RED};font-weight:700;margin-top:2px'>{_cd_text(kdt)}</div>"
                    + (f"<div style='font-size:10px;color:{GOLD};margin-top:1px'>{t('ls_pred')}: {_ps}</div>" if _ps else "")
                    + "</div>", unsafe_allow_html=True)
                _predict_btn(m["home"], m["away"], key, t("ls_predict_fut"))
            for _i, (kdt, m) in enumerate(_list):
                _fut_card(kdt, m, f"fp_{_i}")
            if not upc:
                st.caption("—")
            elif len(upc) > 6:
                # "see all upcoming" lives HERE — at the bottom of the upcoming column.
                if st.button(("▲ " + t("ls_col_fut")) if _show_all else f"{t('ls_see_all')} (+{len(upc) - 6})",
                             key="show_all_up"):
                    st.session_state["_show_all_up"] = not _show_all
                    st.rerun()

        if any(inj_list for inj_list in injuries.values()):
            with st.expander(f"⚕️ {t('ls_injuries')}"):
                for code, inj_list in injuries.items():
                    for inj in (inj_list or []):
                        sev = RED if "OUT" in inj.upper() else GOLD
                        st.markdown(f"{flag(code,disp_df)} **{code}**: <span style='color:{sev}'>{inj}</span>",
                                    unsafe_allow_html=True)
    _live_standings()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MATCH PREDICTOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Match Predictor":
    page_header("mp_eyebrow", "mp_title", "mp_desc")

    all_codes = sorted(elo_df["team"].tolist()) if not elo_df.empty else []
    if not all_codes:
        st.error("No team data loaded.")
        st.stop()

    # Pre-fill from a "click a match → Predict" jump (Live Standings): set the selectbox
    # session-state keys BEFORE the widgets render.
    _pf = st.session_state.pop("mp_prefill", None)
    if _pf and _pf[0] in all_codes:
        st.session_state["mp_a"] = _pf[0]
    if _pf and _pf[1] in all_codes:
        st.session_state["mp_b"] = _pf[1]
    st.session_state.setdefault("mp_a", "ESP" if "ESP" in all_codes else all_codes[0])
    st.session_state.setdefault("mp_b", "ARG" if "ARG" in all_codes else all_codes[-1])

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        team_a = st.selectbox(
            "🏠 Team A", all_codes, key="mp_a",
            format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
        )
    with c2:
        st.markdown(f"<br><h2 style='text-align:center;color:{MUTED}'>vs</h2>", unsafe_allow_html=True)
    with c3:
        team_b = st.selectbox(
            "✈️ Team B", all_codes, key="mp_b",
            format_func=lambda x: f"{flag(x, disp_df)} {x} — {full_name(x, disp_df)}",
        )

    match_type = st.radio("Match context", ["Group Stage", "Knockout"], horizontal=True)

    # 🧬 DNA matchup — both squads' Nation-DNA radars overlaid (extract; full view one click away).
    def _dna_attrs(code):
        if "code" not in teams_df.columns:
            return None
        row = teams_df[teams_df["code"] == code]
        if not len(row):
            return None
        r = row.iloc[0]
        keys = [("Attack", "attack"), ("Defense", "defense"), ("Midfield", "midfield"),
                ("Goalkeeper", "goalkeeper"), ("Depth", "depth"), ("Penalties", "penalties"),
                ("Set Pieces", "setpiece"), ("Form", "form"), ("Health", "health"),
                ("Discipline", "discipline")]
        return {lbl: float(r.get(c, 75)) for lbl, c in keys}
    if team_a != team_b:
        _aa, _ab = _dna_attrs(team_a), _dna_attrs(team_b)
        if _aa and _ab:
            with st.expander("🧬 " + t("mp_dna"), expanded=True):
                _figd = go.Figure()
                _figd.add_trace(go.Scatterpolar(
                    r=list(_aa.values()) + [list(_aa.values())[0]],
                    theta=list(_aa.keys()) + [list(_aa.keys())[0]], fill="toself",
                    name=f"{flag(team_a, disp_df)} {team_a}", fillcolor="rgba(42,157,143,0.18)",
                    line=dict(color=TEAL, width=2)))
                _figd.add_trace(go.Scatterpolar(
                    r=list(_ab.values()) + [list(_ab.values())[0]],
                    theta=list(_ab.keys()) + [list(_ab.keys())[0]], fill="toself",
                    name=f"{flag(team_b, disp_df)} {team_b}", fillcolor="rgba(230,57,70,0.15)",
                    line=dict(color=RED, width=2)))
                _figd.update_layout(
                    **plotly_layout(height=420), showlegend=True,
                    polar=dict(bgcolor=BG2, radialaxis=dict(visible=True, range=[0, 100], gridcolor=BORDER),
                               angularaxis=dict(gridcolor=BORDER)))
                st.plotly_chart(_figd, width="stretch")
                _d1, _d2 = st.columns(2)
                if _d1.button(f"🧬 {t('mp_dna_full')} {team_a}", key="dna_full_a"):
                    st.session_state["_goto"] = "🧬 Nation DNA"; st.session_state["dna_sel"] = team_a; st.rerun()
                if _d2.button(f"🧬 {t('mp_dna_full')} {team_b}", key="dna_full_b"):
                    st.session_state["_goto"] = "🧬 Nation DNA"; st.session_state["dna_sel"] = team_b; st.rerun()
                st.caption(t("mp_dna_note"))

    is_ko = match_type == "Knockout"

    if team_a == team_b:
        st.warning(t("empty_same_team"))
    else:
        try:
            teams_obj, cfg, params, model = _predictor_model()   # cached: no rebuild per keystroke

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
            st.plotly_chart(fig_pie, width="stretch")
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
            st.plotly_chart(fig_heat, width="stretch")

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
                st.plotly_chart(fig_h2h, width="stretch")

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
    page_header("dna_eyebrow", "dna_title", "dna_desc")

    all_codes = sorted(elo_df["team"].tolist()) if not elo_df.empty else []
    if not all_codes:
        st.error("No data loaded."); st.stop()

    st.session_state.setdefault("dna_sel", all_codes[0])
    selected = st.selectbox(
        "Select nation",
        all_codes, key="dna_sel",
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
            st.warning(t("empty_no_prob"))
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
                st.plotly_chart(fig_st, width="stretch")

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
            st.info(t("empty_no_wc_hist"))
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
                st.caption(t("empty_no_pen"))

    with t3:
        team_form = form_df[form_df["code"] == selected].copy() if not form_df.empty else pd.DataFrame()
        if team_form.empty:
            st.info(t("empty_no_form"))
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
            st.plotly_chart(fig_form, width="stretch")

            disp_form = team_form[["date", "opponent", "gf", "ga", "result", "tournament"]].copy()
            disp_form.columns = ["Date", "Opponent", "GF", "GA", "Result", "Tournament"]
            st.dataframe(disp_form.sort_values("Date", ascending=False),
                         width="stretch", hide_index=True)

    with t4:
        if tm_row is None:
            st.info(t("empty_no_squad"))
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
            st.plotly_chart(fig_radar, width="stretch")
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
    page_header("h2h_eyebrow", "h2h_title", "h2h_desc")

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
            **plotly_layout(height=600, xaxis=dict(tickangle=-45, gridcolor=BORDER,
                                                   linecolor=BORDER, tickcolor=BORDER, zeroline=False)),
        )
        st.plotly_chart(fig_mat, width="stretch")
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
            st.info(t("empty_no_pair"))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — HISTORICAL RECORDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜 Historical Records":
    page_header("hist_eyebrow", "hist_title", "hist_desc")

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
        width="stretch", hide_index=True, height=400,
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
    st.plotly_chart(fig_tit, width="stretch")

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
        st.plotly_chart(fig_sc, width="stretch")
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
    page_header("br_eyebrow", "br_title", "br_desc")

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
        st.plotly_chart(fig_fun, width="stretch")

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
    page_header("ml_eyebrow", "ml_title", "ml_desc")
    takeaway(t("ml_takeaway"))
    st.caption(t("ml_hint"))

    t1, t2, t3, t4, t5 = st.tabs(
        ["📐 Mathematics", "📊 Ablation", "🔬 Calibration", "⚠️ Limitations", "📋 Maturity Score"])

    with t1:
        st.markdown("### Core Mathematics")
        st.latex(r"\log \mu_A = \log_{\text{base}} + \beta_{\text{elo}} \cdot \frac{\text{Elo}_A - \text{Elo}_B}{400}")
        st.latex(r"\log \mu_B = \log_{\text{base}} - \beta_{\text{elo}} \cdot \frac{\text{Elo}_A - \text{Elo}_B}{400}")
        st.latex(r"P(X=i, Y=j) = \tau_{ij} \cdot \frac{e^{-\mu_A} \mu_A^i}{i!} \cdot \frac{e^{-\mu_B} \mu_B^j}{j!}")
        st.latex(r"\tau(0,0) = 1 - \rho\mu_A\mu_B, \quad \tau(1,0) = 1 + \rho\mu_B, \quad "
                  r"\tau(0,1) = 1 + \rho\mu_A, \quad \tau(1,1) = 1 - \rho")

        st.markdown("**Parameters actually used by the model** "
                    "(fit on 10,555 international matches, 2010–2025; raw MLE then temperature-corrected ×0.55):")
        try:
            lpp = DATA / "elo_live_params.json"
            lp  = json.loads(lpp.read_text())
            beta_prod = float(lp["beta_elo"])        # value the model actually uses
            beta_raw  = beta_prod / 0.55              # raw MLE before the ×0.55 temperature correction
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("β_elo raw (MLE)", f"{beta_raw:.4f}",
                      help="Maximum-likelihood fit before the temperature correction.")
            c2.metric("β_elo production (used)", f"{beta_prod:.4f}",
                      help="raw × 0.55 — this is the β the model uses in every match.")
            c3.metric("log_base (used)", f"{lp['log_base']:.4f}")
            c4.metric("ρ Dixon-Coles (used)", f"{lp.get('rho', -0.021):.4f}")
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
            st.plotly_chart(fig2, width="stretch")

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
        ⚠️ <b>Caveat:</b> ECE = 0.017 measures match-outcome calibration on historical data.
        Tournament-level validation HAS now been run — a leak-free walk-forward backtest on
        WC2010/2014/2018/2022 (model retrained before each tournament). The ML weight was set to
        0.20 from that evidence. The remaining gap is <b>structural</b> uncertainty: the published
        champion intervals propagate β_elo sampling only (a floor), not model-form uncertainty.
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
             "Described correctly in outputs/audit/model_card_public.md but must not be conflated with MLE."),
            (GOLD, "WC historical backtest: honest scope",
             "WC2022: ARG #1 pick (19.3%), actual winner. WC2018: FRA #5 (5.6%), actual winner. "
             "Champion-level mean-Brier (~0.027) ≈ uniform 1/48 null; discrimination shows at "
             "group/round stages, not at the single winner (n=2 WCs). See Data Quality page."),
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

        # Prefer the latest maturity snapshot (v6); fall back to the original baseline.
        scores, g_avg, _mat_found = {}, 5.25, False
        for _cand in ["final_maturity_score_v6.json", "final_maturity_score_v5.json",
                      "global_maturity_score.json"]:
            _p = AUDIT / _cand
            if _p.exists():
                _d = json.loads(_p.read_text())
                scores = _d.get("scores_after") or _d.get("scores", {})
                g_avg  = float(_d.get("after", _d.get("global_average", 5.25)))
                _mat_found = True
                break
        if _mat_found:

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
            st.plotly_chart(fig_gauge, width="stretch")

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
            st.plotly_chart(fig_dim, width="stretch")

            st.markdown(f"""
**{g_avg:.2f}/10 → Serious, auditable lab. Not investment-grade forecasting.**

Strongest dimensions: Claims Honesty (9.5), Reproducibility & Documentation (9.0).

Resolved since the 5.25 baseline: tournament-level walk-forward backtest
(WC2010/14/18/22, ML retrained per cutoff); β_elo bootstrap CI → champion probability
intervals; ML 1X2 validated leak-free and wired into the simulation @ weight 0.20.

Remaining hard cap: structural uncertainty unquantified (intervals are a *floor*),
only 4 World Cups validated, market is benchmark-only, xG sources share an upstream.
""")
        else:
            st.info("Run outputs/audit/ scripts to generate the maturity score JSON.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📡 Data Quality":
    page_header("dq_eyebrow", "dq_title", "dq_desc")
    takeaway(t("dq_takeaway"))
    st.caption(t("dq_hint"))
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
                "- Fully reproducible offline; 574 tests."
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
                status_dot = "🟢"
                status_label = "ACTIVE"
            elif avail:
                status_dot = "🟡"
                status_label = "AVAILABLE (limited)"
            else:
                status_dot = "🔴"
                status_label = "UNAVAILABLE"

            # Plain markdown label — st.expander does not render raw HTML spans.
            with st.expander(
                f"{status_dot}  **{pname.replace('_',' ').title()}** — Quality {qlevel} — {status_label}",
                expanded=accessible,
            ):
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

**Current status: Quality A** — Highlightly BASIC provides team xG / advanced stats. **TheStatsAPI is active** (Stats API trial, key present locally; re-activated 2026-06-13 after an earlier revocation) for **finished-match** per-shot shotmap xG, bookmaker odds, lineups, timeline, player-stats and referee data — live in-progress stats are **not** on this plan, and its team-xG shares an upstream with Highlightly (not independent). API-Football FREE via date-bypass provides live scores/events/lineups/stats. football-data.org provides standings/scorers/fixtures. Current score disagreement check: zero disagreements across 4 providers.
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
        "Note (TSA)": ["", "", "", "", "ACTIVE (stats trial)", "", "", "", "", "", "", "", "", "ACTIVE"],
        "Impact on model": ["In-play probs", "Elo update", "HT signal",
                            "xG proxy (B)", "xG direct (A)", "Chance quality", "Assist xG",
                            "Domain stats", "Red card adj", "Injury proxy", "Context",
                            "Media", "Manual only", "Calibration"],
    }
    st.dataframe(pd.DataFrame(coverage_data), width="stretch", hide_index=True)

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
            st.dataframe(show, width="stretch", hide_index=True)

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
        st.dataframe(cmp, width="stretch", hide_index=True)
        st.caption(
            f"Gate: {mr['gate']['reason']} "
            "Honest scope: this panel validates the **single-match 1X2 model** on a leak-free temporal "
            "split (train ≤2018, test 2019–2022). That model **is** wired into the tournament Monte "
            "Carlo at weight **0.20** — it reweights the Dixon-Coles W/D/L marginals per match (group + "
            "knockout 90'); extra-time increments and the market layer are NOT reweighted, and it is NOT "
            "an xG-trained model. `model_stack_config.json` carries a rollback flag (set use_ml_match_model=false)."
        )

        # ML ensemble integration into the tournament sim
        ens_path = ROOT / "outputs" / "audit" / "ml_ensemble_integration_decision.json"
        if ens_path.exists():
            ens = json.loads(ens_path.read_text())
            integrated = ens.get("decision") == "INTEGRATED"
            badge = TEAL if integrated else GOLD
            st.markdown(
                f"<span style='color:{badge}'>**Tournament integration: {ens.get('decision')}**</span> "
                f"· the Dixon-Coles scoreline W/D/L marginals are reweighted toward the ML 1X2 model at "
                f"**production weight 0.20** (cut from the 0.50 match-gate weight by tournament walk-forward) "
                f"· rollback flag in config",
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
                st.dataframe(t, width="stretch", hide_index=True)
            st.caption(
                f"Max champion move {ens.get('max_champion_move_pp')}pp shown at the 0.50 evaluation "
                "weight (the integration A/B); the **production weight is 0.20**. "
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
            st.dataframe(agg.round(5), width="stretch", hide_index=True)
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
                st.dataframe(ms, width="stretch", hide_index=True)
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
        st.dataframe(pd.DataFrame(ivrows), width="stretch", hide_index=True)
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
            st.metric("Avg Champion Brier", f"{combined.get('avg_champion_brier', 0):.4f}")
        with cols[1]:
            st.metric("Uniform 1/48 null", f"{combined.get('uniform_null_champion_brier', 0.0204):.4f}",
                      help="Mean-Brier of predicting 1/48 for every team — the honest no-information baseline.")
        with cols[2]:
            ranks = combined.get("actual_champion_ranks", {})
            st.metric("Actual Champion Ranks", f"{list(ranks.values())}")

        st.markdown(f"""<div class="caveat-box">
        <b>How to read this:</b> Brier here is a mean over 48 teams, so the no-information baseline is the
        <b>uniform 1/48 null (~{combined.get('uniform_null_champion_brier', 0.0204):.4f})</b>, NOT a 0.50 coin-flip.
        At champion granularity the model is on par with that null — its discrimination shows at the
        group/round level (more positives per stage), not at pinpointing the single winner.
        <b>n = 2 tournaments</b>: a track record, not a skill guarantee.
        </div>""", unsafe_allow_html=True)

        for wc_key, wc_data in bt.get("tournaments", {}).items():
            with st.expander(f"**{wc_data['tournament']}**"):
                bs = wc_data["brier_scores"]
                st.markdown(f"""
| Stage | Brier Score |
|---|---|
| Group survival | {bs['group_survival']:.4f} |
| Semifinal | {bs['semifinal']:.4f} |
| Champion | {bs['champion']:.4f} |

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
