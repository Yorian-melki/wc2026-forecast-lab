# Reviewer Attack Audit — 20 strongest objections

Generated 2026-06-13T17:18:53 UTC · severity {'HIGH': 6, 'MEDIUM': 11, 'LOW': 3} · defended/now-defended 8/20

| # | Objection | Sev | Defended | Artifact | Remaining weakness | Action |
|---|---|---|---|---|---|---|
| 1 | Only 4 World Cups validated — far too few to trust tournament-level claims | HIGH | partial | `outputs/audit/expanded_tournament_validation.json` | 4 WCs, all 32-team; no EUROs/Copa | flexible-bracket harness to add EUROs/Copa |
| 2 | beta intervals are too narrow because structural uncertainty is excluded | HIGH | partial (labeled a FLOOR) | `outputs/audit/beta_uncertainty_bootstrap.json` | temperature/model-form/tournament-variance uncertainty unquantified | model-form ensemble + posterior over temperature_mul |
| 3 | ML overrates favorites and would hurt on upset tournaments | MEDIUM | yes | `outputs/audit/tournament_walkforward_validation.json (weight cut 0.5->0.2)` | still helps favorites/hurts upsets at 0.20 | adopt dynamic ML on larger sample |
| 4 | Market odds extracted but never used to correct the model | LOW | yes (benchmark by choice) | `outputs/audit/market_disagreement_control.json` | no market calibration; 4 matches | accumulate odds history, revisit |
| 5 | xG sources are not independent (Highlightly == TheStatsAPI upstream) | MEDIUM | yes (documented) | `outputs/audit/thestatsapi_final_retest.json (single_upstream_xg_likely)` | no truly independent xG cross-check | add Understat/FBref via soccerdata |
| 6 | Live API data can drift or break silently | MEDIUM | partial | `data/live/provider_status.json + saved raw responses` | no automated drift alerting | scheduled freshness/disagreement alerts |
| 7 | Team names may silently map to the 1500 default Elo | MEDIUM | yes | `run_expanded_validation_and_dynamic_ml.py (rejects unresolved teams)` | WC2026 name map not auto-asserted | add WC2026 name-resolution test |
| 8 | Dashboard implies more certainty than the evidence warrants | HIGH | partial (intervals+caveats added this batch) | `app.py Forecast Uncertainty panel` | needs explicit 'what this is / is not' | Batch F panel (this batch) |
| 9 | Deployment could leak the 5 API keys | HIGH | NOW yes | `'.gitignore' now excludes .env; .env.example added` | was a real gap until this batch | env_var_inventory + never commit .env |
| 10 | beta_elo was fit with future data relative to WC2018/2022 backtests | MEDIUM | yes | `wc_historical_backtest.json + walk-forward holds beta fixed` | no per-era beta refit | refit beta per held-out era |
| 11 | temperature_mul=0.55 is a hand calibration, not bootstrapped | HIGH | partial (acknowledged) | `beta_uncertainty_bootstrap.json caveats` | its uncertainty not propagated | posterior/sensitivity over temperature_mul |
| 12 | Champion probabilities are Monte Carlo point estimates with noise | LOW | yes | `100k sims, conservation Σ=1.000 verified` | ~0.1pp MC noise (immaterial) | none material |
| 13 | ML uses only 2 features (elo_diff, neutral) — underpowered | MEDIUM | yes (anti-overfit, beats Elo held-out) | `ml_validation_report.json` | richer features untested | gate-test more features |
| 14 | Penalties / extra-time mechanics are simplistic and high-variance | MEDIUM | partial | `logistic penalty model in calibrated_elo_model.py` | KO mechanics not separately validated | validate KO sub-model |
| 15 | No injury, suspension, or squad-depth modeling | MEDIUM | acknowledged | `model_card_public.md limitations` | real gap | provider injury feed |
| 16 | Reproducibility was scattered across many scripts | LOW | NOW yes | `scripts/rebuild_publication_forecast.py` | full run is ~25min | none |
| 17 | Many contradictory maturity reports (v2..v5) confuse the record | MEDIUM | NOW yes | `artifact_consistency_audit.json (v5 canonical)` | historical files remain (labeled) | keep v5 as source of truth |
| 18 | Maturity score is self-assigned, not externally reviewed | MEDIUM | partial (per-dimension, capped honestly) | `final_maturity_score_v5.md` | no external review | seek external review |
| 19 | Single-tournament variance dominates — one WC is high variance | HIGH | yes (this is WHY intervals+entropy exist) | `champion_probability_intervals.json` | inherent to the problem | communicate clearly, never imply certainty |
| 20 | 'ML beats Elo' is a small 0.508 vs 0.529 Brier edge on one test window | MEDIUM | yes | `ml_validation_report.json (leak-free 3580 matches, Brier+NLL+ECE all better)` | modest edge; single window | more held-out years |

## Top unresolved weaknesses

- structural uncertainty beyond beta sampling
- only 4 WCs validated
- temperature_mul uncertainty

## Honest verdict

The project survives most attacks with documented artifacts. The genuinely unresolved core weakness is **uncertainty completeness**: the intervals quantify beta *sampling* error only, while the dominant structural/temperature uncertainty is acknowledged but not yet modeled. A serious reviewer should accept the project as an honest, auditable lab — NOT as a calibrated tournament-level forecaster proven on a large sample.