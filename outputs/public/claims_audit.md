# Claims Audit — WC2026 Forecast

All figures verified from source files. No rounded or approximate values used without explicit marking.

---

## Data counts (verified from `data/external/international_results/results.csv`)

| Claim | Verified count | Source |
|:------|:--------------:|:------:|
| Total match records in database | **49,450** | `wc_count(results.csv)` |
| Post-2000 matches | **25,388** | date filter |
| Post-2010 matches (all types) | **15,862** | date filter |
| Competitive post-2010 (excl. friendlies) | **~10,809** | tournament name filter (approximate — depends on exact "friendly" definition) |
| Competitive matches used in Elo calibration fitting | **10,555** | `data/elo_calibrated_params.json → n_train_matches` |
| Unique national teams/countries in full dataset | **336** | unique team names |
| Unique tournament categories in dataset | **200** | unique tournament values |

> NOTE: "49,450 international match records" is exact and verifiable. Use this number.
> "10,555 competitive matches for calibration" is exact (from fitting code, stored in params). Use this.
> "10,809" should NOT be used publicly — it uses a simplified friendly-filter.

---

## Model parameters (verified from `data/elo_calibrated_params.json`)

| Parameter | Value | Source |
|:----------|:-----:|:------:|
| beta_elo (original, fitted) | **0.988351** | params.json → `original_beta_elo` |
| beta_elo (corrected, production) | **0.543593** | params.json → `beta_elo` |
| temperature multiplier | **0.55** | params.json → `temperature_mul` |
| log_base | **0.226934** | params.json |
| base_xg | **1.2547** goals/team | params.json |
| rho (Dixon-Coles) | **−0.021007** | params.json |
| Fit date | 2026-06-09 | params.json |
| Fit dataset | martj42 competitive 2010–2025 | params.json |

---

## Simulation (verified from `outputs/tournament_run/elo_calibrated_summary.csv`)

| Parameter | Value |
|:----------|:-----:|
| Iterations | **100,000** |
| Seed | **20260609** |
| Model | elo_calibrated (temperature-corrected) |

### Conservation laws (all pass)

| Stage | Sum | Expected |
|:------|:---:|:--------:|
| champion_prob | 1.0000 | 1 |
| final_prob | 2.0000 | 2 |
| sf_prob | 4.0000 | 4 |
| qf_prob | 8.0000 | 8 |
| group_survival_prob | 32.0000 | 32 |

---

## Final top-10 champion probabilities (verified)

| Rank | Team | P(champion) |
|:----:|:-----|:-----------:|
| 1 | ESP | **16.97%** |
| 2 | ARG | **14.76%** |
| 3 | FRA | **10.03%** |
| 4 | ENG | **6.71%** |
| 5 | BRA | **5.69%** |
| 6 | COL | **4.82%** |
| 7 | POR | **4.81%** |
| 8 | NED | **3.30%** |
| 9 | ECU | **3.09%** |
| 10 | GER | **3.02%** |

---

## Concentration metrics (verified)

| Metric | Before correction | After correction |
|:-------|:-----------------:|:----------------:|
| Top-1 | ~30.4% | **16.97%** |
| Top-3 | ~66.4% | **41.76%** |
| Top-5 | ~77.9% | **54.16%** |
| Top-10 | ~91.2% | **73.20%** |
| Champion entropy | ~2.195 bits | _(not re-measured post-correction)_ |

> "Before" numbers are from 100K simulation with original beta_elo=0.988.
> "After" numbers are from 100K simulation with beta_elo=0.5436.

---

## Historical sanity benchmark (internal — NOT external data)

The "historical WC reference" used for concentration validation is **not from external betting markets or peer-reviewed studies**. It is the output of our own simulation applied to pre-tournament Elo snapshots:

| Snapshot | beta_mul | top-3 |
|:---------|:--------:|:-----:|
| WC2018 teams (Elo before 2018-06-01) | 0.55 | 35.6% |
| WC2022 teams (Elo before 2022-11-01) | 0.55 | 39.2% |

**Usage rule:** Say "internal sanity check" or "our simulated pre-tournament concentrations for WC2018/WC2022 Elo snapshots." Do NOT say "historical market data" or "betting market calibration."

---

## Claims status

| Claim | Status | Notes |
|:------|:------:|:------|
| "49,450 international football match records" | ✓ EXACT | verified from results.csv |
| "10,555 competitive matches used for Elo calibration" | ✓ EXACT | from params.json |
| "100,000 Monte Carlo simulations" | ✓ EXACT | from simulation config |
| "Exact 48-team WC2026 bracket mechanics" | ✓ EXACT | from bracket.py |
| "Full Hybrid rejected — ECE degraded 17%" | ✓ EXACT | from P2.5 ablation (0.0199 vs 0.0170) |
| "Over-concentration detected and corrected" | ✓ EXACT | top3: 66.4% → 41.76% |
| "Conservation law verified" | ✓ EXACT | sum=1.000 for champion stage |
| "historical WC reference 36–39%" | ⚠ INTERNAL | from our own simulation, not external data |
| "beats betting markets" | ✗ FORBIDDEN | no comparison made |
| "hedge-fund-grade" | ✗ FORBIDDEN | no institutional validation |
| "AI predicts winner" | ✗ FORBIDDEN | outputs are probabilities |
