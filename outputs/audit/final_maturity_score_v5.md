# Final Maturity Score v5

**5.21 -> 6.43** (Δ +1.22)

## Changed this batch
| Dimension | prev | v5 | Why |
|---|---|---|---|
| uncertainty_quantification | 4.5 | 6.0 | Champion probability INTERVALS via beta bootstrap (honestly labeled a floor) |
| validation_methodology | 6.0 | 6.5 | Expanded 2->4 World Cups (2010/14/18/22), all leak-free |
| model_selection_rigor | 7.0 | 7.5 | Dynamic upset-robust ML tested rigorously; kept fixed on evidence |
| test_quality | 5.5 | 6.0 | 558 tests (+10 protecting uncertainty/robustness) |

## Hard cap
~7: champion intervals capture only beta SAMPLING uncertainty (small); the DOMINANT uncertainties — temperature_mul calibration choice, model-structure error, small-tournament variance — are still NOT quantified. Validation = 4 WCs (32-team only; no EUROs/Copa). Market not integrated. Dynamic ML not adopted (marginal).

## Next unlocks
- Quantify STRUCTURAL uncertainty: ensemble over model forms / posterior over temperature_mul -> wider, honest predictive intervals
- Expand validation to EUROs/Copa via a flexible-bracket harness (more upset samples)
- Re-test dynamic ML on the larger sample; adopt if tail-regret gain holds
- Market integration once an odds history accumulates
