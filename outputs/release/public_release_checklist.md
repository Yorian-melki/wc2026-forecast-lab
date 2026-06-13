# Public Release Checklist

## 0. Pre-push verification (run all; all must pass)
```bash
cd ~/FinderProjects/wc2026_june2026

# tests
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q          # expect: 571 passed

# secret scan — must return NOTHING
grep -rInE 'fapi_[A-Za-z0-9]{25,}|[a-f0-9]{64}|Bearer [A-Za-z0-9._-]{20,}' \
  --exclude-dir=.venv --exclude-dir=.git . | grep -iE 'key|token|secret|bearer'

# confirm secret files are ignored (after `git init` below)
git check-ignore .env .env.backup.20260613_192400          # both must print
```

## 1. Initialize git (local only — do NOT push yet)
```bash
git init
git add .
git status --porcelain | grep -iE '\.env($|\.)' | grep -v example   # MUST be empty
```
If that grep prints anything, STOP — a secret would be staged.

## 2. First commit
```bash
git commit -m "WC2026 probabilistic forecast lab — public release"
```
End commit messages with the Co-Authored-By trailer if desired.

## 3. Create GitHub repo (public)
```bash
gh repo create wc2026-forecast-lab --public --source=. --remote=origin --description \
  "Probabilistic WC2026 forecast lab — Elo/DC + ML, leak-free validation, uncertainty intervals"
# then:
git push -u origin main
```
(Or create the repo in the GitHub UI and `git remote add origin … && git push`.)

## 4. Vercel — portfolio + case study (apex/www already Vercel-wired)
- Add a `/projets/wc2026` page using `outputs/release/portfolio_handoff_pack.md`
  + `outputs/public/wc2026_final_forecast_chart.png` + captured screenshots.
- No secrets, no runtime — static.

## 5. Render — live Streamlit app (Phase 2, later)
- New Web Service → connect the GitHub repo.
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Env: add API keys only if live refresh wanted (else app uses the committed snapshot).

## 6. DNS — LATER, NOT NOW (user action; Claude will not change DNS)
- For `wc2026.yorian-melki.com`: in Spaceship DNS add a CNAME `wc2026` → Render's target.
- Apex + www already point to Vercel — no change needed for the portfolio.

## Rollback / safety
- ML off: set `use_ml_match_model=false` in `data/model_stack_config.json`.
- If a secret is ever committed: rotate the key immediately, then scrub history (or, since this is
  a fresh repo, delete and re-init clean).
