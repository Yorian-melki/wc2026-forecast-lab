# Deployment Architecture Audit

Generated 2026-06-13T17:21:42 UTC

## Key constraint
The dashboard is a Streamlit app = a persistent Python process with websockets. Vercel (serverless/static) CANNOT host it. Vercel = portfolio/static; a Python host runs the live app.

## Host comparison

| Host | Feasibility | Cost | Complexity | Secrets | Custom domain | Subdomain | User action | Claude action |
|---|---|---|---|---|---|---|---|---|
| Vercel (portfolio/static + case study) | HIGH (static/Next.js, NOT Streamlit) | free tier | low | env UI | yes | yes | connect repo, confirm project | scaffold static/Next case-study page |
| Streamlit Community Cloud (live app) | HIGH for app | free | low | st.secrets | NO on free tier (share.streamlit.io URL) | no custom subdomain free | connect GitHub repo | prepare repo + secrets template |
| Render (live app) | HIGH | free(spins down)/$7mo | medium | env vars | yes | yes (CNAME) | create service, add env, map subdomain | write render.yaml + Dockerfile/start cmd |
| Railway (live app) | HIGH | ~$5/mo usage | low-medium | env vars | yes | yes | create project, add env | write start config |
| Fly.io (live app) | HIGH | free allowance | higher (Dockerfile) | fly secrets | yes | yes | flyctl launch + secrets | write Dockerfile + fly.toml |
| Static snapshot + separate live app | RECOMMENDED split | free + host | low | n/a for static | yes | yes | host static on Vercel, app on Render | build static export of forecast |
| VPS (DIY) | possible, not advised | $5+/mo | high (ops) | manual | yes | yes | provision, secure, deploy | not recommended |

## Recommendation

- **portfolio_and_case_study**: Vercel (apex+www already Vercel-wired) -> yorian-melki.com + /projets/wc2026
- **live_streamlit_app**: Render (or Railway) at wc2026.yorian-melki.com — supports custom subdomain + env secrets. Streamlit Community Cloud is easiest but cannot map a custom subdomain on the free tier.
- **safest_public_demo**: Deploy the app reading the COMMITTED offline snapshot (no live API keys needed) — zero secret exposure. Add keys to host env only if live refresh is wanted.
- **split**: static case study (Vercel) + live app (Render) is the clean separation.

## Secrets
All hosts: API keys go in the host's env/secret store, NEVER in the repo. The offline forecast needs NO keys; only live refresh does.