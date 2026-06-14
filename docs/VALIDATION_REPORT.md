# Validation Report

Generated 2026-06-14T00:24:36 UTC

| Check | Result |
|---|---|
| py_compile app.py | OK |
| pytest tests/ -q | 571 passed |
| AppTest (all 10 pages) | ALL OK |
| secret scan | CLEAN |
| QAT-SUI duplicate | FIXED (render filter + upcoming_today pruned in merge_and_persist) |
| git status | clean after commit |

No failures. No unresolved warnings affecting correctness.
