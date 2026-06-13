# Final Maturity Score v6

**5.21 -> 6.93** (Δ +1.72)

This batch moved DEFENSIBILITY, not predictive power.

| Dimension | prev | v6 | Why |
|---|---|---|---|
| reproducibility | 8.0 | 9.0 | one-command rebuild, requirements fixed, offline-proven |
| documentation | 7.0 | 9.0 | model card, lineage, reviewer audit, runbook, case study, README destaled |
| publication_readiness | 5.5 | 8.0 | deploy audit, portfolio pack, consistency cleanup |
| code_quality | 7.0 | 7.5 | .env gitignored (security), requirements complete |
| claims_honesty | 9.0 | 9.5 | 20-point self-hostile reviewer audit, stale claims fixed |
| test_quality | 6.0 | 6.5 | 571 tests |

## Hard cap
~7.5: the MODELING ceiling is unchanged this batch — structural uncertainty still unquantified, only 4 WCs validated, xG sources not independent. This batch raised DEFENSIBILITY (reproducibility, documentation, publication-readiness, security), not predictive power. Maturity is self-assessed, not externally reviewed.

## Next unlocks
- Structural-uncertainty quantification (model-form ensemble + temperature posterior)
- Flexible-bracket harness -> EUROs/Copa validation
- Independent xG source (Understat/FBref)
- External/peer review of the maturity claims
- Ship static case study to Vercel + live app to Render
