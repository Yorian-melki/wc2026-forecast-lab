# Phase 3G — Sportmonks Market-Odds International Generalization

> **Offline research only.** No production model/app/data/config change, no integration, no betting,
> Sportmonks-only. Token from `.env.yorian` (never printed; scrubbed; leak scan clean). Rate-limit-safe
> (Retry-After / exponential backoff, max 2 retries, then skip+record). **Run completed: 39 requests,
> 0 rate-limited.** Files: `scripts/research/sportmonks_market_generalization.py`,
> `outputs/research/phase_3g_market_generalization/`.

## Bounded extraction plan (executed)
International tournament **finals** (balanced top-team events, WC-comparable), from the Phase 3G inventory
(league ids not re-searched). Reused the frozen Phase 3E WC dataset for the WC segment.
| Competition | League | Editions targeted | Usable 1X2 obtained |
|---|---|---|---|
| Euro | 1326 | 2020, 2024 | **2020 only (51)** |
| Copa America | 1114 | 2019, 2021, 2024 | **2019+2021 (54)** |
| AFCON | 1117 | 2019, 2021, 2023, 2025 | **2019+2021 (104)** |
| AFC Asian Cup | 1105 | 2019, 2023 | **2019 (47)** |
| World Cup (reused 3E) | 732 | 2018, 2022 | 128 |
**Excluded (documented):** WC/AFCON/Asian qualifiers + UEFA Nations League — too large / weak-team-heavy
for a bounded phase (avoids uncontrolled crawl).

**Coverage caveat (important):** ~498 international fixtures were collected, but **only the 2019–2021
editions produced usable Fulltime-Result (1X2) odds (256 intl fixtures).** The **2023–2025 finals (Euro
2024, Copa 2024, AFCON 2023/2025, Asian Cup 2023) returned no usable 1X2** in this extract — the same
pattern seen for WC2026 in Phase 3E (recent international 1X2 not populated/settled in this data tier).
So the generalization evidence spans **five competitions but mostly the 2018–2022 era.**

## Counts
- International fixtures collected: ~498 · **usable 1X2: 256** (2019–2021 editions).
- Unified eval set (matched to full production by date+team): **356** = 228 non-WC + 128 WC.

## Results — market vs FULL production (OOS, bootstrap CIs)
Δ = market − production RPS (negative = market better).
| Segment | n | prod RPS | market RPS | ΔRPS [95% CI] | beyond noise? | blend* α | prod ECE | mkt ECE |
|---|---|---|---|---|---|---|---|---|
| **pooled ALL** | **356** | 0.2116 | **0.1861** | **−0.025 [−0.036, −0.015]** | **YES** | 1.0 | 0.070 | **0.050** |
| **pooled non-WC** | **228** | 0.1991 | **0.1773** | **−0.022 [−0.032, −0.011]** | **YES** | 1.0 | 0.083 | **0.057** |
| pooled WC | 128 | 0.2338 | 0.2020 | −0.032 [−0.055, −0.007] | YES | 1.0 | 0.109 | 0.047 |
| AFCON | 100 | 0.2073 | 0.1942 | −0.013 [−0.026, −0.0001] | YES (marginal) | 1.0 | 0.080 | 0.044 |
| Asian Cup | 44 | 0.2124 | 0.1575 | −0.055 [−0.085, −0.022] | YES | 1.0 | 0.108 | 0.142 |
| Copa America | 33 | 0.1692 | 0.1382 | −0.031 [−0.067, +0.002] | within noise | 1.0 | 0.206 | 0.104 |
| **Euro** | 51 | 0.1908 | 0.1863 | **−0.004 [−0.022, +0.014]** | **within noise (≈ tie)** | 0.8 | 0.165 | 0.226 |
| pre-2022 | 244 | 0.2049 | 0.1734 | −0.031 [−0.044, −0.019] | YES | 1.0 | 0.082 | 0.061 |
| post-2022 | 112 | 0.2260 | 0.2138 | −0.012 [−0.034, +0.010] | within noise | 0.8 | 0.118 | 0.069 |

