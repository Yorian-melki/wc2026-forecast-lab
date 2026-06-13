# FILE INDEX — WC2026 Forecast
# All critical files and their purpose.
# Use this when you need to find something quickly.

---

## CORE MODEL CODE (`src/wc2026/`)

| File | Purpose | Modify? |
|------|---------|:-------:|
| `calibrated_elo_model.py` | Elo MLE engine: fits beta_elo, log_base, rho from match data | NO |
| `match_model.py` | Computes expected goals per match (line 51: form coeff 0.008, line 80-82: jet lag) | NO |
| `model_factory.py` | Selects which model (Expert or Elo) to use in simulation | NO |
| `tournament.py` | 48-team bracket mechanics: groups, best-3rd, R32→Final | NO |
| `data_loader.py` | Loads teams.csv, applies temporal form (16 teams), computes jet lag (all 48) | NO |
| `temporal_form.py` | Exponential decay form score (λ=0.030, half-life≈23 days) — used for 16 teams | NO |
| `jet_lag.py` | Jet lag performance multiplier — Dallas UTC-5 approximation | NO |
| `best_thirds.py` | Best third-place team selection logic for R32 | NO |
| `bracket.py` | Bracket draw logic | NO |
| `confidence.py` | Wilson CI computation | NO |
| `entropy.py` | Entropy and concentration metrics | NO |
| `group_rules.py` | Group stage tiebreaker rules | NO |

---

## SCRIPTS (`scripts/`)

| File | Purpose | Run again? |
|------|---------|:----------:|
| `simulate_models.py` | Main simulation runner (both models) | Only if re-running simulation |
| `generate_public_final_chart.py` | Generates `wc2026_final_forecast_chart.png` | Only for P5 chart update |
| `generate_chart.py` | Generates comparison chart | Only for P5 chart update |
| `reproduce_public_outputs.py` | End-to-end verification (5 steps) | YES — use to verify |
| `run_p35_audit.py` | P3.5 temperature ablation — do not re-run | NO |
| `calibrate_mle.py` | Runs MLE fitting — do not re-run | NO |
| `apply_temporal_form.py` | One-time form update script | NO |

---

## DATA FILES (`data/`)

| File | Purpose | Modify? |
|------|---------|:-------:|
| `elo_calibrated_params.json` | **FROZEN parameters: beta_elo=0.543593, seed, etc.** | NEVER |
| `model_freeze_manifest.json` | SHA256 hashes + conservation laws + top10 probs | NEVER |
| `teams.csv` | 29-column team data: Elo, analyst ratings, StatsBomb features | NO |
| `form_history.csv` | Last N competitive matches for 16 teams (code, result, date, opponent) | NO |
| `external/international_results/results.csv` | 49,450 match records (martj42) | NO |

---

## SIMULATION OUTPUTS (`outputs/tournament_run/`)

| File | Purpose | Modify? |
|------|---------|:-------:|
| `elo_calibrated_summary.csv` | **FROZEN: 100K simulation results, seed=20260609, beta=0.543593** | NEVER |
| `expert_summary.csv` | Expert model 100K simulation results | NO |
| `results.csv` | Raw simulation output | NO |

---

## CALIBRATION / AUDIT (`outputs/calibration/`)

| File | Purpose |
|------|---------|
| `ablation_results.csv` | **P2.5 ablation: 9 models × 4 temporal splits, NLL + ECE** |
| `ablation_summary.md` | Human-readable ablation summary |
| `elo_temperature_ablation.csv` | P3.5: 5 beta values × concentration metrics |
| `elo_calibration_gate.json` | P3.5: production gate verdict (PASS_WITH_TEMPERATURE) |
| `historical_tournament_concentration.csv` | "Sanity check": top-3 at beta=0.544 on WC2018/2022 Elo snapshots |
| `final_model_probability_jump_audit.md` | Why probabilities jumped: Expert vs Elo mathematical explanation |
| `final_model_probability_jump_audit.csv` | Per-team: expert_prob, elo_prob, delta, xG ratios |
| `significance_report.csv` | P-values for model comparison (variance=0.40 HARDCODED — approximate) |
| `calibration_curve.png` | Reliability diagram (ECE visualization) — NOT in public docs |
| `mle_params.json` | P1 pure MLE results (rejected model) |
| `hybrid_params.json` | P2 hybrid parameters |

