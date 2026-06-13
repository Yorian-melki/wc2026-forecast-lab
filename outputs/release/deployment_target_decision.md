# Deployment Target Decision

**Decision (do not deploy yet — this is the chosen path for when you do):**

> **Phase 1 — Static case study on Vercel (ship first).** Zero secrets, zero runtime, never breaks.
> **Phase 2 — Live Streamlit app on Render** at `wc2026.yorian-melki.com`.

## Options compared

| Option | Live Streamlit? | Custom subdomain | Secrets | Cost | Verdict |
|---|---|---|---|---|---|
| **Static case study only** | n/a | yes (Vercel) | none | free | ✅ **Phase 1 — do first** |
| **Render** | yes | yes (CNAME) | env store | free (spins down) / $7·mo | ✅ **Phase 2 — recommended live host** |
| Railway | yes | yes | env store | ~$5·mo usage | ⚪ viable alternative |
| Streamlit Community Cloud | yes | **no on free tier** | st.secrets | free | ⚪ easiest, but cannot map `wc2026.yorian-melki.com` |
| Fly.io | yes | yes | fly secrets | free allowance | ⚪ more ops (Dockerfile) |

## Why Render for the live app
- Hosts a **persistent Streamlit process** (Vercel cannot — it is serverless/static).
- Supports a **custom subdomain** via CNAME → meets the `wc2026.yorian-melki.com` goal (Streamlit
  Community Cloud's free tier does not).
- Clean **env-var secret store** (or deploy the offline snapshot with **no keys at all**).
- Free tier is fine for a portfolio demo (cold starts acceptable); $7/mo removes spin-down.

## Why static-first
The case study carries the whole story (model card, validation, intervals, reviewer audit) with no
runtime risk and no secrets. Ship it on Vercel immediately; add the live app when ready.

## Secret posture
For the public demo, deploy the app reading the **committed offline snapshot** → no API keys
deployed. Add keys to Render's env only if you want live xG/odds refresh.
