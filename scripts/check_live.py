#!/usr/bin/env python3
"""Live-feed doctor — tells you, in ~10s, WHICH provider is actually returning live in-play WC
matches right now (and which keys are set), so the spotlight score isn't a guessing game.

    python scripts/check_live.py

Never prints key values. Run it where the keys are set (locally with your .env, or shell into
Render). If EVERY provider shows 0 live matches while a game is being played, the issue is the
keys/plan, not the app — set at least one working live key (FOOTBALL_DATA_ORG_KEY covers the WC
live on the free tier; THESTATSAPI_KEY also works if you keep it fresh).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def _row(m):
    return (f"{m.get('home','?')} {m.get('home_goals')}-{m.get('away_goals')} {m.get('away','?')}"
            f" · {m.get('status','')} {m.get('minute') or ''}".strip())


def main() -> int:
    print("── keys present (values hidden) ──")
    for k in ("API_FOOTBALL_KEY", "FOOTBALL_DATA_ORG_KEY", "THESTATSAPI_KEY",
              "HIGHLIGHTLY_API_KEY", "PRIMARY_LIVE_PROVIDER"):
        v = os.getenv(k)
        print(f"  {k:24s}: {'SET' if v else 'missing'}")

    from wc2026.providers.api_football import ApiFootballProvider
    from wc2026.providers.football_data_org import FootballDataOrgProvider
    from wc2026.providers.thestatsapi import TheStatsAPIProvider
    from wc2026.providers.highlightly import HighlightlyProvider
    from wc2026.providers.thesportsdb import TheSportsDBProvider
    from wc2026.providers.espn import EspnProvider

    provs = [("espn (official clock)", EspnProvider()), ("api_football", ApiFootballProvider()),
             ("football_data_org", FootballDataOrgProvider()), ("thestatsapi", TheStatsAPIProvider()),
             ("highlightly", HighlightlyProvider()), ("thesportsdb", TheSportsDBProvider())]

    print("\n── live in-play matches, per provider ──")
    any_live = False
    for name, p in provs:
        try:
            live = p.get_live_matches() or []
        except Exception as e:
            print(f"  {name:18s}: ERROR {type(e).__name__}: {str(e)[:70]}")
            continue
        print(f"  {name:18s}: {len(live)} live" + ("" if not live else "  →  " + " | ".join(_row(m) for m in live[:4])))
        any_live = any_live or bool(live)

    print("\n── what the router (and therefore the app) will use ──")
    try:
        from wc2026.providers.router import ProviderRouter
        rl = ProviderRouter().get_live_matches() or []
        print(f"  router.get_live_matches(): {len(rl)} live" +
              ("" if not rl else "  →  " + " | ".join(f"{m.home} {m.home_goals}-{m.away_goals} {m.away} ({m.status} {m.minute or ''})".strip() for m in rl[:4])))
    except Exception as e:
        print(f"  router ERROR: {type(e).__name__}: {str(e)[:80]}")

    print("\nVERDICT:", "✅ at least one provider reports live matches — the spotlight will show them."
          if any_live else "⚠️  no provider returned a live match. If a game is being played right now, "
          "set a working live key (FOOTBALL_DATA_ORG_KEY or THESTATSAPI_KEY) in the environment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
