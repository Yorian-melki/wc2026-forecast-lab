# Phase 2B — Tail-overdispersion diagnostic (offline, in-repo historical set)

Dataset: martj42 competitive 2010-2025, **10,555 matches**. Production scoring grid g=8 (goals 0-7), mu clamp [0.15, cap]. **Baseline = (r=inf, cap=3.60)** = the live independent-Poisson + Dixon-Coles model. All params held at production values (no recalibration). Negative-Binomial dispersion r: smaller r = fatter tail; r=inf = Poisson.

## Baseline (live model on this set)
- 5+ goals mean rank **21.78** · blowout mean rank **17.21** · top-3 33.1% · top-10 74.9%
- Guardrails: Brier 0.5560 · RPS 0.1929 · NLL 0.9414 · acc 58.3% · ECE 0.0983

## Pass/fail rule (pre-registered)
PASS only if **both** 5+ and blowout mean rank drop ≥0.5 abs AND ≥10% rel, **and** Brier/RPS/NLL not worse by >0.5% rel, acc not lower by >0.5pp, ECE not worse by >0.005 abs.

**Candidates that PASS: 0 / 27** (baseline excluded).

## Tradeoff table
|        r |    cap |   rank_5plus |   blowout_rank |   top3_cov |   top10_cov |   brier_wdl |    rps |   nll_wdl |   outcome_acc |    ece | verdict                             |
|---------:|-------:|-------------:|---------------:|-----------:|------------:|------------:|-------:|----------:|--------------:|-------:|:------------------------------------|
|   2.0000 | 3.6000 |      20.8769 |        16.0086 |     0.2981 |      0.7448 |      0.5742 | 0.2012 |    0.9683 |        0.5837 | 0.1332 | FAIL — no material rank improvement |
|   4.0000 | 3.6000 |      21.1094 |        16.4250 |     0.3237 |      0.7483 |      0.5649 | 0.1971 |    0.9552 |        0.5830 | 0.1152 | FAIL — no material rank improvement |
|   6.0000 | 3.6000 |      21.2721 |        16.6477 |     0.3298 |      0.7489 |      0.5619 | 0.1957 |    0.9506 |        0.5837 | 0.1101 | FAIL — no material rank improvement |
|   8.0000 | 3.6000 |      21.3757 |        16.7750 |     0.3342 |      0.7499 |      0.5604 | 0.1950 |    0.9484 |        0.5837 | 0.1073 | FAIL — no material rank improvement |
|  12.0000 | 3.6000 |      21.4748 |        16.9075 |     0.3372 |      0.7501 |      0.5589 | 0.1943 |    0.9460 |        0.5837 | 0.1045 | FAIL — no material rank improvement |
|  20.0000 | 3.6000 |      21.5859 |        17.0327 |     0.3355 |      0.7498 |      0.5577 | 0.1937 |    0.9442 |        0.5837 | 0.1023 | FAIL — no material rank improvement |
| inf      | 3.6000 |      21.7824 |        17.2115 |     0.3308 |      0.7489 |      0.5560 | 0.1929 |    0.9414 |        0.5830 | 0.0983 | FAIL — no material rank improvement |
|   2.0000 | 4.5000 |      20.8729 |        16.0063 |     0.2981 |      0.7449 |      0.5742 | 0.2012 |    0.9682 |        0.5837 | 0.1332 | FAIL — no material rank improvement |
|   4.0000 | 4.5000 |      21.1037 |        16.4207 |     0.3240 |      0.7484 |      0.5649 | 0.1971 |    0.9551 |        0.5830 | 0.1151 | FAIL — no material rank improvement |
|   6.0000 | 4.5000 |      21.2652 |        16.6438 |     0.3298 |      0.7492 |      0.5619 | 0.1957 |    0.9506 |        0.5837 | 0.1101 | FAIL — no material rank improvement |
|   8.0000 | 4.5000 |      21.3683 |        16.7707 |     0.3342 |      0.7503 |      0.5604 | 0.1950 |    0.9483 |        0.5837 | 0.1073 | FAIL — no material rank improvement |
|  12.0000 | 4.5000 |      21.4691 |        16.9032 |     0.3372 |      0.7502 |      0.5589 | 0.1943 |    0.9460 |        0.5837 | 0.1045 | FAIL — no material rank improvement |
|  20.0000 | 4.5000 |      21.5796 |        17.0281 |     0.3355 |      0.7499 |      0.5577 | 0.1937 |    0.9442 |        0.5837 | 0.1023 | FAIL — no material rank improvement |
| inf      | 4.5000 |      21.7761 |        17.2079 |     0.3307 |      0.7491 |      0.5560 | 0.1929 |    0.9414 |        0.5830 | 0.0983 | FAIL — no material rank improvement |
|   2.0000 | 6.0000 |      20.8729 |        16.0063 |     0.2981 |      0.7449 |      0.5742 | 0.2012 |    0.9682 |        0.5837 | 0.1332 | FAIL — no material rank improvement |
|   4.0000 | 6.0000 |      21.1037 |        16.4207 |     0.3240 |      0.7484 |      0.5649 | 0.1971 |    0.9551 |        0.5830 | 0.1151 | FAIL — no material rank improvement |
|   6.0000 | 6.0000 |      21.2652 |        16.6438 |     0.3298 |      0.7492 |      0.5619 | 0.1957 |    0.9506 |        0.5837 | 0.1101 | FAIL — no material rank improvement |
|   8.0000 | 6.0000 |      21.3683 |        16.7707 |     0.3342 |      0.7503 |      0.5604 | 0.1950 |    0.9483 |        0.5837 | 0.1073 | FAIL — no material rank improvement |
|  12.0000 | 6.0000 |      21.4691 |        16.9032 |     0.3372 |      0.7502 |      0.5589 | 0.1943 |    0.9460 |        0.5837 | 0.1045 | FAIL — no material rank improvement |
|  20.0000 | 6.0000 |      21.5796 |        17.0281 |     0.3355 |      0.7499 |      0.5577 | 0.1937 |    0.9442 |        0.5837 | 0.1023 | FAIL — no material rank improvement |
| inf      | 6.0000 |      21.7761 |        17.2079 |     0.3307 |      0.7491 |      0.5560 | 0.1929 |    0.9414 |        0.5830 | 0.0983 | FAIL — no material rank improvement |
|   2.0000 | 8.0000 |      20.8729 |        16.0063 |     0.2981 |      0.7449 |      0.5742 | 0.2012 |    0.9682 |        0.5837 | 0.1332 | FAIL — no material rank improvement |
|   4.0000 | 8.0000 |      21.1037 |        16.4207 |     0.3240 |      0.7484 |      0.5649 | 0.1971 |    0.9551 |        0.5830 | 0.1151 | FAIL — no material rank improvement |
|   6.0000 | 8.0000 |      21.2652 |        16.6438 |     0.3298 |      0.7492 |      0.5619 | 0.1957 |    0.9506 |        0.5837 | 0.1101 | FAIL — no material rank improvement |
|   8.0000 | 8.0000 |      21.3683 |        16.7707 |     0.3342 |      0.7503 |      0.5604 | 0.1950 |    0.9483 |        0.5837 | 0.1073 | FAIL — no material rank improvement |
|  12.0000 | 8.0000 |      21.4691 |        16.9032 |     0.3372 |      0.7502 |      0.5589 | 0.1943 |    0.9460 |        0.5837 | 0.1045 | FAIL — no material rank improvement |
|  20.0000 | 8.0000 |      21.5796 |        17.0281 |     0.3355 |      0.7499 |      0.5577 | 0.1937 |    0.9442 |        0.5837 | 0.1023 | FAIL — no material rank improvement |
| inf      | 8.0000 |      21.7761 |        17.2079 |     0.3307 |      0.7491 |      0.5560 | 0.1929 |    0.9414 |        0.5830 | 0.0983 | FAIL — no material rank improvement |