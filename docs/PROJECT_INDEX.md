# Project Index

Generated 2026-06-14T00:19:59 UTC · commit 8484b07 · branch main · git DIRTY

**WC2026 Probabilistic Forecast Lab** — local `~/FinderProjects/wc2026_june2026`
Public repo: https://github.com/Yorian-melki/wc2026-forecast-lab

## Run
```bash
PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.port 8512 --server.headless false
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q   # 571 passed
```

## Folder map

| Folder | Purpose |
|---|---|
| `src/wc2026/` | Model + providers + live_engine (AUTHORITATIVE code). |
| `tests/` | 571 pytest tests gating every claim. |
| `scripts/` | Pipeline/validation scripts (forecast, ML gate, walk-forward, beta intervals, live update). |
| `data/` | Inputs + frozen params + runtime live snapshot. data/live/ = provider extracts. |
| `outputs/audit/` | Audits & maturity. v6 maturity is current; global_maturity 5.25 is LEGACY. |
| `outputs/release/` | Public-release safety + manifests. |
| `outputs/deploy/` | Render + DNS + runbook deploy docs. |
| `outputs/launch/` | Launch ops notes (gitignored, local only). |
| `outputs/public/` | Portfolio case-study + chart assets. |
| `outputs/tournament_run/` | Simulation output CSVs (champion probs). |
| `outputs/models/` | Persisted ML model pkl (if gate passed). |
| `docs/` | THIS organization/handoff system. |
| `session_handoff/` | LEGACY old handoff notes — verify before trusting. |
| `ui/` | Misc UI assets (review). |

## Authoritative docs (trust these)

- `PROJECT_STATE.md`
- `docs/PROJECT_INDEX.md`
- `docs/DASHBOARD_PAGE_MAP.md`
- `docs/FILE_AUTHORITY_TABLE.md`
- `docs/LIVE_SYSTEM_TRUTH_AUDIT.md`
- `outputs/audit/model_card_public.md`

## Legacy — DO NOT trust as current

- outputs/audit/global_maturity_score.json (5.25 baseline)
- MODEL_CARD.md / MODEL_FREEZE.md (P4)
- session_handoff/
- *.bak / *_BACKUP_PRE_P0.csv

## Private / ignored (never commit)

- .env
- .env.backup*
- outputs/audit/*.json (masked fragments) except v5/v6 maturity
- outputs/launch/
- data/raw/provider_responses/