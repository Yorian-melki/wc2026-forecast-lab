# Dependency Install Audit (Phase 3)

Installed 2026-06-13T13:18:26:

| Package | Version | Import | Purpose |
|---|---|---|---|
| scikit-learn | 1.9.0 | ✓ | logistic 1X2 baseline + isotonic calibration |
| statsmodels | 0.14.6 | ✓ | GLM/Poisson goal models (available, not yet used) |
| penaltyblog | 1.11.0 | ✓ | Dixon-Coles / football goal models (available, not yet used) |

Rejected (this pass): lightgbm, xgboost, catboost.
Tests after install: 521 passed (unchanged).
