"""
Wave 2 — Odds report: market comparison + value bets + Kelly sizing.

Usage:
    python3 scripts/odds_report.py                     # demo mode (no API key needed)
    python3 scripts/odds_report.py --live              # requires ODDS_API_KEY env var
    python3 scripts/odds_report.py --method power      # use power margin removal
    python3 scripts/odds_report.py --champion-only     # skip match-level analysis
    python3 scripts/odds_report.py --min-edge 3.0      # 3pp minimum edge threshold
    python3 scripts/odds_report.py --out report.csv    # save to CSV

Output:
    - Champion outright value table (model vs market, edge, Kelly fraction)
    - Match H2H value table
    - Diversified Kelly stakes (max 20% total exposure)
    - Overround diagnostics per bookmaker
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def print_section(title: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def main() -> None:
    parser = argparse.ArgumentParser(description="WC2026 Odds Report — Wave 2")
    parser.add_argument("--live", action="store_true",
                        help="Fetch live odds from The Odds API (requires ODDS_API_KEY)")
    parser.add_argument("--method", default="shin",
                        choices=["basic", "power", "shin"],
                        help="Margin removal method (default: shin)")
    parser.add_argument("--champion-only", action="store_true",
                        help="Skip match H2H analysis (faster)")
    parser.add_argument("--min-edge", type=float, default=2.0,
                        help="Minimum edge %% to flag value bet (default: 2.0)")
    parser.add_argument("--max-exposure", type=float, default=0.20,
                        help="Max total bankroll exposure across all bets (default: 0.20)")
    parser.add_argument("--match-sims", type=int, default=5000,
                        help="Iterations per match simulation (default: 5000)")
    parser.add_argument("--out", type=str, default=None,
                        help="Save champion value table to CSV path")
    args = parser.parse_args()

    import os
    if args.live and not os.environ.get("ODDS_API_KEY"):
        print("ERROR: --live requires ODDS_API_KEY environment variable.")
        print("Get a free key at: https://the-odds-api.com")
        sys.exit(1)

    from wc2026.odds.fetcher import fetch_outright_odds, fetch_match_odds
    from wc2026.odds.margin_removal import implied_overround
    from wc2026.odds.value_detector import analyze_champion_market, analyze_match_market
    from wc2026.odds.kelly import diversified_kelly

    mode = "LIVE" if args.live else "DEMO (synthetic odds from model)"
    print(f"\nWC 2026 ODDS REPORT")
    print(f"Mode:   {mode}")
    print(f"Method: {args.method.upper()} margin removal")
    print(f"Date:   {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")

    # ---- OUTRIGHT ODDS ----
    print_section("1. CHAMPION OUTRIGHT — MARKET OVERVIEW")
    t0 = time.time()
    outright = fetch_outright_odds()
    print(f"Bookmakers: {sorted(set(bk for bks in outright.teams.values() for bk in bks))}")
    covered = len(outright.covered_teams())
    print(f"Teams with odds: {covered}/48")

    # Overround diagnostics: full 48-team market
    import pandas as pd
    df = pd.read_csv(ROOT / "outputs" / "tournament_run" / "summary.csv")
    all_odds = [outright.consensus_odds(t) for t in df["team"] if outright.consensus_odds(t) > 1]
    if all_odds:
        K = implied_overround(all_odds)
        print(f"Full market overround: K={K:.4f} ({(K-1)*100:.1f}% margin)")

    # ---- CHAMPION VALUE TABLE ----
    print_section("2. CHAMPION VALUE ANALYSIS")
    # For outright (48 outcomes), force power method; shin is for H2H only
    outright_method = "power" if args.method == "shin" else args.method
    stakes = analyze_champion_market(
        outright, method=outright_method, min_edge_pct=args.min_edge
    )

    n_value = sum(1 for s in stakes if s.is_value_bet)
    print(f"\nAll teams with market coverage ({len(stakes)} total, {n_value} VALUE):\n")
    print(f"{'Team':<8} {'Model%':>7} {'Mkt%':>7} {'Edge':>7} {'Odds':>7} "
          f"{'qKelly':>8} {'EV%':>7} {'Flag':>6}")
    print("-" * 65)
    for s in stakes[:20]:
        flag = "★ VALUE" if s.is_value_bet else "      "
        print(
            f"{s.team_or_outcome:<8} "
            f"{s.model_prob*100:>6.2f}%  "
            f"{s.market_fair_prob*100:>6.2f}%  "
            f"{s.edge*100:>+6.2f}pp "
            f"{s.decimal_odds:>7.2f}  "
            f"{s.quarter_kelly*100:>6.3f}%  "
            f"{s.expected_value*100:>+6.2f}%  "
            f"{flag}"
        )
    if len(stakes) > 20:
        print(f"  ... {len(stakes)-20} more teams not shown ...")

    # ---- DIVERSIFIED KELLY ----
    div = diversified_kelly(stakes, max_total_exposure=args.max_exposure)
    if div:
        total_exp = sum(div.values())
        print(f"\nDiversified Kelly stakes (max {args.max_exposure*100:.0f}% total exposure):")
        for team, frac in sorted(div.items(), key=lambda x: -x[1]):
            print(f"  {team}: {frac*100:.3f}% of bankroll")
        print(f"  Total: {total_exp*100:.3f}%")
    else:
        print(f"\nNo value bets found at {args.min_edge:.1f}pp minimum edge.")

    # ---- SAVE TO CSV ----
    if args.out:
        rows = [
            {
                "team": s.team_or_outcome,
                "model_prob": round(s.model_prob, 5),
                "market_fair_prob": round(s.market_fair_prob, 5),
                "decimal_odds": s.decimal_odds,
                "edge_pp": round(s.edge * 100, 3),
                "full_kelly_pct": round(s.full_kelly * 100, 4),
                "quarter_kelly_pct": round(s.quarter_kelly * 100, 4),
                "expected_value_pct": round(s.expected_value * 100, 3),
                "is_value_bet": s.is_value_bet,
                "diversified_stake_pct": round(div.get(s.team_or_outcome, 0) * 100, 4),
            }
            for s in stakes
        ]
        import pandas as pd
        pd.DataFrame(rows).to_csv(args.out, index=False)
        print(f"\nSaved champion analysis → {args.out}")

    # ---- MATCH H2H ----
    if not args.champion_only:
        print_section("3. GROUP MATCH H2H VALUE ANALYSIS")
        print(f"Simulating {args.match_sims:,} matches per fixture...")
        match_bets = analyze_match_market(
            fetch_match_odds(),
            method=args.method,
            min_edge_pct=args.min_edge + 0.5,
            simulation_iters=args.match_sims,
        )
        value_matches = [b for b in match_bets if b.is_value_bet]
        print(f"\nValue bets in group matches: {len(value_matches)}\n")
        if value_matches:
            print(f"{'Fixture':<16} {'Out':>5} {'Odds':>7} {'Mdl%':>6} "
                  f"{'Mkt%':>6} {'Edge':>6} {'qKell':>7}")
            print("-" * 65)
            for b in value_matches[:15]:
                print(
                    f"{b.home_code}v{b.away_code:<10} "
                    f"{b.outcome:>5} "
                    f"{b.decimal_odds:>7.2f} "
                    f"{b.model_prob*100:>5.1f}% "
                    f"{b.market_fair_prob*100:>5.1f}% "
                    f"{b.edge*100:>+5.1f}pp "
                    f"{b.quarter_kelly*100:>6.3f}%"
                )
        else:
            print("No H2H value bets above threshold.")

    print(f"\n[odds_report] Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
