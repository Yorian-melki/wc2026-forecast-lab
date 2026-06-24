#!/usr/bin/env python3
"""Immutable scorecard metric audit (Phase 1B).

READ-ONLY measurement layer. Recomputes the full set of forecast-vs-reality metrics from completed
matches using the EXISTING model + scorecard.score_match() (imported, not modified), and writes an
immutable timestamped snapshot to outputs/audit/live_metric_snapshots/. It never writes to data/,
configs/, or any model/forecast file — it only measures.

Metrics: 1X2 accuracy, RPS (+ uniform baseline), multiclass Brier, NLL, exact-score top-1/3/5/10,
average rank of the real score, 3x3 confusion matrix, draw recall + draw-probability calibration
buckets, blowout report (total>=5 or margin>=3), and average rank by total-goals bucket.

    python scripts/audit_live_scorecard.py [--input matches.csv] [--no-write]

CSV input (optional) needs columns: home, away, home_goals, away_goals[, group].
Default source: data/wc2026_live.json completed_matches.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

LIVE_JSON = ROOT / "data" / "wc2026_live.json"
SNAP_DIR = ROOT / "outputs" / "audit" / "live_metric_snapshots"


def _load_completed(input_csv: str | None, live: bool = False) -> list[dict]:
    if live:
        # the full current scorecard set (~48), assembled at runtime from the live provider feed.
        # Read-only: fetch_live_state() only fetches; it does not persist or modify any file.
        from wc2026.live_engine import fetch_live_state
        st = fetch_live_state()
        return [m for m in st.get("all_completed", []) if m.get("home_goals") is not None]
    if input_csv:
        rows = []
        with open(input_csv, newline="") as f:
            for r in csv.DictReader(f):
                try:
                    rows.append({
                        "home": r["home"], "away": r["away"],
                        "home_goals": int(r["home_goals"]), "away_goals": int(r["away_goals"]),
                        "group": r.get("group", "") or "",
                    })
                except (KeyError, ValueError):
                    continue
        return rows
    data = json.loads(LIVE_JSON.read_text())
    return [m for m in data.get("completed_matches", []) if m.get("home_goals") is not None]


def compute_audit(completed: list[dict], model=None, teams=None) -> dict:
    """Pure, deterministic metric computation. Reuses scorecard.score_match (read-only)."""
    import numpy as np
    from wc2026.scorecard import score_match, get_model_and_teams
    if model is None or teams is None:
        model, teams = get_model_and_teams()

    rows = []
    for m in completed:
        if m.get("home_goals") is None:
            continue
        r = score_match(model, teams, m["home"], m["away"],
                        int(m["home_goals"]), int(m["away_goals"]), knockout=not m.get("group"))
        if not r:
            continue
        hg, ag = int(m["home_goals"]), int(m["away_goals"])
        out = 0 if hg > ag else (1 if hg == ag else 2)
        pw = (r["p_wdl"]["home"], r["p_wdl"]["draw"], r["p_wdl"]["away"])
        rows.append({"rank": r["rank"], "p_actual": r["p_actual"], "ok": int(r["outcome_ok"]),
                     "rps": r["rps"], "rps_u": r["rps_uniform"], "pred": int(np.argmax(pw)),
                     "out": out, "pw": pw, "total": hg + ag, "margin": abs(hg - ag)})
    n = len(rows)
    if not n:
        return {"n_matches": 0, "note": "no completed matches"}

    def mean(key):
        return round(float(np.mean([r[key] for r in rows])), 4)

    # confusion 3x3 [predicted][actual]
    conf = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for r in rows:
        conf[r["pred"]][r["out"]] += 1
    # draw calibration buckets on predicted P(draw)
    buckets = {}
    for r in rows:
        b = min(int(r["pw"][1] * 10), 9)
        buckets.setdefault(b, []).append(r)
    draw_cal = [{"bucket": f"{b/10:.1f}-{(b+1)/10:.1f}", "n": len(v),
                 "pred_draw_mean": round(float(np.mean([x["pw"][1] for x in v])), 4),
                 "actual_draw_rate": round(sum(x["out"] == 1 for x in v) / len(v), 4)}
                for b, v in sorted(buckets.items())]
    n_draws = sum(r["out"] == 1 for r in rows)
    draw_recall = round(sum(r["out"] == 1 and r["pred"] == 1 for r in rows) / n_draws, 4) if n_draws else None
    # blowout report
    blow = [r for r in rows if r["total"] >= 5 or r["margin"] >= 3]
    blow_report = {"n": len(blow),
                   "mean_rank": round(float(np.mean([r["rank"] for r in blow])), 2) if blow else None,
                   "mean_p_actual": round(float(np.mean([r["p_actual"] for r in blow])), 4) if blow else None,
                   "top10_coverage": round(sum(r["rank"] <= 10 for r in blow) / len(blow), 4) if blow else None}
    # rank by total-goals bucket
    def bucket_total(t):
        return "0-1" if t <= 1 else ("2-3" if t <= 3 else ("4" if t == 4 else "5+"))
    rbb = {}
    for r in rows:
        rbb.setdefault(bucket_total(r["total"]), []).append(r["rank"])
    rank_by_total = {k: {"n": len(v), "mean_rank": round(float(np.mean(v)), 2)} for k, v in sorted(rbb.items())}

    # NLL / Brier on the W/D/L distribution
    nll = round(float(np.mean([-math.log(max(r["pw"][r["out"]], 1e-9)) for r in rows])), 4)
    brier = round(float(np.mean([sum((r["pw"][c] - (1.0 if c == r["out"] else 0.0)) ** 2 for c in range(3))
                                 for r in rows])), 4)

    return {
        "n_matches": n,
        "outcome_accuracy": round(sum(r["ok"] for r in rows) / n, 4),
        "rps": mean("rps"), "rps_uniform_baseline": mean("rps_u"),
        "brier_wdl": brier, "nll_wdl": nll,
        "exact_top1": round(sum(r["rank"] == 1 for r in rows) / n, 4),
        "exact_top3": round(sum(r["rank"] <= 3 for r in rows) / n, 4),
        "exact_top5": round(sum(r["rank"] <= 5 for r in rows) / n, 4),
        "exact_top10": round(sum(r["rank"] <= 10 for r in rows) / n, 4),
        "avg_rank_real_score": mean("rank"),
        "mean_prob_actual_score": mean("p_actual"),
        "confusion_matrix_pred_x_actual": {"order": ["home", "draw", "away"], "counts": conf},
        "draw_recall": draw_recall, "n_actual_draws": n_draws,
        "draw_calibration": draw_cal,
        "blowout_report": blow_report,
        "rank_by_total_goals": rank_by_total,
    }


def _to_markdown(a: dict, meta: dict) -> str:
    if a.get("n_matches", 0) == 0:
        return f"# Scorecard audit — {meta['generated_at']}\n\nNo completed matches.\n"
    L = [f"# Scorecard metric audit — {meta['generated_at']}",
         f"\nSource: `{meta['source']}` · model `{meta['model_version']}` · **{a['n_matches']} matches**\n",
         "| metric | value |", "|---|---|",
         f"| Outcome accuracy | {a['outcome_accuracy']:.1%} |",
         f"| RPS (model) | {a['rps']} |", f"| RPS (coin-flip) | {a['rps_uniform_baseline']} |",
         f"| Brier (W/D/L) | {a['brier_wdl']} | ", f"| NLL (W/D/L) | {a['nll_wdl']} |",
         f"| Exact top-1 / top-3 / top-5 / top-10 | {a['exact_top1']:.1%} / {a['exact_top3']:.1%} / {a['exact_top5']:.1%} / {a['exact_top10']:.1%} |",
         f"| Avg rank of real score | {a['avg_rank_real_score']} |",
         f"| Draw recall ({a['n_actual_draws']} draws) | {a['draw_recall']} |",
         f"| Blowouts (≥5 or margin≥3) | n={a['blowout_report']['n']}, mean rank {a['blowout_report']['mean_rank']} |",
         "\n## Confusion (rows=predicted, cols=actual: home/draw/away)"]
    for i, lbl in enumerate(["home", "draw", "away"]):
        L.append(f"- pred {lbl}: {a['confusion_matrix_pred_x_actual']['counts'][i]}")
    L.append("\n## Avg rank by total goals")
    for k, v in a["rank_by_total_goals"].items():
        L.append(f"- {k} goals: n={v['n']}, mean rank {v['mean_rank']}")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="optional CSV (home,away,home_goals,away_goals[,group])")
    ap.add_argument("--live", action="store_true", help="source the full current completed set from the live feed (fetch_live_state, ~48 matches)")
    ap.add_argument("--no-write", action="store_true", help="compute + print only, write no snapshot")
    args = ap.parse_args(argv)

    completed = _load_completed(args.input, live=args.live)
    audit = compute_audit(completed)
    try:
        mv = json.loads((ROOT / "configs" / "model_version.json").read_text()).get("model_version", "?")
    except Exception:
        mv = "?"
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": ("live:fetch_live_state().all_completed" if args.live
                       else (args.input or "data/wc2026_live.json:completed_matches")),
            "model_version": mv}
    snapshot = {"meta": meta, "metrics": audit}

    print(json.dumps(audit, indent=2)[:1200])
    if not args.no_write and audit.get("n_matches", 0) > 0:
        SNAP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
        (SNAP_DIR / f"{stamp}.json").write_text(json.dumps(snapshot, indent=2))
        (SNAP_DIR / f"{stamp}.md").write_text(_to_markdown(audit, meta))
        print(f"\nsnapshot → outputs/audit/live_metric_snapshots/{stamp}.json (+ .md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
