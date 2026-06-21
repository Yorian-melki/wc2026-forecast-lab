#!/usr/bin/env python3
"""Securely set / rotate THESTATSAPI_KEY in .env (weekly trial rotation).

The key is read from a HIDDEN prompt (getpass) — never on the command line, never in shell
history, never echoed to the screen. It is written only to .env, which is gitignored, so it
can never be committed. After updating locally, ALSO set it in Render -> Environment for the
live site (this script cannot reach your Render dashboard).

Usage:
    python scripts/set_thestatsapi_key.py
    python scripts/set_thestatsapi_key.py --key VAR   # rotate a different VAR= key instead
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"


def main() -> int:
    var = "THESTATSAPI_KEY"
    if "--key" in sys.argv:
        var = sys.argv[sys.argv.index("--key") + 1]

    key = getpass.getpass(f"Paste new {var} (hidden, not echoed): ").strip()
    if not key:
        print("empty input — aborted, nothing changed")
        return 1

    lines = ENV.read_text().splitlines() if ENV.exists() else []
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{var}="):
            lines[i] = f"{var}={key}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{var}={key}")
    ENV.write_text("\n".join(lines) + "\n")

    action = "rotated" if replaced else "added"
    print(f"✓ {var} {action} in .env ({len(key)} chars, value not shown).")
    print("  Next: set the same value in Render → your service → Environment, "
          "then redeploy or let it pick up on next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
