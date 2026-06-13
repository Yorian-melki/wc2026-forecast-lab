# Expanded Validation + Upset-Robust ML (Batch B + C)

Generated 2026-06-13T16:43:02 · N=30,000/config

## Accepted: FIFA World Cup 2010, FIFA World Cup 2014, FIFA World Cup 2018, FIFA World Cup 2022
## Rejected: none

## Aggregate champion Brier by config (4 WCs)

| Config | Champ Brier | SF Brier | Entropy | Worst-case regret |
|---|---|---|---|---|
| dynamic_0.20 | 0.02529 | 0.09109 | 2.80852 | 0.0061 |
| elo_only | 0.0255 | 0.09168 | 2.87785 | — |
| fixed_0.20 | 0.02516 | 0.09074 | 2.75598 | 0.0129 |

**Decision: KEEP_FIXED** — adopt dynamic only if it lowers worst-case upset regret AND aggregate champ Brier within 0.2% of fixed

## Per-tournament champion Brier

| Tournament | elo_only | fixed_0.20 | dynamic_0.20 | actual champ |
|---|---|---|---|---|
| 2010 | 0.02109 | 0.02017 | 0.02056 | ESP |
| 2014 | 0.02763 | 0.02799 | 0.02771 | GER |
| 2018 | 0.03016 | 0.03030 | 0.03035 | FRA |
| 2022 | 0.02310 | 0.02217 | 0.02253 | ARG |

## Honest caveats

- Sample is now 4 World Cups (2010/2014/2018/2022) — still small; EUROs/Copa not added (32-team bracket harness only).
- beta_elo held fixed (full-history fit) -> absolute Brier mildly optimistic; config comparison valid.
- ML retrained per cutoff (leak-free).