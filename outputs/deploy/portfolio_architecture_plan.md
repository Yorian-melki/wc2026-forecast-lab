# Portfolio Architecture Plan

## Vision
`yorian-melki.com` = central portfolio. WC2026 is the flagship technical case study.

```
yorian-melki.com                     -> portfolio home            [Vercel]
www.yorian-melki.com                 -> same (already Vercel-wired)
yorian-melki.com/projets/wc2026      -> WC2026 case study (static) [Vercel]
wc2026.yorian-melki.com              -> live Streamlit forecast    [Render/Railway]
  future: /projets/major, /projets/black-ice, /projets/pro-act-invest
```

## Why this split
- **Vercel** hosts the portfolio + static case-study pages (fast, free, apex+www already pointed at Vercel).
- **Render/Railway** hosts the live Streamlit app (persistent Python process — Vercel can't run it).
- The case study (static) carries no secrets and never breaks; the live app is separable and optional.

## Build order (low-risk first)
1. **Static case study** at `/projets/wc2026` from `outputs/public/portfolio_wc2026_case_study.md`
   + the champion chart + a screenshot of the dashboard. No secrets, no live dependency. **Ship first.**
2. **Live app** on Render at `wc2026.yorian-melki.com`, reading the committed snapshot (no keys).
3. **Live refresh** (optional): add API keys to Render env; enable the live providers.

## Per-project template (reuse for future projects)
- `/projets/<slug>` static case study (problem → stack → validation → honest limits).
- optional `<slug>.yorian-melki.com` live app if it needs a runtime.
- one short LinkedIn post + one README per project.

## User actions required
- Choose host for the live app (recommend Render).
- Add the `wc2026` CNAME at Spaceship when ready (Claude will not change DNS).
- Decide live vs static-snapshot demo.
