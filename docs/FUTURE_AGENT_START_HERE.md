# FUTURE AGENT — START HERE

You are an AI with **no chat history**. This folder is built so you can understand the real state
without it. Read in this order, then act.

## Read order (do not skip)
1. **`PROJECT_STATE.md`** (repo root) — single source of truth: what's live, done, broken, stale.
2. **`docs/PROJECT_INDEX.md`** — folder map, run commands, public repo.
3. **`docs/DASHBOARD_PAGE_MAP.md`** — every Streamlit page, line range, data, status.
4. **`docs/FILE_AUTHORITY_TABLE.md`** — which files are TRUTH vs legacy/backup. **Check this before trusting any output file.**
5. **`docs/DATA_FLOW_MAP.md`** — what produces/consumes each artifact.
6. **`docs/LIVE_SYSTEM_TRUTH_AUDIT.md`** — before touching live logic.

## Hard rules
- **Never** touch or print `.env` / `.env.backup*` / any API key. They are gitignored.
- **Never** trust `outputs/audit/global_maturity_score.json` (5.25) — it's the OLD baseline. Current maturity is `outputs/audit/final_maturity_score_v6.json` (6.93).
- **Never** rely on `MODEL_CARD.md` / `MODEL_FREEZE.md` (P4-era) — use `outputs/audit/model_card_public.md`. Treat `session_handoff/` and `*.bak` as legacy.
- **Before changing `app.py`:** run AppTest across **all 10 pages** (command below). The last regression was a crash on a page nobody tested.
- **Before saying "it works":** test every page, run `pytest`, and (if you changed live logic) re-check the QAT–SUI dedup.
- **Before touching live logic:** read `docs/LIVE_SYSTEM_TRUTH_AUDIT.md`.
- **Do not** claim `wc2026.yorian-melki.com` is live — Render + DNS are still pending.
- **Do not** change DNS. The `wc2026` CNAME is a user action at Spaceship after Render gives a target.

## Verify everything (copy-paste)
```bash
cd ~/FinderProjects/wc2026_june2026
PYTHONPATH=src .venv/bin/python -m py_compile app.py
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q          # expect 571 passed
# AppTest all pages:
PYTHONPATH=src .venv/bin/python - <<'PY'
from dotenv import load_dotenv; load_dotenv(".env")
from streamlit.testing.v1 import AppTest
pages=["🚀 Release Status","🏆 Champion Tracker","⚽ Live Standings","🎯 Match Predictor","🧬 Nation DNA","⚔️ Head-to-Head","📜 Historical Records","🔮 Bracket Paths","🧮 Model Lab","📡 Data Quality"]
for pg in pages:
    at=AppTest.from_file("app.py",default_timeout=120); at.run(); at.radio[0].set_value(pg).run()
    print(("OK " if not at.exception else "FAIL ")+pg, (at.exception[0] if at.exception else ""))
PY
# secret scan (must be empty):
grep -rInE 'fapi_[A-Za-z0-9]{25,}|[a-f0-9]{64}' --exclude-dir=.venv . | grep -iE 'key|token'
```

## Run / deploy
- Local app: `PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.port 8512 --server.headless false` → http://localhost:8512
- Tests: `docs/RUN_TESTS.md` · Live data: `docs/UPDATE_LIVE_DATA.md`
- Deploy app: `docs/DEPLOY_RENDER.md` · DNS: `docs/DNS_SPACESHIP.md` · Troubleshoot: `docs/TROUBLESHOOTING.md`

## The one-line truth
Local probabilistic WC2026 lab: Elo→Dixon-Coles + ML@0.20, live auto-updating standings (with key),
571 tests, maturity 6.93. Public repo + portfolio are live; the live app and its subdomain are not yet.
