# Tournament Walk-Forward Validation (WC2018 + WC2022)

Generated 2026-06-13T16:02:28 · N=30,000/config · seed=20260613 (common random numbers across weights)

## Aggregate champion Brier by ML weight (mean of WC2018, WC2022)

| ML weight | Champ Brier ↓ | SF Brier | Group Brier | Entropy | Mean top-1 |
|---|---|---|---|---|---|
| 0.00 | 0.02663 | 0.10049 | 0.19844 | 2.8903 | 0.17145 |
| 0.10 | 0.02636 | 0.10068 | 0.1972 | 2.829 | 0.1838 |
| 0.20 ←chosen | 0.02624 | 0.10095 | 0.19615 | 2.775 | 0.19155 |
| 0.30 | 0.02618 | 0.10105 | 0.19489 | 2.7196 | 0.204 |
| 0.50 | 0.02608 | 0.10206 | 0.1941 | 2.6109 | 0.2263 |

**Chosen ML weight: 0.20** (smallest ML weight that improves aggregate champ Brier, captures >=60% of best improvement, AND keeps worst-case per-tournament regret <=3%; else 0 (ML tournament-diagnostic-only)).
Champion Brier 0.02624 vs Elo-only 0.02663 (+1.49%). Overconcentration flag: **True**.

## Per-tournament detail

### FIFA World Cup 2018 (random champ Brier 0.9688)
| weight | champ Brier | actual champ | rank | p | entropy | top-1 |
|---|---|---|---|---|---|---|
| 0.00 | 0.03016 | FRA | #5 | 0.055 | 2.909 | 0.171 BRA |
| 0.10 | 0.03034 | FRA | #6 | 0.054 | 2.859 | 0.180 BRA |
| 0.20 | 0.03030 | FRA | #5 | 0.057 | 2.805 | 0.189 BRA |
| 0.30 | 0.03062 | FRA | #5 | 0.056 | 2.743 | 0.204 BRA |
| 0.50 | 0.03117 | FRA | #6 | 0.053 | 2.641 | 0.230 BRA |

### FIFA World Cup 2022 (random champ Brier 0.9688)
| weight | champ Brier | actual champ | rank | p | entropy | top-1 |
|---|---|---|---|---|---|---|
| 0.00 | 0.02310 | ARG | #1 | 0.172 | 2.871 | 0.172 ARG |
| 0.10 | 0.02239 | ARG | #1 | 0.187 | 2.799 | 0.187 ARG |
| 0.20 | 0.02217 | ARG | #1 | 0.194 | 2.745 | 0.194 ARG |
| 0.30 | 0.02174 | ARG | #1 | 0.204 | 2.696 | 0.204 ARG |
| 0.50 | 0.02100 | ARG | #1 | 0.223 | 2.581 | 0.223 ARG |

## Honest notes

- Team Elos: leak-free (pre-cutoff rolling Elo).
- ML model: leak-free (retrained per cutoff; never sees the test tournament).
- beta_elo: FIXED across weights (full-history fit) -> absolute Brier mildly optimistic, but weight comparison valid.
- Sample = 2 tournaments. Treat as directional evidence, not proof.