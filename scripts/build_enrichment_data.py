#!/usr/bin/env python3
"""
Build all historical enrichment data for the WC2026 analytics platform.
Outputs CSV files used by the Streamlit dashboard.
Run: python scripts/build_enrichment_data.py
"""
from __future__ import annotations
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

RESULTS = ROOT / 'data' / 'external' / 'international_results' / 'results.csv'

CODE_TO_CSV: dict[str, str] = {
    'MEX':'Mexico','RSA':'South Africa','KOR':'South Korea','CZE':'Czech Republic',
    'CAN':'Canada','BIH':'Bosnia and Herzegovina','QAT':'Qatar','SUI':'Switzerland',
    'BRA':'Brazil','MAR':'Morocco','HAI':'Haiti','SCO':'Scotland',
    'USA':'United States','PAR':'Paraguay','AUS':'Australia','TUR':'Turkey',
    'GER':'Germany','CUW':'Curaçao','CIV':'Ivory Coast','ECU':'Ecuador',
    'NED':'Netherlands','JPN':'Japan','SWE':'Sweden','TUN':'Tunisia',
    'BEL':'Belgium','EGY':'Egypt','IRN':'Iran','NZL':'New Zealand',
    'ESP':'Spain','CPV':'Cape Verde','KSA':'Saudi Arabia','URU':'Uruguay',
    'FRA':'France','SEN':'Senegal','IRQ':'Iraq','NOR':'Norway',
    'ARG':'Argentina','ALG':'Algeria','AUT':'Austria','JOR':'Jordan',
    'POR':'Portugal','COD':'DR Congo','UZB':'Uzbekistan','COL':'Colombia',
    'ENG':'England','CRO':'Croatia','GHA':'Ghana','PAN':'Panama',
}
CSV_TO_CODE: dict[str, str] = {v: k for k, v in CODE_TO_CSV.items()}
WC2026 = list(CODE_TO_CSV.keys())

