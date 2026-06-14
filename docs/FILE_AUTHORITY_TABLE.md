# File Authority Table

Generated 2026-06-14T00:19:03 UTC · which files are TRUTH vs legacy/backup.

| Path | Category | Rely? | Successor / note |
|---|---|---|---|
| `app.py` | AUTHORITATIVE_SOURCE | yes | Streamlit dashboard entrypoint |
| `src/wc2026/` | AUTHORITATIVE_SOURCE | yes | model + providers + live_engine |
| `src/wc2026/live_engine.py` | AUTHORITATIVE_SOURCE | yes | live fetch+merge+standings (failure-safe) |
| `tests/` | AUTHORITATIVE_SOURCE | yes | 571 tests gate the claims |
| `data/wc2026_live.json` | LIVE_RUNTIME_SNAPSHOT | yes — but app overwrites it | auto-updated by live_engine; completed+standings |
| `data/elo_calibrated_params.json` | AUTHORITATIVE_SOURCE | yes | frozen model params (beta_elo, team_elos) |
| `data/model_stack_config.json` | AUTHORITATIVE_SOURCE | yes | ML weight 0.20, rollback flag |
| `data/groups.json` | AUTHORITATIVE_SOURCE | yes | 48-team group map (team->group) |
| `data/teams.csv` | AUTHORITATIVE_SOURCE | yes | team Elo + attributes |
| `outputs/tournament_run/live_summary.csv` | AUTHORITATIVE_GENERATED | yes — **this is the displayed forecast** | calibrated Elo→DC + ML@0.20, live-conditioned; regenerate via `scripts/run_live_simulation.py` |
| `outputs/tournament_run/elo_calibrated_summary.csv` | AUTHORITATIVE_GENERATED | yes (fallback) | calibrated, pre-tournament (no live conditioning) |
| `outputs/tournament_run/summary.csv` · `summary.json` | LEGACY_REFERENCE | no — **EXPERT model, NOT displayed** | analyst-prior model; different favourite; feeds offline odds/value-detector demo only. See `outputs/tournament_run/ARTIFACTS.md` |
| `outputs/tournament_run/expert_summary.csv` | LEGACY_REFERENCE | no — expert model | identical to summary.csv; comparison baseline only |
| `outputs/audit/final_maturity_score_v6.json` | AUTHORITATIVE_GENERATED | yes | supersedes global_maturity_score.json |
| `outputs/audit/global_maturity_score.json` | LEGACY_REFERENCE | no — historical only | final_maturity_score_v6.json |
| `outputs/audit/*.md` | AUDIT_DOC | yes | curated audits (reviewer, lineage, model card) |
| `outputs/audit/thestatsapi_*` | PRIVATE_IGNORED | no | masked key fragments — gitignored |
| `outputs/release/` | RELEASE_DOC | yes | git safety, manifests, deploy decision |
| `outputs/deploy/` | DEPLOYMENT_DOC | yes | render/dns/runbook docs |
| `outputs/launch/` | DEPLOYMENT_DOC | yes (local) | launch ops notes — gitignored (local only) |
| `render.yaml` | DEPLOYMENT_DOC | yes | Render blueprint for live app |
| `.env.example` | DEPLOYMENT_DOC | yes | env var names only, no values |
| `.env / .env.backup*` | PRIVATE_IGNORED | no | SECRETS — never commit |
| `app.py.bak_before_dashboard_hotfix` | BACKUP_DO_NOT_USE | NO | app.py @ 8484b07+ |
| `data/teams.csv.bak, data/*_BACKUP_PRE_P0.csv` | BACKUP_DO_NOT_USE | no | data/teams.csv |
| `session_handoff/` | LEGACY_REFERENCE | no — verify first | old chat handoff notes — may be stale |
| `MODEL_CARD.md, MODEL_FREEZE.md` | LEGACY_REFERENCE | no — use outputs/audit/model_card_public.md | outputs/audit/model_card_public.md |
| `README.md` | AUTHORITATIVE_SOURCE | yes | public-facing, current (571 tests, ML@0.20) |

## Categories

- **AUTHORITATIVE_SOURCE** — hand-maintained truth (code, frozen params, configs).
- **AUTHORITATIVE_GENERATED** — current generated truth (v6 maturity).
- **LIVE_RUNTIME_SNAPSHOT** — auto-updated by the app at runtime (wc2026_live.json).
- **AUDIT/RELEASE/DEPLOYMENT_DOC** — curated docs, safe to rely on.
- **LEGACY_REFERENCE** — historical; do NOT rely on as current (global_maturity 5.25, MODEL_CARD.md, session_handoff/).
- **BACKUP_DO_NOT_USE** — backups; gitignored; never rely on.
- **PRIVATE_IGNORED** — secrets / masked fragments; never commit.