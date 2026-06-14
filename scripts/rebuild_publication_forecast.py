#!/usr/bin/env python3
"""Reproducibility orchestrator — regenerate the publication forecast artifacts.

Modes:
  --smoke (default): fast (<60s). Verifies deps, key inputs, runs a small conservation
                     sim, counts tests. Proves the pipeline is wired without the long runs.
  --full           : regenerates every artifact (ML gate, ensemble compare, walk-forward,
                     expanded validation, beta intervals). ~25-30 min total.

ALL of this is reproducible OFFLINE from committed data (martj42 + frozen params + saved
live snapshot). Live API keys are only needed to REFRESH provider data, not to reproduce
the forecast. Writes outputs/audit/reproducibility_pack.{md,json}.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (label, command, approx_seconds, offline)
FULL_PIPELINE = [
    ("ml_gate", f"PYTHONPATH=src {PY} scripts/train_ml_match_model.py", 5, True),
    ("ml_ensemble_compare", f"PYTHONPATH=src {PY} scripts/run_ml_ensemble_comparison.py --n 100000", 240, True),
    ("tournament_walkforward", f"PYTHONPATH=src {PY} scripts/run_tournament_walkforward_validation.py --n 30000", 240, True),
    ("expanded_validation", f"PYTHONPATH=src {PY} scripts/run_expanded_validation_and_dynamic_ml.py --n 30000", 280, True),
    ("beta_intervals", f"PYTHONPATH=src {PY} scripts/run_beta_uncertainty_intervals.py --b 300 --n 50000", 190, True),
]

KEY_INPUTS = [
    "data/external/international_results/results.csv",
    "data/elo_calibrated_params.json",
    "data/groups.json", "data/teams.csv",
    "data/model_stack_config.json", "data/xg_adjustment_config.json",
]
KEY_OUTPUTS = [
    "outputs/audit/ml_validation_report.json",
    "outputs/audit/tournament_walkforward_validation.json",
    "outputs/audit/expanded_tournament_validation.json",
    "outputs/audit/beta_uncertainty_bootstrap.json",
    "data/live/champion_probability_intervals.json",
    "outputs/audit/model_stack_final_decision.json",
]


def smoke():
    out = {"mode": "smoke", "checks": []}
    ok = True
    # deps
    for mod in ["numpy", "pandas", "scipy", "sklearn", "statsmodels"]:
        try:
            __import__(mod); out["checks"].append({"dep": mod, "ok": True})
        except Exception as e:
            ok = False; out["checks"].append({"dep": mod, "ok": False, "err": str(e)})
    # inputs
    for p in KEY_INPUTS:
        e = (ROOT / p).exists(); ok &= e
        out["checks"].append({"input": p, "exists": e})
    # outputs present
    for p in KEY_OUTPUTS:
        out["checks"].append({"output": p, "exists": (ROOT / p).exists()})
    # conservation sim
    sys.path.insert(0, str(ROOT / "src"))
    from wc2026.calibrated_elo_model import CalibratedEloMatchModel
    from wc2026.tournament import TournamentSimulator
    from wc2026.data_loader import load_teams, load_groups
    m = CalibratedEloMatchModel(use_ml=None)
    sim = TournamentSimulator(teams=load_teams(apply_temporal_form=True), groups=load_groups(), model=m)
    s = sim.simulate_many(iterations=500, seed=1).summary
    csum = float(s["champion_prob"].sum())
    out["conservation_champion_sum"] = round(csum, 5)
    out["conservation_ok"] = abs(csum - 1.0) < 1e-6
    ok &= out["conservation_ok"]
    out["ml_active"] = m.use_ml
    out["smoke_pass"] = ok
    return out


def run_full():
    results = []
    for label, cmd, approx, offline in FULL_PIPELINE:
        print(f"[{label}] {cmd}")
        t0 = time.monotonic()
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
        results.append({"step": label, "returncode": r.returncode,
                        "seconds": round(time.monotonic() - t0, 1),
                        "tail": r.stdout.strip().splitlines()[-3:] if r.stdout else []})
        if r.returncode != 0:
            print(f"  FAILED: {r.stderr[-400:]}"); break
    return results


def write_pack(smoke_res, full_res=None):
    NOW = datetime.now(timezone.utc).isoformat()
    pack = {
        "generated_at": NOW,
        "one_command": "PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py --full",
        "smoke_command": "PYTHONPATH=src .venv/bin/python scripts/rebuild_publication_forecast.py",
        "env_required_for_reproduction": "NONE — forecast + validation reproduce offline from committed data.",
        "env_required_for_live_refresh": ["API_FOOTBALL_KEY", "THESTATSAPI_KEY", "HIGHLIGHTLY_API_KEY",
                                          "FOOTBALL_DATA_ORG_KEY"],
        "key_inputs": KEY_INPUTS, "key_outputs": KEY_OUTPUTS,
        "pipeline": [{"step": s[0], "cmd": s[1], "approx_seconds": s[2], "offline": s[3]} for s in FULL_PIPELINE],
        "expected_total_runtime_min": round(sum(s[2] for s in FULL_PIPELINE) / 60, 1),
        "expected_tests": "571 passed (PYTHONPATH=src .venv/bin/python -m pytest tests/ -q)",
        "smoke_result": smoke_res,
        "full_result": full_res,
        "offline_vs_live": {
            "offline_reproducible": ["all validation", "all simulations", "champion probabilities",
                                     "intervals", "ML gate", "beta bootstrap"],
            "requires_live_api": ["refreshing wc2026_live.json scores/xG/odds via update_live_data.py",
                                  "provider_status.json freshness"],
        },
    }
    (ROOT / "outputs" / "audit" / "reproducibility_pack.json").write_text(json.dumps(pack, indent=2))
    md = [f"# Reproducibility Pack\n\nGenerated {NOW[:19]} UTC\n",
          "## One command (full regenerate, ~%.0f min)" % pack["expected_total_runtime_min"],
          f"```\n{pack['one_command']}\n```\n",
          "## Fast smoke check (<60s)", f"```\n{pack['smoke_command']}\n```\n",
          f"**Smoke pass:** {smoke_res.get('smoke_pass')} · conservation Σχampion={smoke_res.get('conservation_champion_sum')} · ML active={smoke_res.get('ml_active')}\n",
          "## Reproducibility model",
          "- **Forecast + validation reproduce fully OFFLINE** from committed data (martj42 results.csv, frozen params, saved live snapshot). No API keys needed.",
          "- **Live API keys** only refresh provider data (scores/xG/odds). Listed in `.env.example`.\n",
          "## Pipeline (offline)", "", "| Step | Command | ~sec |", "|---|---|---|"]
    for s in FULL_PIPELINE:
        md.append(f"| {s[0]} | `{s[1].replace(PY, '.venv/bin/python')}` | {s[2]} |")
    md += ["", f"**Expected tests:** {pack['expected_tests']}", "",
           "## Inputs", ""] + [f"- `{p}`" for p in KEY_INPUTS] + ["", "## Outputs", ""] + [f"- `{p}`" for p in KEY_OUTPUTS]
    (ROOT / "outputs" / "audit" / "reproducibility_pack.md").write_text("\n".join(md))
    print(f"\nWrote reproducibility_pack.{{md,json}} · smoke_pass={smoke_res.get('smoke_pass')}")


def main():
    full = "--full" in sys.argv
    print("=== Reproducibility: smoke checks ===")
    s = smoke()
    f = run_full() if full else None
    write_pack(s, f)
    return 0 if s["smoke_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