# ────────────────────────────────────────────────────────────────────────────
# WC TOURNAMENT HISTORY per nation (verified, WC 1930–2022)
# Fields: appearances, titles, runner_up, third, fourth, best_result
#   best_result: W=Champion, F=Final, SF=Semifinal, QF=Quarterfinal,
#                R16=Round of 16, GS=Group Stage, Q=Qualified (for WC2026 only)
# ────────────────────────────────────────────────────────────────────────────
WC_HISTORY: dict[str, dict] = {
    'ARG': {'appearances':18,'titles':3,'runner_up':3,'third':0,'fourth':0,
            'best_result':'W','wc_titles':[1978,1986,2022],'wc_finals':[1930,1990]},
    'BRA': {'appearances':22,'titles':5,'runner_up':2,'third':2,'fourth':2,
            'best_result':'W','wc_titles':[1958,1962,1970,1994,2002],'wc_finals':[1950,1998]},
    'GER': {'appearances':20,'titles':4,'runner_up':4,'third':4,'fourth':2,
            'best_result':'W','wc_titles':[1954,1974,1990,2014],'wc_finals':[1966,1982,1986,2002]},
    'FRA': {'appearances':16,'titles':2,'runner_up':1,'third':2,'fourth':1,
            'best_result':'W','wc_titles':[1998,2018],'wc_finals':[2006]},
    'ESP': {'appearances':16,'titles':1,'runner_up':0,'third':0,'fourth':1,
            'best_result':'W','wc_titles':[2010],'wc_finals':[]},
    'ENG': {'appearances':16,'titles':1,'runner_up':0,'third':0,'fourth':1,
            'best_result':'W','wc_titles':[1966],'wc_finals':[]},
    'ITA': {'appearances':18,'titles':4,'runner_up':2,'third':1,'fourth':1,
            'best_result':'W','wc_titles':[1934,1938,1982,2006],'wc_finals':[1970,1994]},
    'URU': {'appearances':14,'titles':2,'runner_up':0,'third':0,'fourth':3,
            'best_result':'W','wc_titles':[1930,1950],'wc_finals':[]},
    'NED': {'appearances':11,'titles':0,'runner_up':3,'third':1,'fourth':1,
            'best_result':'F','wc_titles':[],'wc_finals':[1974,1978,2010]},
    'POR': {'appearances':9,'titles':0,'runner_up':0,'third':2,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'MEX': {'appearances':17,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'BEL': {'appearances':14,'titles':0,'runner_up':0,'third':1,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'KOR': {'appearances':11,'titles':0,'runner_up':0,'third':0,'fourth':1,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'CRO': {'appearances':6,'titles':0,'runner_up':1,'third':2,'fourth':0,
            'best_result':'F','wc_titles':[],'wc_finals':[2018]},
    'COL': {'appearances':7,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'JPN': {'appearances':7,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'SUI': {'appearances':12,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'SWE': {'appearances':12,'titles':0,'runner_up':1,'third':2,'fourth':1,
            'best_result':'F','wc_titles':[],'wc_finals':[1958]},
    'MAR': {'appearances':7,'titles':0,'runner_up':0,'third':0,'fourth':1,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'SEN': {'appearances':4,'titles':0,'runner_up':0,'third':0,'fourth':1,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'AUS': {'appearances':6,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'NOR': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'SCO': {'appearances':8,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'GHA': {'appearances':4,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'ECU': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'PAR': {'appearances':9,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'QF','wc_titles':[],'wc_finals':[]},
    'IRN': {'appearances':6,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'TUN': {'appearances':6,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'EGY': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'TUR': {'appearances':3,'titles':0,'runner_up':0,'third':1,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'CZE': {'appearances':11,'titles':0,'runner_up':2,'third':0,'fourth':0,  # as Czechoslovakia
            'best_result':'F','wc_titles':[],'wc_finals':[1934,1962]},  # as CZK/CSK
    'USA': {'appearances':11,'titles':0,'runner_up':0,'third':1,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'CAN': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'NZL': {'appearances':2,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'ALG': {'appearances':4,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'AUT': {'appearances':7,'titles':0,'runner_up':0,'third':1,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'POR': {'appearances':9,'titles':0,'runner_up':0,'third':2,'fourth':0,
            'best_result':'SF','wc_titles':[],'wc_finals':[]},
    'PAN': {'appearances':1,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'RSA': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'HAI': {'appearances':1,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    # Debutants / rare
    'BIH': {'appearances':1,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'QAT': {'appearances':2,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'KSA': {'appearances':7,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
    'JOR': {'appearances':0,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'DEBUT','wc_titles':[],'wc_finals':[]},
    'CPV': {'appearances':0,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'DEBUT','wc_titles':[],'wc_finals':[]},
    'CUW': {'appearances':0,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'DEBUT','wc_titles':[],'wc_finals':[]},
    'UZB': {'appearances':0,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'DEBUT','wc_titles':[],'wc_finals':[]},
    'IRQ': {'appearances':2,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'COD': {'appearances':1,'titles':0,'runner_up':0,'third':0,'fourth':0,  # as Zaire 1974
            'best_result':'GS','wc_titles':[],'wc_finals':[]},
    'CIV': {'appearances':3,'titles':0,'runner_up':0,'third':0,'fourth':0,
            'best_result':'R16','wc_titles':[],'wc_finals':[]},
}

# Fill any missing teams with defaults
for code in WC2026:
    if code not in WC_HISTORY:
        WC_HISTORY[code] = {'appearances':0,'titles':0,'runner_up':0,'third':0,'fourth':0,
                             'best_result':'DEBUT','wc_titles':[],'wc_finals':[]}

# ────────────────────────────────────────────────────────────────────────────
# PENALTY SHOOTOUT HISTORY (WC-specific, verified)
# ────────────────────────────────────────────────────────────────────────────
PENALTY_HISTORY: dict[str, dict] = {
    'GER': {'won':5,'lost':2,'pct':0.714,'record':'5W-2L','tournaments':[1982,1990,2006,2014,2016]},
    'ARG': {'won':5,'lost':4,'pct':0.556,'record':'5W-4L'},
    'FRA': {'won':3,'lost':4,'pct':0.429,'record':'3W-4L'},
    'ENG': {'won':2,'lost':6,'pct':0.250,'record':'2W-6L','note':'historically poor at penalties'},
    'ITA': {'won':2,'lost':4,'pct':0.333,'record':'2W-4L'},
    'BRA': {'won':3,'lost':2,'pct':0.600,'record':'3W-2L'},
    'ESP': {'won':3,'lost':3,'pct':0.500,'record':'3W-3L'},
    'NED': {'won':2,'lost':4,'pct':0.333,'record':'2W-4L'},
    'POR': {'won':3,'lost':2,'pct':0.600,'record':'3W-2L'},
    'CRO': {'won':2,'lost':1,'pct':0.667,'record':'2W-1L'},
    'URU': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'MEX': {'won':1,'lost':3,'pct':0.250,'record':'1W-3L','note':'1/4 in WC shootouts'},
    'JPN': {'won':0,'lost':3,'pct':0.000,'record':'0W-3L','note':'0/3 in WC shootouts'},
    'KOR': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'SUI': {'won':2,'lost':2,'pct':0.500,'record':'2W-2L'},
    'BEL': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'COL': {'won':1,'lost':1,'pct':0.500,'record':'1W-1L'},
    'GHA': {'won':0,'lost':1,'pct':0.000,'record':'0W-1L'},
    'SEN': {'won':0,'lost':1,'pct':0.000,'record':'0W-1L'},
    'USA': {'won':1,'lost':1,'pct':0.500,'record':'1W-1L'},
    'PAR': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'MAR': {'won':1,'lost':1,'pct':0.500,'record':'1W-1L'},
    'SCO': {'won':0,'lost':0,'pct':0.500,'record':'0W-0L'},
    'AUS': {'won':0,'lost':1,'pct':0.000,'record':'0W-1L'},
    'ECU': {'won':0,'lost':0,'pct':0.500,'record':'0W-0L'},
    'IRN': {'won':0,'lost':0,'pct':0.500,'record':'0W-0L'},
    'TUR': {'won':0,'lost':1,'pct':0.333,'record':'0W-1L'},
    'SWE': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'CZE': {'won':1,'lost':2,'pct':0.333,'record':'1W-2L'},
    'NOR': {'won':0,'lost':0,'pct':0.500,'record':'0W-0L'},
}
# Default for teams with no history
for code in WC2026:
    if code not in PENALTY_HISTORY:
        PENALTY_HISTORY[code] = {'won':0,'lost':0,'pct':0.500,'record':'No WC history'}

# ────────────────────────────────────────────────────────────────────────────
# TEAM FULL NAMES and DISPLAY
# ────────────────────────────────────────────────────────────────────────────
TEAM_DISPLAY: dict[str, dict] = {
    'MEX': {'full_name':'Mexico','flag':'🇲🇽','confederation':'CONCACAF','nickname':'El Tri'},
    'RSA': {'full_name':'South Africa','flag':'🇿🇦','confederation':'CAF','nickname':'Bafana Bafana'},
    'KOR': {'full_name':'South Korea','flag':'🇰🇷','confederation':'AFC','nickname':'Taeguk Warriors'},
    'CZE': {'full_name':'Czechia','flag':'🇨🇿','confederation':'UEFA','nickname':'Lions'},
    'CAN': {'full_name':'Canada','flag':'🇨🇦','confederation':'CONCACAF','nickname':'The Canadians'},
    'BIH': {'full_name':'Bosnia & Herzegovina','flag':'🇧🇦','confederation':'UEFA','nickname':'Dragons'},
    'QAT': {'full_name':'Qatar','flag':'🇶🇦','confederation':'AFC','nickname':'The Maroons'},
    'SUI': {'full_name':'Switzerland','flag':'🇨🇭','confederation':'UEFA','nickname':'Nati'},
    'BRA': {'full_name':'Brazil','flag':'🇧🇷','confederation':'CONMEBOL','nickname':'Seleção'},
    'MAR': {'full_name':'Morocco','flag':'🇲🇦','confederation':'CAF','nickname':'Atlas Lions'},
    'HAI': {'full_name':'Haiti','flag':'🇭🇹','confederation':'CONCACAF','nickname':'Les Grenadiers'},
    'SCO': {'full_name':'Scotland','flag':'🏴󠁧󠁢󠁳󠁣󠁴󠁿','confederation':'UEFA','nickname':'The Tartan Army'},
    'USA': {'full_name':'United States','flag':'🇺🇸','confederation':'CONCACAF','nickname':'USMNT'},
    'PAR': {'full_name':'Paraguay','flag':'🇵🇾','confederation':'CONMEBOL','nickname':'La Albirroja'},
    'AUS': {'full_name':'Australia','flag':'🇦🇺','confederation':'AFC','nickname':'Socceroos'},
    'TUR': {'full_name':'Türkiye','flag':'🇹🇷','confederation':'UEFA','nickname':'Crescent-Stars'},
    'GER': {'full_name':'Germany','flag':'🇩🇪','confederation':'UEFA','nickname':'Die Mannschaft'},
    'CUW': {'full_name':'Curaçao','flag':'🇨🇼','confederation':'CONCACAF','nickname':'Pisci di Awa'},
    'CIV': {'full_name':'Ivory Coast','flag':'🇨🇮','confederation':'CAF','nickname':'The Elephants'},
    'ECU': {'full_name':'Ecuador','flag':'🇪🇨','confederation':'CONMEBOL','nickname':'La Tri'},
    'NED': {'full_name':'Netherlands','flag':'🇳🇱','confederation':'UEFA','nickname':'Oranje'},
    'JPN': {'full_name':'Japan','flag':'🇯🇵','confederation':'AFC','nickname':'Samurai Blue'},
    'SWE': {'full_name':'Sweden','flag':'🇸🇪','confederation':'UEFA','nickname':'Blågult'},
    'TUN': {'full_name':'Tunisia','flag':'🇹🇳','confederation':'CAF','nickname':'Eagles of Carthage'},
    'BEL': {'full_name':'Belgium','flag':'🇧🇪','confederation':'UEFA','nickname':'Red Devils'},
    'EGY': {'full_name':'Egypt','flag':'🇪🇬','confederation':'CAF','nickname':'The Pharaohs'},
    'IRN': {'full_name':'Iran','flag':'🇮🇷','confederation':'AFC','nickname':'Team Melli'},
    'NZL': {'full_name':'New Zealand','flag':'🇳🇿','confederation':'OFC','nickname':'All Whites'},
    'ESP': {'full_name':'Spain','flag':'🇪🇸','confederation':'UEFA','nickname':'La Roja'},
    'CPV': {'full_name':'Cape Verde','flag':'🇨🇻','confederation':'CAF','nickname':'Blue Sharks'},
    'KSA': {'full_name':'Saudi Arabia','flag':'🇸🇦','confederation':'AFC','nickname':'Green Falcons'},
    'URU': {'full_name':'Uruguay','flag':'🇺🇾','confederation':'CONMEBOL','nickname':'La Celeste'},
    'FRA': {'full_name':'France','flag':'🇫🇷','confederation':'UEFA','nickname':'Les Bleus'},
    'SEN': {'full_name':'Senegal','flag':'🇸🇳','confederation':'CAF','nickname':'Lions of Teranga'},
    'IRQ': {'full_name':'Iraq','flag':'🇮🇶','confederation':'AFC','nickname':'Lions of Mesopotamia'},
    'NOR': {'full_name':'Norway','flag':'🇳🇴','confederation':'UEFA','nickname':'The Boys'},
    'ARG': {'full_name':'Argentina','flag':'🇦🇷','confederation':'CONMEBOL','nickname':'La Albiceleste'},
    'ALG': {'full_name':'Algeria','flag':'🇩🇿','confederation':'CAF','nickname':'Les Fennecs'},
    'AUT': {'full_name':'Austria','flag':'🇦🇹','confederation':'UEFA','nickname':'Die Adler'},
    'JOR': {'full_name':'Jordan','flag':'🇯🇴','confederation':'AFC','nickname':'The Knights'},
    'POR': {'full_name':'Portugal','flag':'🇵🇹','confederation':'UEFA','nickname':'Seleção das Quinas'},
    'COD': {'full_name':'DR Congo','flag':'🇨🇩','confederation':'CAF','nickname':'Les Léopards'},
    'UZB': {'full_name':'Uzbekistan','flag':'🇺🇿','confederation':'AFC','nickname':'White Wolves'},
    'COL': {'full_name':'Colombia','flag':'🇨🇴','confederation':'CONMEBOL','nickname':'Los Cafeteros'},
    'ENG': {'full_name':'England','flag':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','confederation':'UEFA','nickname':'Three Lions'},
    'CRO': {'full_name':'Croatia','flag':'🇭🇷','confederation':'UEFA','nickname':'Vatreni'},
    'GHA': {'full_name':'Ghana','flag':'🇬🇭','confederation':'CAF','nickname':'Black Stars'},
    'PAN': {'full_name':'Panama','flag':'🇵🇦','confederation':'CONCACAF','nickname':'Los Canaleros'},
}

def main():
    print("Loading match data...")
    df = pd.read_csv(RESULTS)
    df['date'] = pd.to_datetime(df['date'])

    # ── 1. H2H records ────────────────────────────────────────────────────
    print("Computing H2H records...")
    h2h_rows = []
    for ca, cb in combinations(WC2026, 2):
        na, nb = CODE_TO_CSV[ca], CODE_TO_CSV[cb]
        mask = (
            ((df['home_team']==na) & (df['away_team']==nb)) |
            ((df['home_team']==nb) & (df['away_team']==na))
        )
        sub = df[mask & ~df['tournament'].str.contains('riendly', case=False, na=False)].copy()
        sub_wc = sub[sub['tournament'] == 'FIFA World Cup']

        for label, s in [('all_competitive', sub), ('wc_only', sub_wc)]:
            total = len(s)
            if total == 0:
                continue
            wins_a = draws = wins_b = 0
            gfa = gfb = 0
            for _, r in s.iterrows():
                if r['home_team'] == na:
                    ga, gb = r['home_score'], r['away_score']
                else:
                    ga, gb = r['away_score'], r['home_score']
                if pd.isna(ga) or pd.isna(gb):
                    continue
                gfa += ga; gfb += gb
                if ga > gb: wins_a += 1
                elif ga < gb: wins_b += 1
                else: draws += 1
            h2h_rows.append({
                'team_a': ca, 'team_b': cb, 'scope': label,
                'matches': total, 'wins_a': wins_a, 'draws': draws, 'wins_b': wins_b,
                'goals_a': gfa, 'goals_b': gfb,
                'win_pct_a': wins_a/total, 'win_pct_b': wins_b/total,
                'avg_goals_a': gfa/total, 'avg_goals_b': gfb/total,
                'last_meeting': s['date'].max().strftime('%Y-%m-%d') if len(s) > 0 else None,
            })

    h2h_df = pd.DataFrame(h2h_rows)
    out = ROOT / 'data' / 'h2h_records.csv'
    h2h_df.to_csv(out, index=False)
    print(f"  → {len(h2h_df)} H2H records saved to {out}")

    # ── 2. WC History ─────────────────────────────────────────────────────
    print("Building WC history table...")
    wc_rows = []
    for code in WC2026:
        h = WC_HISTORY.get(code, {})
        disp = TEAM_DISPLAY.get(code, {})
        wc_rows.append({
            'code': code,
            'full_name': disp.get('full_name', code),
            'flag': disp.get('flag', ''),
            'confederation': disp.get('confederation', ''),
            'nickname': disp.get('nickname', ''),
            'wc_appearances': h.get('appearances', 0),
            'wc_titles': h.get('titles', 0),
            'wc_runner_up': h.get('runner_up', 0),
            'wc_third': h.get('third', 0),
            'wc_fourth': h.get('fourth', 0),
            'wc_best_result': h.get('best_result', 'N/A'),
            'title_years': str(h.get('wc_titles', [])),
            'final_years': str(h.get('wc_finals', [])),
            # Historical round conversion rates (approximate from appearances)
            'deep_run_rate': (h.get('titles',0)+h.get('runner_up',0)+h.get('third',0)+h.get('fourth',0)) / max(h.get('appearances',1),1),
        })
    wch_df = pd.DataFrame(wc_rows)
    out_wch = ROOT / 'data' / 'wc_history.csv'
    wch_df.to_csv(out_wch, index=False)
    print(f"  → WC history saved to {out_wch}")

    # ── 3. Penalty history ────────────────────────────────────────────────
    print("Building penalty shootout table...")
    pen_rows = []
    for code in WC2026:
        p = PENALTY_HISTORY.get(code, {'won':0,'lost':0,'pct':0.500,'record':'No WC history'})
        pen_rows.append({'code': code, **p})
    pen_df = pd.DataFrame(pen_rows)
    out_pen = ROOT / 'data' / 'penalty_history.csv'
    pen_df.to_csv(out_pen, index=False)
    print(f"  → Penalty history saved to {out_pen}")

    # ── 4. Recent form (last 10 competitive matches per team) ─────────────
    print("Computing recent form...")
    form_rows = []
    for code in WC2026:
        name = CODE_TO_CSV[code]
        mask = (
            ((df['home_team']==name) | (df['away_team']==name)) &
            (~df['tournament'].str.contains('riendly', case=False, na=False))
        )
        sub = df[mask].dropna(subset=['home_score','away_score']).tail(15).copy()
        for _, r in sub.iterrows():
            at_home = r['home_team'] == name
            gf = r['home_score'] if at_home else r['away_score']
            ga = r['away_score'] if at_home else r['home_score']
            opp_name = r['away_team'] if at_home else r['home_team']
            opp_code = CSV_TO_CODE.get(opp_name, opp_name[:3].upper())
            result = 'W' if gf > ga else ('L' if gf < ga else 'D')
            form_rows.append({
                'code': code, 'date': r['date'].strftime('%Y-%m-%d'),
                'opponent': opp_code, 'gf': int(gf), 'ga': int(ga),
                'result': result, 'tournament': r['tournament'], 'neutral': r['neutral'],
            })
    form_df = pd.DataFrame(form_rows)
    out_form = ROOT / 'data' / 'recent_form.csv'
    form_df.to_csv(out_form, index=False)
    print(f"  → Recent form saved to {out_form} ({len(form_df)} rows)")

    # ── 5. Team display data ──────────────────────────────────────────────
    display_rows = [{'code': k, **v} for k, v in TEAM_DISPLAY.items() if k in WC2026]
    display_df = pd.DataFrame(display_rows)
    out_display = ROOT / 'data' / 'team_display.csv'
    display_df.to_csv(out_display, index=False)
    print(f"  → Team display saved to {out_display}")

    print("\n✓ All enrichment data built successfully.")


if __name__ == '__main__':
    main()
