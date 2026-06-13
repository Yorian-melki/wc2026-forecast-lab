# Model Card — WC2026 Monte Carlo Forecast

**Version:** P4 (frozen 2026-06-10)  
**Type:** Probabilistic tournament simulator  
**Status:** Publication-ready

---

## What the model does

Simulates the 2026 FIFA World Cup (48 teams, North America) through 100,000 independent bracket runs and reports champion probabilities for each team. Each simulation plays every group match and knockout round using Poisson-distributed goal counts, derived from Elo rating differences.

**Output:** A probability distribution over the 48 teams, not a single predicted winner.

---

## What the model does NOT do

- Does not predict match scores
- Does not predict individual match outcomes
- Does not use in-tournament injury or squad updates
- Does not compare to or claim to beat betting markets
- Does not provide betting advice
- Does not output certainties

---

## Data sources

| Source | Description | Access |
|:-------|:-----------|:------:|
| martj42/international-football-results | 49,450 international match records 1872–2025 | Public GitHub |
| StatsBomb Open Data | Pressing intensity / shot quality for 30/48 WC2026 teams | Public GitHub |
| FIFA Elo ratings (elo_current) | Current Elo at time of freeze | teams.csv (manual) |

**Competitive matches used for Elo calibration fitting:** 10,555 (martj42, 2010–2025)

---

## Model selection history

Four model families were evaluated in sequence:

### P1 — Pure MLE Dixon-Coles
Fitted attack/defense parameters for each national team via maximum likelihood on independent Poisson with Dixon-Coles correction.  
**Rejected:** Did not beat Elo baseline on holdout NLL.

### P2.5 — Full Hybrid Elo-DC
Combined Elo backbone with per-team attack/defense residuals (646 parameters) fitted on rolling temporal splits.  
**Rejected:** ECE degraded 17% vs baseline (0.0199 vs 0.0170). Zero clear-win splits across 4 temporal holdouts. Production gate: BORDERLINE_EXPERIMENTAL. Residual parameters add overconfidence, not signal.

### P3 — Elo-calibrated (original)
Rolling Elo fitted on competitive-only data (2010–2025) via L-BFGS-B.  
**Promoted to production candidate** — best ECE among tested variants.  
**Issue detected in P3.5:** beta_elo=0.988 too high (competitive-only training amplifies Elo signal). Top-3 concentration: 66.4%.

### P3.5 — Elo-calibrated (temperature-corrected)
Applied temperature multiplier 0.55 to beta_elo.  
**Result:** Top-3 concentration: 41.76%. Internal WC2018/WC2022 Elo snapshots yield 36–39% at same correction — consistent.  
**Gate: PASS_WITH_TEMPERATURE. Selected as final model.**

---

## Final model

**Elo-calibrated, temperature-corrected Poisson simulator**

Expected goals:
```
log_μ_home = log_base + β_elo × (Elo_home − Elo_away) / 400
log_μ_away = log_base − β_elo × (Elo_home − Elo_away) / 400
```

Parameters:
- `log_base = 0.226934` (base_xg = 1.255 goals/team/match)
- `β_elo = 0.543593` (temperature-corrected from fitted 0.988)
- `ρ = −0.021007` (Dixon-Coles low-score correction)

Goal scoring: sampled from truncated Poisson. Draws go to extra time (same reduced-intensity Poisson) then penalties (logistic skill prior).

---

## Simulation mechanics

- 100,000 independent Monte Carlo simulations
- Seed: 20260609
- Bracket: exact WC2026 structure (12 groups of 4, top-2 + 8 best third-place advance to R32)
- Knockout: R32 → R16 → QF → SF → Final
- Penalties: logistic win probability based on specialist/goalkeeper ratings
- Discipline: Poisson yellow/red card accumulation, red card malus applied
- Jet lag: European teams in North America get modest xG reduction
- Home nations: USA, MEX, CAN receive +8% xG boost

Conservation laws verified: Σ P(champion) = 1.000, Σ P(finalist) = 2.000, Σ P(SF) = 4.000, Σ P(QF) = 8.000, Σ P(group advance) = 32.000

---

## Validation

| Test | Result |
|:-----|:------:|
| P2.5 ablation — Full Hybrid ECE vs baseline | +17% worse (rejected) |
| P2.5 holdout NLL — 4 temporal splits | No clear-win splits for hybrid |
| P3.5 concentration audit | top3: 66.4% → 41.76% (corrected) |
| Internal WC snapshots (WC2018/WC2022 Elos) | 35–39% top-3 at corrected beta |
| Conservation laws | All 5 pass (error < 0.001) |
| Full test suite | 278 tests, 278 passing |

---

## Concentration correction

**Problem:** beta_elo=0.988 fitted on competitive-only data over-amplifies Elo signal in the full WC draw (includes mismatches like rank 5 vs rank 45).

Example: ESP vs median team (Elo diff 373): μ_ESP=3.15, μ_median=0.50 at original beta. P(ESP win 90min) ≈ 83%.

**Fix:** Temperature multiplier 0.55 applied to beta_elo. Not fitted on external calibration data — validated by internal sanity check on historical Elo snapshots.

**Honest framing:** "We applied a shrinkage correction to prevent extreme amplification of top-team advantage. The correction is internally validated, not peer-reviewed."

---

## Limitations

1. beta_elo correction is heuristic (internal sanity only, not cross-validated on WC outcomes)
2. Elo ratings frozen at data cutoff — no pre-tournament form
3. No injury or squad depth modeling
4. Bracket path correlations not captured
5. Penalty model uses skill proxies, not shoot-out specialists
6. Host advantage is a flat boost, not crowd-calibrated
7. Source data may have recording errors in older matches (pre-1990)

---

## Reproducibility

Full reproduction in one command:
```bash
PYTHONPATH=src .venv/bin/python scripts/reproduce_public_outputs.py
```

All outputs are deterministic given the same seed and data.

---

## Public claims allowed

- "I ingested 49,450 international football match records"
- "I benchmarked simpler and more complex model variants"
- "I rejected the pure MLE model because it failed validation"
- "I rejected the full hybrid model — it degraded calibration and showed no robust improvement"
- "I detected and corrected tournament-level over-concentration"
- "I ran 100,000 Monte Carlo simulations through the WC2026 bracket"
- "The model outputs probabilities, not certainties"
- "Exact 48-team WC2026 bracket mechanics"
- "Conservation law verified: Σ P(champion) = 1"

## Public claims forbidden

- "AI predicts the World Cup winner"
- "hedge-fund-grade"
- "fully calibrated"
- "beats betting markets"
- "guaranteed edge"
- "production betting model"
- "sure prediction" / "will win"
- "peer-reviewed methodology"
- "historical market data confirms" (our historical check is internal, not market data)
