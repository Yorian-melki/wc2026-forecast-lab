# Market Disagreement Control (Batch D)

Generated 2026-06-13T16:48:46 · 4 matches · **warning layer only, not blended**

Class counts: {'agree': 1, 'model_more_confident': 2, 'model_underprices_team': 1, 'market_unavailable': 0}

| Match | Class | Market H/D/A | Model H/D/A | Max disagree |
|---|---|---|---|---|
| MEX-RSA | model_more_confident | [0.671, 0.219, 0.11] | [0.731, 0.174, 0.096] | 0.06 |
| KOR-CZE | agree | [0.368, 0.31, 0.319] | [0.388, 0.278, 0.334] | 0.033 |
| CAN-BIH | model_more_confident | [0.521, 0.275, 0.204] | [0.588, 0.233, 0.18] | 0.067 |
| USA-PAR | model_underprices_team | [0.466, 0.3, 0.237] | [0.292, 0.265, 0.443] | 0.206 |

**Key finding:** USA-PAR: model underprices USA vs market (market 0.47 home, model ~0.29) — model's USA Elo lags market expectation. Surfaced as a control-layer warning, not auto-corrected.

**Decision:** Do NOT blend market into model (4 matches). Keep as a disagreement monitor; revisit if a larger odds history accumulates.

## Caveats

- 4 matches only.
- 3/4 home teams are host nations (model applies host boost).
- Market is a strong but not infallible baseline.