# P1 — Dixon-Coles MLE Calibration Report

**Date:** 2026-06-09 | **Status:** EXPERIMENTAL — NOT PRODUCTION-READY

---

## A. Installation

| Item | Value |
|---|---|
| Python | 3.13.11 (`.venv/bin/python`) |
| scipy | 1.17.1 |
| numpy | 2.4.0 |
| pandas | 3.0.2 |
| MLE stack | ✅ OK |

---

## B. Dataset

| Item | Train (WC2018) | Holdout (WC2022) |
|---|---|---|
| Matches | 64 | 64 |
| Teams | 32 | 32 |
| Unique teams total | 40 | |
| Competitions | StatsBomb season_id=3 | StatsBomb season_id=106 |
| Mapping success | 100% (0 failures) | 100% (0 failures) |
| Mean home goals | ~1.19 | ~1.22 |
| Mean away goals | ~1.30 | ~1.16 |
| Matches/team avg | ~1.6 | |

**CRITICAL WARNING: This is a SPARSE dataset.**
- 40 teams, 128 total matches → ~3.2 matches/team average
- Dixon-Coles with attack+defense+base_xg+rho = 81+ parameters
- Effective degrees of freedom ≈ 128 - 81 = 47. Regularization (L2) is mandatory.
- The model CANNOT be reliably calibrated on this data. It can still find directional patterns.

**WC2014 availability:** NOT available in StatsBomb open data. Not used.

---

## C. Calibration Results

| Item | Value |
|---|---|
| Optimizer | L-BFGS-B (scipy.optimize.minimize) |
| Grid search λ | [0.01, 0.05, 0.10, 0.20] by holdout NLL |
| Best λ by holdout | **0.20** (higher regularization → less overfit) |
| Convergence | Partial (L-BFGS-B condition met but not fully converged) |
| Final NLL (train, no reg) | 2.41 |
| Restarts | 5 (best of 5 picked) |
| rho estimated | **0.2000** (hit upper boundary — optimizer pushed harder DC correction) |
| base_xg | **1.1051** |

**rho at boundary is a warning.** The optimizer wants rho > 0.20 but was capped. This suggests either:
1. The WC2018 data has more 1-0/0-1 scorelines than the model can explain, or
2. 64 matches is too few to reliably estimate rho.

### Top 10 Attack (highest offense strength, WC2018-trained)
```
FRA=0.887, CRO=0.734, BEL=0.615, JPN=0.520, POR=0.499,
RUS=0.465, ARG=0.462, ESP=0.416, ENG=0.390, COL=0.267
```

### Worst 10 Defense (easiest to score against)
```
PAN=-0.739, KSA=-0.671, TUN=-0.573, MEX=-0.530, EGY=-0.506,
CRC=-0.479, GER=-0.459, POR=-0.385, SUI=-0.353, ARG=-0.289
```

Note: GER and POR appear in both top attack and worst defense — consistent with their WC2018 performances (GER eliminated in group stage, POR reached QF).

---

## D. Comparison Table (WC2022 Holdout)

| Model | Train NLL | Holdout NLL | Holdout Brier | Holdout Acc | Holdout ECE |
|---|---|---|---|---|---|
| Random (uniform 1/3) | 1.0986 | 1.0986 | 0.6667 | 0.4531 | 0.0000 |
| **Elo-only** | **1.0478** | **1.0838** | **0.6070** | **0.5625** | 0.1221 |
| Indep Poisson (MLE) | 0.7852 | 1.2331 | 0.7131 | 0.4219 | 0.1211 |
| **DC MLE (experimental)** | 0.8023 | 1.1175 | 0.6651 | 0.5000 | 0.0728 |

**Random NLL baseline:** log(3) = 1.0986

---

## E. Verdict Brutal

| Question | Answer |
|---|---|
| DC MLE beats random on holdout? | **NO** — 1.1175 > 1.0986 |
| DC MLE beats Elo-only on holdout? | **NO** — 1.1175 > 1.0838 |
| DC MLE beats indep Poisson? | YES — 1.1175 < 1.2331 |
| Production candidate? | **NO** |
| Should current expert model be replaced? | **NO** |

### What went wrong?

1. **Dataset too sparse.** 64 training matches for 40 teams. Elo is pre-trained on 10+ years of international football — it carries far more signal than what we can extract from 64 matches.

2. **rho hit boundary.** The DC correction parameter was pushed to the maximum allowed (0.20). This suggests either the data wants a stronger correction, or the optimizer is compensating for a misspecified model by inflating rho.

3. **Indep Poisson overfits.** Train NLL=0.785 (better than DC) but holdout NLL=1.233 (worst of all). Classic overfit on 64 matches — the DC regularization from the tau function is actually hurting here, not helping.

4. **Elo is hard to beat on 64 matches.** Elo = decades of calibrated rating history encoded in a single number per team. A pure bivariate Poisson with 40 attack+defense parameters cannot reliably beat it with this sample size.

### What's needed to make this work?

1. **More data.** 200+ international matches minimum. Options:
   - Expand to all confederations (not just WC) — UEFA Nations League, Copa América, etc.
   - Use openfootball historical results (covers WC back to 1930 + qualifiers)
   - This is the single most impactful action.

2. **Elo as a feature inside the DC model**, not a standalone baseline:
   - `log_mu_h = log_base + elo_diff * k + attack_h + defense_a`
   - Let MLE find the right k coefficient
   - This would combine Elo's pre-calibrated signal with match-specific attack/defense

3. **Team embeddings from more games.** WC teams also play qualifiers, friendlies, Nations League. Their attack/defense parameters should be estimated from ALL their recent games, not just WC games.

---

## F. Files Produced

| File | Contents |
|---|---|
| `outputs/calibration/mle_params.json` | All parameters + metrics + verdict |
| `outputs/calibration/comparison_table.csv` | Model comparison on holdout |
| `outputs/calibration/mapping_failures.csv` | Teams that failed FIFA3 mapping (empty — 100%) |
| `src/wc2026/calibration/datasets.py` | StatsBomb WC dataset builder |
| `src/wc2026/calibration/dixon_coles_mle.py` | Full DC MLE with grid search |
| `src/wc2026/calibration/metrics.py` | NLL, Brier, logloss, ECE, baselines |
| `scripts/calibrate_mle.py` | Calibration runner |
| `tests/test_p1_mle.py` | 22 tests, all pass |

---

## G. Current Production Model Status

The production model at `src/wc2026/match_model.py` is **unchanged**.
The MLE calibration is EXPERIMENTAL and isolated in `src/wc2026/calibration/`.
No production parameters were overwritten.
