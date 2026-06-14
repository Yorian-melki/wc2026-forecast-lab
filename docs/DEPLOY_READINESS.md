# Deploy Readiness — Render + Spaceship DNS (NOT yet deployed)

> Status as of 2026-06-14: **the live Streamlit app is NOT deployed.**
> `wc2026.yorian-melki.com` is **NOT live** — it resolves to nothing until the steps below are done.
> Only the GitHub repo and the Vercel portfolio (`www.yorian-melki.com`) are live.
> This is a checklist to *prepare* a deploy; do not treat any step as done.

## 0. Pre-flight (all green on `main`)
- `requirements.txt` — lean app deps; `streamlit>=1.44,<2` bounded; `penaltyblog` removed; `matplotlib` intentionally excluded (only offline chart scripts need it, not the app).
- `.python-version` = `3.13` (matches the local test env, 3.13.11). See §5 if Render can't resolve it.
- `render.yaml` blueprint present. Build `pip install -r requirements.txt`; start `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`.
- 571 tests pass; all 10 pages render via AppTest; secret scan clean.

## 1. Create the Render service
1. https://render.com → log in with GitHub.
2. **New + → Blueprint** → connect **Yorian-melki/wc2026-forecast-lab** → Render reads `render.yaml`.
3. Pick **plan** (see §3) → Create. First build ≈ 3–5 min.
4. You get a URL like `https://wc2026-forecast-lab.onrender.com`. **This `onrender.com` URL is the live app** once the build is green — the custom subdomain comes later (§4).

## 2. Environment variables
All provider keys are `sync:false` in `render.yaml` (never committed). In the Render dashboard → Environment, paste the values from your local `.env`. Names only (no values) are listed in `outputs/deploy/env_var_inventory.md`:
- `API_FOOTBALL_KEY` (primary live: scores/events/lineups/fixtures/finished)
- `THESTATSAPI_KEY` (finished-match per-shot xG + odds + stats; Stats API trial)
- `HIGHLIGHTLY_API_KEY` + `HIGHLIGHTLY_BASE_URL` (team xG / advanced stats)
- `FOOTBALL_DATA_ORG_KEY` (standings/scorers/fixtures)
- Non-secret config already in `render.yaml`: `PYTHONPATH=src`, `API_FOOTBALL_HOST`, `PRIMARY_LIVE_PROVIDER`.

**Without any keys:** the app still runs. `AUTO_LIVE=False` → no API calls → it serves the committed `data/wc2026_live.json` snapshot and shows a **SNAPSHOT** badge on Live Standings. No crash. This is a valid no-secret public demo (the snapshot will simply not auto-update).

## 3. Free plan vs paid — limitations
Render **free** web service:
- **Spins down after ~15 min idle**; the next visitor waits ~50s for a cold start.
- **Ephemeral filesystem**: runtime writes to `data/wc2026_live.json` (live standings merge) do **not** persist across restarts/redeploys. The app re-fetches, so this is cosmetic, not data loss — but "persisted standings" are not durable on free.
- The 45s auto-refresh fragment only runs **while a viewer has the page open** (the service sleeps otherwise).
- Tight memory; the build (numpy/pandas/scipy/sklearn/statsmodels/plotly/streamlit) is heavy but fits.

**Recommendation:** for a *demo/portfolio link*, **free is fine** (accept cold starts). For anything you'd show live during the tournament with smooth auto-refresh, use **Starter ($7/mo)** — no spin-down, persistent disk optional.

## 4. Custom domain (Spaceship DNS) — only after the service is up
1. Render → your service → **Settings → Custom Domains → Add** `wc2026.yorian-melki.com`. Render shows a **CNAME target** (e.g. `wc2026-forecast-lab.onrender.com`).
2. Spaceship DNS for `yorian-melki.com` → **Add record**:
   - Type **CNAME** · Host **`wc2026`** · Value **`<the Render target>`** · TTL **1 min** (raise later).
   - **DO NOT touch the `@` or `www` records** — those point at the Vercel portfolio and must stay.
3. Wait for DNS propagation + Render auto-TLS (Let's Encrypt). **`https://wc2026.yorian-melki.com` is live ONLY after both DNS resolves AND Render issues the certificate** (can be minutes to a few hours).

See `docs/DNS_SPACESHIP.md` for the exact Spaceship UI steps.

## 5. If the Render build can't resolve Python 3.13
`.python-version` pins `3.13` (tested locally on 3.13.11). If Render's build log can't find a 3.13 image, set a Render-supported version explicitly: dashboard → Environment → add `PYTHON_VERSION` = a `3.13.x` (or `3.12.x`) that Render lists, or edit `.python-version` to that exact value. The app's deps support 3.12 and 3.13.

## 6. Truthful status lines (do not overstate)
- ✅ GitHub repo public · ✅ `www.yorian-melki.com` (Vercel portfolio) live.
- ❌ Live Streamlit app — not deployed. · ❌ `wc2026.yorian-melki.com` — not live (no DNS record yet).
- The in-app Release Status page already states the subdomain is "pending Render + DNS" — keep it that way until §4 is verifiably done.
