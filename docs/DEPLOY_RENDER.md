# Deploy the Live App on Render (manual — CLI not installed)

The repo has `render.yaml` (Blueprint), so most is automatic.

1. https://render.com → log in (GitHub login).
2. **New + → Blueprint** → connect **Yorian-melki/wc2026-forecast-lab**.
3. Render reads `render.yaml`:
   - build: `pip install -r requirements.txt`
   - start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - plan: free (cold starts) or Starter ($7/mo).
4. **Env vars** (the `sync:false` keys): paste from local `.env`. NAMES in `outputs/deploy/env_var_inventory.md`.
   To ship a no-secret demo, skip them — the app runs on the committed snapshot.
5. Create → first build ~3–5 min → URL like `https://wc2026-forecast-lab.onrender.com`.
6. Settings → Custom Domains → add `wc2026.yorian-melki.com` → copy the CNAME target → see `DNS_SPACESHIP.md`.

Never put key values in `render.yaml` or any committed file.
