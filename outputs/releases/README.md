# outputs/releases/

One folder per released model version (created from Phase 2 onward). Each `outputs/releases/<version>/`
holds the rollback artifacts for that release:

- `model_config.json` — the config used for that release
- `forecast_snapshot.csv` — the forecast at release time
- `scorecard_metrics.json` — the metric snapshot at release time
- `CHANGELOG.md` — the changelog entry for that release

Empty for now (Phase 1A established the structure; no model release has been cut yet).
