# STATE VERIFICATION — WC2026 Forecast
# Run these commands at the start of the next session.
# Compare output to EXPECTED OUTPUT sections.
# If anything differs from expected: STOP and report to user before proceeding.

---

## COMMAND 1: Working directory

```bash
pwd
```

**EXPECTED:**
```
/Users/yorian/FinderProjects/wc2026_june2026
```

---

## COMMAND 2: No git (this is NOT a git repo)

```bash
ls -la | grep -E '\.git|session_handoff'
```

**EXPECTED:**
- `session_handoff/` directory exists
- No `.git/` directory (this is not a git repository)

---

## COMMAND 3: Frozen parameters

```bash
cat data/elo_calibrated_params.json | python3 -c "import json,sys; p=json.load(sys.stdin); print(f'beta_elo: {p[\"beta_elo\"]}'); print(f'original_beta_elo: {p[\"original_beta_elo\"]}'); print(f'temperature_mul: {p[\"temperature_mul\"]}'); print(f'seed note: {p[\"note\"][:60]}')"
```

**EXPECTED:**
```
beta_elo: 0.543593
original_beta_elo: 0.988351
temperature_mul: 0.55
seed note: P3.5 temperature-corrected. Original beta_elo=0.988 over-conc
```

**If beta_elo ≠ 0.543593: STOP. Something modified the frozen parameter. Do not proceed.**

---

## COMMAND 4: Audit files exist

```bash
ls outputs/audit/
```

**EXPECTED (10 files):**
```
done_vs_fake_done.md
final_action_plan.md
global_maturity_score.json
global_maturity_score.md
mega_maturity_matrix.csv
mega_maturity_matrix.md
model_selection_reaudit.md
probability_output_audit.csv
probability_output_audit.md
test_quality_audit.md
wording_risk_report.md
```

---

## COMMAND 5: Session handoff files exist

```bash
ls session_handoff/
```

**EXPECTED (7 files):**
```
ANTI_DRIFT_RULES.md
FILE_INDEX.md
HANDOFF_COMPLETE_CHECKLIST.md
NEXT_ACTION_PROMPT.md
NEXT_SESSION_BOOT.md
PROJECT_CONTEXT_LOCK.md
STATE_VERIFICATION.md
```

---

## COMMAND 6: Public output files exist

```bash
ls outputs/public/
```

**EXPECTED:**
```
claims_audit.md
claims_checklist.md
linkedin_post.md
linkedin_post_long.md
model_selection_report.md
reproducibility_log.txt
technical_summary.md
wc2026_final_forecast_chart.png
wc2026_model_comparison_chart.png
```

---

## COMMAND 7: Core publication files exist

```bash
ls MODEL_CARD.md MODEL_FREEZE.md README.md data/model_freeze_manifest.json data/elo_calibrated_params.json
```

**EXPECTED:** All 5 files listed without error.

---

## COMMAND 8: Simulation output

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('outputs/tournament_run/elo_calibrated_summary.csv')
print(f'Rows: {len(df)}')
print(f'champion_prob sum: {df[\"champion_prob\"].sum():.6f}')
print(f'top3: {df.head(3)[\"champion_prob\"].sum()*100:.2f}%')
top3 = df.head(3)
for _, r in top3.iterrows():
    print(f'  {r[\"team\"]}: {r[\"champion_prob\"]*100:.2f}%')
"
```

**EXPECTED:**
```
Rows: 48
champion_prob sum: 1.000000
top3: 41.76%
  ESP: 16.97%
  ARG: 14.76%
  FRA: 10.03%
```

**If top3 ≠ 41.76% or ESP ≠ 16.97%: STOP. Simulation was regenerated. Do not proceed.**

---

## COMMAND 9: Full test suite

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q --ignore=tests/test_data_and_mapping.py
```

**EXPECTED:**
```
350 passed in 14.XXs
```

**If tests fail: report which tests fail and WAIT for user instruction before investigating or fixing.**

---

## COMMAND 10: Calibration files

```bash
ls outputs/calibration/
```

**EXPECTED (at minimum):**
```
ablation_results.csv
elo_calibration_gate.json
elo_temperature_ablation.csv
final_model_probability_jump_audit.csv
final_model_probability_jump_audit.md
historical_tournament_concentration.csv
significance_report.csv
```

---

## VERIFICATION SUMMARY TABLE

After running all commands, fill this in:

| Check | Expected | Actual | Pass/Fail |
|-------|----------|--------|:---------:|
| Working directory | `/Users/yorian/FinderProjects/wc2026_june2026` | ? | ? |
| beta_elo | 0.543593 | ? | ? |
| original_beta_elo | 0.988351 | ? | ? |
| temperature_mul | 0.55 | ? | ? |
| Audit files count | 10 | ? | ? |
| Handoff files count | 7 | ? | ? |
| ESP champion prob | 16.97% | ? | ? |
| top3 concentration | 41.76% | ? | ? |
| Tests passing | 350 | ? | ? |
| Conservation law | 1.000000 | ? | ? |

**If all 10 checks pass: context is intact. Proceed to NEXT_ACTION_PROMPT.md.**  
**If any check fails: STOP. Report to user. Do not proceed.**

---

## NO-GIT NOTE

This repository has no git history. There is no `git log`, no `git diff`, no `git blame`.  
All history is in these handoff files and the phase documentation in PROJECT_CONTEXT_LOCK.md.  
Do not attempt git commands.
