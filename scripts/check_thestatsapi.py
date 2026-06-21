#!/usr/bin/env python3
"""Weekly TheStatsAPI health check — run it after rotating the key.

In ~5 seconds it tells you whether the current THESTATSAPI_KEY (in .env) is ALIVE and what
it unlocks (odds / xG), so the free-trial key never dies silently on the live site. It reads
.env and NEVER prints the key. Exit code 0 = alive, 1 = dead (rotate it).

    python scripts/check_thestatsapi.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


def main() -> int:
    try:
        from wc2026.providers.thestatsapi import TheStatsAPIProvider
        p = TheStatsAPIProvider()
        st = p.get_status()
        if not getattr(st, "available", False):
            print("❌ TheStatsAPI DEAD — rotate the key:")
            print("   1) python scripts/set_thestatsapi_key.py")
            print("   2) update THESTATSAPI_KEY in Render → Environment (live site)")
            print("   reason:", (getattr(st, "error", "") or "no access")[:80])
            return 1
        ms = p.get_all_finished_matches()
        mid = ms[0].get("id") if ms else None
        odds = bool(p.get_odds(mid)) if mid else False
        xg = bool(p.get_shotmap(mid)) if mid else False
        print(f"✅ TheStatsAPI ALIVE · matches={len(ms)} · odds={'yes' if odds else 'no'} · xG={'yes' if xg else 'no'}")
        print("   Reminder: set the SAME key in Render → Environment → THESTATSAPI_KEY for the live site.")
        return 0
    except Exception as e:
        print("❌ TheStatsAPI check failed:", str(e)[:100])
        print("   Rotate the key and try again (python scripts/set_thestatsapi_key.py).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