## Reading the evidence
- **The market edge GENERALIZES beyond the World Cup:** pooled **non-WC** international (n=228) beats full
  production **beyond bootstrap noise** (ΔRPS −0.022, CI excludes 0), and so does pooled-ALL (n=356). It is
  **not** a WC-only artifact. Market is also better calibrated overall (ECE 0.050 vs 0.070 pooled).
- **But it's heterogeneous, and the pattern is informative:** the edge is **largest where the Elo→DC→ML
  model is weakest** — Asian Cup (Δ−0.055), WC final (−0.032), AFCON (−0.013) — and **≈ zero on the Euro**
  (Δ−0.004, within noise; blend α=0.8). European teams are data-rich and well-modelled, so the model holds
  its own there; in less-modelled confederations (AFC/CAF) and balanced WC finals, the market is far sharper.
- **Best blend = α=1.0 (pure market)** on every segment except Euro/post-2022 (α=0.8) — production adds
  incremental value only in the strong-model (European) regime.
- **Era caveat:** pre-2022 is strongly significant (n=244); **post-2022 is within noise (n=112)** — partly
  because recent international 1X2 odds were sparse in this extract, so the post-2022 sample is thin and
  WC2022-dominated.

## Critical practical gate (for any future deployment on WC2026)
Phase 3E already found **WC2026 had usable O/U but no usable 1X2** in the same-style extract, and 3G found
the 2023–2025 finals likewise lacked usable 1X2. **So the historical signal is proven, but LIVE WC2026
pre-match 1X2 odds availability is UNCONFIRMED** — and without it, the market feature cannot be served for
the actual target tournament. Resolving live 1X2 availability (Sportmonks live pre-match, or The Odds API)
is the #1 design question.

## Answers to the brief
1. Leagues/seasons: Euro 1326 (2020), Copa 1114 (2019/21), AFCON 1117 (2019/21), Asian Cup 1105 (2019),
   WC 732 (2018/22 reused). 2023–2025 editions collected but no usable 1X2.
2. Fixtures extracted: ~498 international collected.
3. Usable 1X2: 256 international (+128 WC reused) → **356 matched to production**.
4. Market vs full production: pooled market RPS 0.1861 vs prod 0.2116 (and 0.1773 vs 0.1991 non-WC).
5. Best blend: α=1.0 on all but Euro/post-2022 (α=0.8).
6. Bootstrap CIs: pooled & non-WC exclude 0 (significant); Euro/Copa/post-2022 within noise.
7. **Generalizes beyond WC? YES** on the pooled and non-WC samples (beyond noise) — but heterogeneous
   (≈ tie on Euro).
8. α=1.0 remains best overall; blend (α=0.8) only helps in the strong-model Euro/recent regime.
9. Files changed: see header + HANDOFF/NEXT_STEP. 10. No production files changed. 11. No secrets leaked.

## Final recommendation: READY_FOR_INTEGRATION_DESIGN — with hard conditions
The generalization gate (the whole point of 3G) is **passed**: the market edge holds across five
international competitions and on the pooled non-WC sample beyond noise, while improving calibration. That
is enough to **start designing** an integration — **not** to integrate. Design must resolve:
1. **LIVE WC2026 1X2 odds availability + fallback** (the binding practical gate — currently unconfirmed).
2. **Regime-aware blend** — the market helps most where the model is weak (AFC/CAF/WC final), ≈ nothing on
   Euro; a flat α=1.0 would needlessly dissolve the model where it's competitive.
3. **Identity preservation** — a market-informed anchor/blend, not "become the bookmaker."
4. **Champion-calibration guardrail** — W/D/L feeds the 100k MC; re-validate champion concentration/Brier.
5. **Close the recent-era odds-coverage gap** (2023–2025 finals + WC2026 1X2) before trusting post-2022.
**No integration, no production change** until a design clears these. Model math remains FROZEN.
