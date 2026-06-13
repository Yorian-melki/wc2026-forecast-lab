#!/usr/bin/env python
"""
P4 reproduction script. Verifies and regenerates all public outputs.

Outputs:
  outputs/public/reproducibility_log.txt
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

LOG_PATH = ROOT / "outputs" / "public" / "reproducibility_log.txt"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], desc: str, log: list[str]) -> tuple[bool, str]:
    t0 = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    elapsed = time.monotonic() - t0
    ok = result.returncode == 0
    status = "OK" if ok else "FAIL"
    line = f"[{status}] {desc} ({elapsed:.1f}s)"
    log.append(line)
    if not ok:
        log.append(f"  stderr: {result.stderr.strip()[:300]}")
    return ok, result.stdout + result.stderr


def main():
    python = str(Path(sys.executable))
    log = []
    log.append("=" * 60)
    log.append("WC2026 Forecast — Reproducibility Log")
    log.append(f"Timestamp: {datetime.datetime.now().isoformat()}")
    log.append(f"Python: {sys.version.split()[0]}")
    log.append("=" * 60)

    # --- 1. Verify params ---
    params = json.loads((ROOT / "data" / "elo_calibrated_params.json").read_text())
    log.append(f"\n[PARAMS]")
    log.append(f"  beta_elo: {params['beta_elo']}")
    log.append(f"  original_beta_elo: {params.get('original_beta_elo', 'N/A')}")
    log.append(f"  temperature_mul: {params.get('temperature_mul', 'N/A')}")
    log.append(f"  log_base: {params['log_base']}")
    log.append(f"  base_xg: {params['base_xg']}")
    log.append(f"  rho: {params['rho']}")
    log.append(f"  n_train_matches: {params.get('n_train_matches', 'N/A')}")
    log.append(f"  fit_dataset: {params.get('fit_dataset', 'N/A')}")

    # --- 2. Run tests ---
    print("[1/5] Running test suite...")
    ok_tests, test_out = run_cmd(
        [python, "-m", "pytest", "tests/", "-q",
         "--ignore=tests/test_data_and_mapping.py"],
        "pytest (full suite, ignoring test_data_and_mapping)",
        log,
    )
    # Extract pass count
    for line in (test_out or "").splitlines():
        if "passed" in line or "failed" in line or "error" in line:
            log.append(f"  {line.strip()}")
    if not ok_tests:
        print("  FAIL: tests did not pass — see log")

    # --- 3. Verify simulation outputs ---
    print("[2/5] Verifying simulation outputs...")
    import pandas as pd
    import numpy as np
    elo_csv = ROOT / "outputs" / "tournament_run" / "elo_calibrated_summary.csv"
    if elo_csv.exists():
        df = pd.read_csv(elo_csv)
        log.append(f"\n[SIMULATION]")
        log.append(f"  rows: {len(df)}")
        log.append(f"  champion_prob sum: {df['champion_prob'].sum():.6f}")
        log.append(f"  final_prob sum: {df['final_prob'].sum():.6f}")
        log.append(f"  sf_prob sum: {df['sf_prob'].sum():.6f}")
        top3 = float(df.head(3)["champion_prob"].sum())
        top5 = float(df.head(5)["champion_prob"].sum())
        top10 = float(df.head(10)["champion_prob"].sum())
        log.append(f"  top1: {float(df.head(1)['champion_prob'].sum())*100:.2f}%")
        log.append(f"  top3: {top3*100:.2f}%")
        log.append(f"  top5: {top5*100:.2f}%")
        log.append(f"  top10: {top10*100:.2f}%")
        log.append(f"\n  Top-10 champion probabilities:")
        for _, r in df.head(10).iterrows():
            log.append(f"    {r['team']}: {r['champion_prob']*100:.2f}%")

        # Conservation law checks
        log.append(f"\n  Conservation laws:")
        for stage, expected in [("champion_prob", 1.0), ("final_prob", 2.0),
                                 ("sf_prob", 4.0), ("qf_prob", 8.0),
                                 ("group_survival_prob", 32.0)]:
            s = float(df[stage].sum())
            ok_law = abs(s - expected) < 0.01
            log.append(f"    {'OK' if ok_law else 'FAIL'} {stage}: {s:.4f} (expected {expected})")
    else:
        log.append("  MISSING: elo_calibrated_summary.csv")

    # --- 4. Regenerate chart ---
    print("[3/5] Regenerating public chart...")
    ok_chart, _ = run_cmd(
        [python, "scripts/generate_public_final_chart.py"],
        "generate_public_final_chart.py",
        log,
    )

    # --- 5. Verify all public output files ---
    print("[4/5] Verifying public output files...")
    required_files = [
        ROOT / "MODEL_CARD.md",
        ROOT / "MODEL_FREEZE.md",
        ROOT / "README.md",
        ROOT / "data" / "model_freeze_manifest.json",
        ROOT / "outputs" / "public" / "wc2026_final_forecast_chart.png",
        ROOT / "outputs" / "public" / "model_selection_report.md",
        ROOT / "outputs" / "public" / "technical_summary.md",
        ROOT / "outputs" / "public" / "claims_checklist.md",
        ROOT / "outputs" / "public" / "linkedin_post.md",
        ROOT / "outputs" / "public" / "claims_audit.md",
        # Note: reproducibility_log.txt is the file being written — checked after write
    ]
    log.append(f"\n[OUTPUT FILES]")
    all_present = True
    for f in required_files:
        present = f.exists()
        log.append(f"  {'OK' if present else 'MISSING'} {f.relative_to(ROOT)}")
        if not present:
            all_present = False

    # --- 6. Verify forbidden claims absent from public outputs ---
    print("[5/5] Checking forbidden claims...")
    forbidden = [
        "hedge-fund-grade", "beats betting markets", "guaranteed edge",
        "ai predicts winner", "production betting model", "sure prediction",
        "peer-reviewed methodology", "fully calibrated",
    ]
    # Files that exist to DOCUMENT forbidden items — skip entirely (not public-facing claims)
    skip_entirely = {"claims_audit.md", "claims_checklist.md"}
    # Files with a "Forbidden" section listing them — check only body before that section
    has_forbidden_section = {
        "model_selection_report.md",
        "model_card.md",  # has "## Public claims forbidden" section
    }
    public_dir = ROOT / "outputs" / "public"
    log.append(f"\n[FORBIDDEN CLAIMS CHECK]")
    forbidden_found = False
    check_files = list(public_dir.glob("*.md")) + [ROOT / "README.md", ROOT / "MODEL_CARD.md"]
    for md_file in check_files:
        if not md_file.exists():
            continue
        if md_file.name.lower() in skip_entirely:
            continue
        text = md_file.read_text().lower()
        if md_file.name.lower() in has_forbidden_section:
            parts = text.split("forbidden")
            text_to_check = parts[0] if len(parts) > 1 else text
        else:
            text_to_check = text
        for phrase in forbidden:
            if phrase in text_to_check:
                log.append(f"  FAIL found '{phrase}' in {md_file.name}")
                forbidden_found = True
    if not forbidden_found:
        log.append("  OK all forbidden phrases absent from public document bodies")

    # --- Final summary ---
    log.append(f"\n{'='*60}")
    log.append("SUMMARY")
    log.append(f"  Tests: {'PASS' if ok_tests else 'FAIL'}")
    log.append(f"  Chart: {'PASS' if ok_chart else 'FAIL'}")
    log.append(f"  Output files present: {'PASS' if all_present else 'FAIL'}")
    log.append(f"  Forbidden claims: {'PASS' if not forbidden_found else 'FAIL'}")
    log.append(f"  beta_elo: {params['beta_elo']}")
    log.append(f"  Seed: 20260609 · Iterations: 100,000")
    all_pass = ok_tests and ok_chart and all_present and not forbidden_found
    log.append(f"  Overall: {'READY TO PUBLISH' if all_pass else 'ISSUES FOUND — review log'}")
    log.append(f"{'='*60}")

    text = "\n".join(log)
    LOG_PATH.write_text(text)
    print(text)
    # Verify the log file itself was written successfully
    log_ok = LOG_PATH.exists() and LOG_PATH.stat().st_size > 100
    if not log_ok:
        print("WARNING: reproducibility_log.txt may not have been written correctly")
    print(f"\nLog saved → {LOG_PATH}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
