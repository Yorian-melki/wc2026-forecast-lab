# Deployment Readiness Checklist

Status as of 2026-06-14. ☑ done · ☐ user action.

## Security (blocking)
- ☑ `.env` added to `.gitignore` (was NOT ignored — fixed this batch)
- ☑ `.env.example` template added (names only, no values)
- ☑ raw provider responses gitignored
- ☐ **User:** confirm no secret was ever committed (project is not yet a git repo — clean start possible)
- ☐ **User:** rotate any key that was shared in plaintext outside the machine

## Reproducibility
- ☑ One-command rebuild: `scripts/rebuild_publication_forecast.py` (smoke + `--full`)
- ☑ `requirements.txt` updated (scipy, scikit-learn, statsmodels, penaltyblog, dotenv, requests)
- ☑ Offline reproduction proven (no keys needed for forecast/validation)
- ☑ 558 tests passing

## Documentation
- ☑ Public model card (`outputs/audit/model_card_public.md`)
- ☑ Data lineage map · reviewer attack audit · artifact consistency audit
- ☑ README rewritten to current truth

## App architecture
- ☑ Streamlit app runs locally (`streamlit run app.py`)
- ☐ **User:** choose live-app host (recommended: Render at wc2026.yorian-melki.com)
- ☐ **User/Claude:** decide live vs static-snapshot demo (static = zero secrets)

## Domain
- ☑ DNS audited (apex + www already Vercel-wired)
- ☐ **User:** for wc2026 subdomain, add CNAME at Spaceship to the app host (Claude will NOT change DNS)

## Go / No-go
- **Portfolio + case study on Vercel:** GO (apex/www ready).
- **Live Streamlit app:** GO once a Python host is chosen and secrets set in host env.
- **Public live demo with keys:** only after the secret-never-committed confirmation above.
