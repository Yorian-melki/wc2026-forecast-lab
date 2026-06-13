#!/usr/bin/env python3
"""Phase 7 — train + gate the ML 1X2 match model. Honest accept/reject.

Leak-free temporal split: train on matches <= 2018-12-31, test on 2019-2022.
Baselines: Elo-only (same elo_diff feature) and random. Hard gate: ML must beat
Elo-only on BOTH held-out Brier and NLL, else REJECTED.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from wc2026.calibration.international_dataset import build_clean_dataset
from wc2026.ml.features import build_leakfree_features, FEATURE_COLS
from wc2026.ml.train_match_model import train_and_gate

OUT_AUDIT = ROOT / "outputs" / "audit"
OUT_MODELS = ROOT / "outputs" / "models"
OUT_MODELS.mkdir(parents=True, exist_ok=True)


def main():
    t0 = time.monotonic()
    NOW = datetime.now(timezone.utc).isoformat()

    print("Building dataset 1990-2025 ...")
    df, _ = build_clean_dataset(min_year=1990, max_year=2025)
    print(f"  matches: {len(df)}")

    print("Building leak-free rolling-Elo features ...")
    feat = build_leakfree_features(df)

    # Temporal split (leak-free): train <= 2018, test 2019-2022
    train = feat[feat["date"] <= "2018-12-31"]
    test = feat[(feat["date"] >= "2019-01-01") & (feat["date"] <= "2022-12-31")]
    print(f"  train: {len(train)}  test: {len(test)}")

    result, clf, iso = train_and_gate(train, test)

    print("\n=== Held-out results (test 2019-2022) ===")
    print(f"  random   : Brier {result.random['brier']}  NLL {result.random['nll']}  ECE {result.random['ece']}")
    print(f"  elo-only : Brier {result.elo_only['brier']}  NLL {result.elo_only['nll']}  ECE {result.elo_only['ece']}")
    print(f"  ML       : Brier {result.ml['brier']}  NLL {result.ml['nll']}  ECE {result.ml['ece']}")
    if result.ml_calibrated:
        print(f"  ML+isoCal: Brier {result.ml_calibrated['brier']}  NLL {result.ml_calibrated['nll']}  ECE {result.ml_calibrated['ece']}")
    print(f"\n  GATE: {'ACCEPTED' if result.accepted else 'REJECTED'} — {result.reason}")

    # Calibration verdict
    cal_helps = (result.ml_calibrated is not None
                 and result.ml_calibrated["ece"] < result.ml["ece"])

    report = {
        "generated_at": NOW,
        "split": "train<=2018-12-31, test 2019-2022 (leak-free temporal)",
        "n_train": len(train), "n_test": len(test),
        "features": FEATURE_COLS,
        "model": "multinomial LogisticRegression (sklearn 1.9, C=1.0)",
        "metrics": {
            "random": result.random,
            "elo_only": result.elo_only,
            "ml": result.ml,
            "ml_isotonic_calibrated": result.ml_calibrated,
        },
        "gate": {
            "accepted": result.accepted,
            "reason": result.reason,
            "rule": "ML must beat Elo-only on BOTH held-out Brier and NLL",
        },
        "calibration": {
            "isotonic_reduces_ece": bool(cal_helps),
            "decision": "apply isotonic" if cal_helps else "reject isotonic (no ECE gain)",
        },
        "honest_notes": [
            "Elo-only baseline uses the SAME pre-match elo_diff feature -> fair test of learned vs hand-set mapping.",
            "Features are intentionally lean (elo_diff, neutral) to avoid overfitting.",
            "Test set is strictly after train -> no temporal leakage.",
            "This validates a single-match 1X2 model, NOT the tournament Monte Carlo directly.",
        ],
    }
    OUT_AUDIT.joinpath("ml_validation_report.md").write_text(
        f"# ML Validation Report (Phase 7)\n\n"
        f"Generated: {NOW[:19]} · split: train≤2018, test 2019-2022 (leak-free)\n"
        f"Features: {FEATURE_COLS} · model: multinomial logistic regression\n\n"
        f"| Model | Brier | NLL | ECE | Acc | n |\n|---|---|---|---|---|---|\n"
        f"| random | {result.random['brier']} | {result.random['nll']} | {result.random['ece']} | {result.random['accuracy']} | {result.random['n']} |\n"
        f"| Elo-only | {result.elo_only['brier']} | {result.elo_only['nll']} | {result.elo_only['ece']} | {result.elo_only['accuracy']} | {result.elo_only['n']} |\n"
        f"| **ML** | {result.ml['brier']} | {result.ml['nll']} | {result.ml['ece']} | {result.ml['accuracy']} | {result.ml['n']} |\n"
        + (f"| ML+isotonic | {result.ml_calibrated['brier']} | {result.ml_calibrated['nll']} | {result.ml_calibrated['ece']} | {result.ml_calibrated['accuracy']} | {result.ml_calibrated['n']} |\n" if result.ml_calibrated else "")
        + f"\n## Gate: **{'ACCEPTED' if result.accepted else 'REJECTED'}**\n{result.reason}\n\n"
        f"## Calibration\nIsotonic reduces ECE: **{cal_helps}** → {report['calibration']['decision']}\n\n"
        f"## Honest notes\n" + "\n".join(f"- {x}" for x in report["honest_notes"]) + "\n"
    )
    OUT_AUDIT.joinpath("ml_validation_report.json").write_text(json.dumps(report, indent=2))

    # Model card
    OUT_AUDIT.joinpath("ml_model_card.md").write_text(
        f"# ML Model Card — WC2026 1X2 match model\n\n"
        f"- **Type**: multinomial logistic regression (sklearn 1.9.0)\n"
        f"- **Features**: pre-match rolling-Elo diff (incl. home adv), neutral flag\n"
        f"- **Training data**: martj42 international results 1990–2018 ({len(train)} matches)\n"
        f"- **Validation**: held-out 2019–2022 ({len(test)} matches), leak-free temporal split\n"
        f"- **Baseline**: Elo-only formula on the same elo_diff\n"
        f"- **Gate result**: {'ACCEPTED' if result.accepted else 'REJECTED'}\n"
        f"- **Intended use**: single-match 1X2 probabilities; NOT a tournament simulator replacement\n"
        f"- **Limitations**: 2 features only; no xG/lineup/rest-day features (avoided leakage & overfit); "
        f"does not model goal counts; tournament sim still uses CalibratedEloMatchModel\n"
        f"- **Ethical/▸honesty**: not 'xG-calibrated'; not 'validated' beyond the stated temporal split\n"
    )

    # Model stack config — controls whether ML is wired in (rollback-safe)
    stack = {
        "generated_at": NOW,
        "use_xg_live_adjustment": True,
        "use_ml_match_model": bool(result.accepted),
        "use_isotonic_calibrator": bool(cal_helps and result.accepted),
        "ensemble": {
            "elo_calibrated_weight": 1.0 if not result.accepted else 0.5,
            "ml_logistic_weight": 0.0 if not result.accepted else 0.5,
        },
        "rollback_to_score_only": True,
        "notes": "use_ml_match_model is driven purely by the held-out gate. If False, the tournament "
                 "sim is unchanged (CalibratedEloMatchModel only). Flip requires a passing gate.",
    }
    (ROOT / "data" / "model_stack_config.json").write_text(json.dumps(stack, indent=2))

    # Persist model only if accepted
    if result.accepted:
        import pickle
        with open(OUT_MODELS / "ml_match_model.pkl", "wb") as f:
            pickle.dump(clf, f)
        if cal_helps and iso is not None:
            with open(OUT_MODELS / "calibrator.pkl", "wb") as f:
                pickle.dump(iso, f)
        print("  Model persisted (gate passed).")
    else:
        print("  Model NOT persisted (gate failed) — ML rejected, stack unchanged.")

    print(f"\nDone in {time.monotonic()-t0:.1f}s")
    print(f"use_ml_match_model = {stack['use_ml_match_model']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