---

## MEGA AUDIT (`outputs/audit/`)

| File | Purpose |
|------|---------|
| `mega_maturity_matrix.csv` | 62-item inventory: status/completion/risk (machine-readable) |
| `mega_maturity_matrix.md` | Same as above, markdown table |
| `global_maturity_score.md` | 14 dimensions, 5.25/10 global score, why not higher, what raises it |
| `global_maturity_score.json` | Machine-readable scores |
| `done_vs_fake_done.md` | 3 buckets: truly done / partially done / fake done |
| `model_selection_reaudit.md` | 5 publication options A→E compared |
| `wording_risk_report.md` | 9 risky claims + proposed fixes |
| `test_quality_audit.md` | 23% real tests; 10 new tests to add (with code) |
| `probability_output_audit.md` | Per-team defensibility, Wilson CIs, Expert vs Elo comparison |
| `probability_output_audit.csv` | Machine-readable per-team audit |
| `final_action_plan.md` | 4 buckets: MUST/SHOULD/COULD/DO NOT |

---

## PUBLIC OUTPUTS (`outputs/public/`)

| File | Purpose | Modify in P5? |
|------|---------|:-------------:|
| `model_selection_report.md` | Expert vs Elo comparison table (48 teams) + narrative | Minor wording |
| `technical_summary.md` | Technical audience summary | Minor wording |
| `linkedin_post.md` | Short post (~1950 chars) | YES — P5 items |
| `linkedin_post_long.md` | Long post (~3200 chars) | Optional |
| `claims_audit.md` | Every public number traced to source | NO |
| `claims_checklist.md` | Allowed/forbidden claims list | NO |
| `reproducibility_log.txt` | Output of reproduce_public_outputs.py | Regenerate after P5 |
| `wc2026_final_forecast_chart.png` | Top-12 bar chart (Elo-only) | Regenerate if wording in footer changes |
| `wc2026_model_comparison_chart.png` | Expert vs Elo side-by-side (recommended primary chart) | NO |

---

## ROOT PUBLICATION FILES

| File | Purpose | Modify in P5? |
|------|---------|:-------------:|
| `MODEL_CARD.md` | Comprehensive model documentation | YES — P5 items |
| `MODEL_FREEZE.md` | Frozen parameter record | Minor wording |
| `README.md` | Project README with full model narrative | Minor wording |

---

## TEST FILES (`tests/`)

| File | Tests | Purpose |
|------|------:|---------|
| `test_p4_publication_package.py` | 74 | Publication package: files, beta freeze, conservation laws, forbidden claims |
| `test_p35_elo_sanity.py` | 44 | Temperature ablation, concentration audit, Poisson math |
| `test_p3_elo_calibrated_production.py` | ~30 | Elo model production readiness |
| `test_p25_validation.py` | ~30 | P2.5 ablation validation |
| `test_p1_mle.py` | ~15 | MLE parameter tests |
| `test_tournament_smoke.py` | ~20 | End-to-end tournament smoke tests |
| `test_dixon_coles.py` | ~15 | DC correction unit tests |
| `test_p0_wiring.py` | ~20 | Expert model wiring |
| `test_group_rules.py` | ~15 | Group stage rules |
| `test_wave0.py` | ~25 | temporal_form module |
| Other test files | ~62 | Various: dashboard, pairwise, i18n, live state |

**Total: 350 passing. Run with `--ignore=tests/test_data_and_mapping.py` (that one has external data deps).**

---

## SESSION HANDOFF FILES (`session_handoff/`)

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT_LOCK.md` | **Master context: full phase history, all facts, all decisions** |
| `NEXT_SESSION_BOOT.md` | Tomorrow boot sequence + 10-line emergency summary |
| `STATE_VERIFICATION.md` | Verification commands + expected outputs |
| `NEXT_ACTION_PROMPT.md` | P5 wording fix details — DO NOT RUN without user GO |
| `FILE_INDEX.md` | This file |
| `ANTI_DRIFT_RULES.md` | Rules to prevent Claude from drifting or over-engineering |
| `HANDOFF_COMPLETE_CHECKLIST.md` | Checklist verifying handoff completeness |
