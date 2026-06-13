# Public File Manifest — safe to push

## Source & tests
- `src/**`
- `tests/**`
- `scripts/**`
- `app.py`
## Project meta
- `README.md`
- `requirements.txt`
- `pyproject.toml`
- `Makefile`
- `.gitignore`
- `.env.example`
## Input data (public sources)
- `data/external/international_results/results.csv (martj42)`
- `data/teams.csv`
- `data/groups.json`
- `data/elo_calibrated_params.json`
- `data/*config*.json`
- `data/raw/provider_docs/** (API docs, no keys)`
## Curated docs
- `outputs/audit/*.md EXCEPT thestatsapi_*`
- `outputs/public/**`
- `outputs/deploy/**`
- `outputs/release/**`
- `docs/**`
- `MODEL_CARD.md`
- `MODEL_FREEZE.md`
- `SOURCE_MANIFEST.txt`

> Everything here is code, public input data, or curated docs with no secrets.
