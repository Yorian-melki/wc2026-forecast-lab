"""Pytest configuration.

Prevent any test (or an AppTest run under pytest) from mutating the committed runtime
snapshot data/wc2026_live.json. live_engine.merge_and_persist honors WC2026_DISABLE_PERSIST=1
by skipping ONLY the disk write — the merge/standings computation and return value are
unchanged, so live behavior on the real deploy (flag unset) is unaffected.
"""
import os

# setdefault so an explicit caller value still wins.
os.environ.setdefault("WC2026_DISABLE_PERSIST", "1")
