"""Phase 3K — OFFLINE champion-safe market-blend policy lab (READ-ONLY, no API).

Develops + validates the re-temper policy from Phase 3J: blend (alpha) then temper (S) so the match-level
gain is preserved while champion concentration stays in band. Grids alpha x S, evaluates BOTH levels
(match-level proper scores on the 356 real fixtures; champion concentration on the synthetic bracket from
3J), and selects conservative / balanced / aggressive safe policies.

Reuses Phase 3J bracket machinery (import) + Phase 3I/3K blend+temperature modules. No production change.
Run:  PYTHONPATH=src .venv/bin/python scripts/research/champion_safe_blend_policy.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "research" / "phase_3k_champion_safe_blend"
sys.path.insert(0, str(ROOT / "scripts" / "research"))

# Phase 3J bracket machinery (no API; safe to import)
from champion_market_guardrail import (  # noqa: E402
    WDLFromElo, make_bracket_elos, pairwise, sim_tournament, metrics, fit_T, powersharpen,
    production_and_market_356,
)
from wc2026.experimental.market_blend import blend_wdl  # noqa: E402
from wc2026.experimental.market_temperature import champion_safe_blend, fit_temperature_to_conf, mean_confidence  # noqa: E402

ALPHAS = [0.25, 0.40, 0.60]
SCALAR_S = [0.70, 0.80, 0.90]
N_SIMS = 15000
SEED = 20260625

# champion-safety thresholds (stricter than 3J's "material-detection"; for policy SELECTION)
TOP3_TOL, ENT_TOL, TOP1_TOL = 0.02, 0.10, 0.02


def rps_rows(P, y):
    o = np.zeros_like(P); o[np.arange(len(y)), y] = 1.0
    return np.sum((np.cumsum(P, 1) - np.cumsum(o, 1)) ** 2, axis=1) / 2.0


def nll_rows(P, y):
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def ece(P, y, bins=10):
    conf = P.max(1); corr = (P.argmax(1) == y); e = 0.0
    for lo in np.linspace(0, 1, bins + 1)[:-1]:
        m = (conf >= lo) & (conf < lo + 1 / bins)
        if m.any():
            e += m.mean() * abs(corr[m].mean() - conf[m].mean())
    return float(e)


def boot_lt0(a, b):
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(SEED)
    bs = d[rng.integers(0, len(d), size=(4000, len(d)))].mean(1)
    hi = float(np.percentile(bs, 97.5))
    return float(d.mean()), hi, hi < 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wdlfn = WDLFromElo()
    prod, mkt, y = production_and_market_356(wdlfn)
    T = fit_T(prod)
    base_conf = mean_confidence(prod)
    rps_prod = float(rps_rows(prod, y).mean())
    rps_market = float(rps_rows(mkt, y).mean())
    print(f"prod conf {base_conf:.3f} · RPS prod {rps_prod:.4f} · market {rps_market:.4f} · T={T:.3f}")

    codes, elos, groups = make_bracket_elos()
    rng = np.random.default_rng(SEED)

    def champ_metrics(alpha, S):
        M = pairwise(codes, elos, wdlfn, T, alpha, retemper_S=(None if S == 1.0 else S))
        counts = {}
        for _ in range(N_SIMS):
            c = sim_tournament(codes, groups, M, rng)
            counts[c] = counts.get(c, 0) + 1
        return metrics(counts, N_SIMS)

    base_champ = champ_metrics(0.0, 1.0)

    rows = []
    for alpha in ALPHAS:
        naive = blend_wdl(prod, mkt, alpha)
        rps_naive = float(rps_rows(naive, y).mean())
        # S modes: none(1.0), match-confidence-restore, scalar grid
        s_match = fit_temperature_to_conf(naive, base_conf)
        modes = [("none", 1.0), ("match_conf_restore", round(s_match, 3))] + [(f"S={s}", s) for s in SCALAR_S]
        for label, S in modes:
            Q = champion_safe_blend(prod, mkt, alpha, S)
            d_rps, ci_hi, beats = boot_lt0(rps_rows(Q, y), rps_rows(prod, y))
            gain_retained = (rps_prod - float(rps_rows(Q, y).mean())) / (rps_prod - rps_naive) if rps_prod != rps_naive else 0.0
            cm = champ_metrics(alpha, S)
            d_top3 = cm["top3_share"] - base_champ["top3_share"]
            d_ent = base_champ["entropy_bits"] - cm["entropy_bits"]
            d_top1 = cm["top1"] - base_champ["top1"]
            champ_safe = (d_top3 <= TOP3_TOL and d_ent <= ENT_TOL and d_top1 <= TOP1_TOL)
            passes = beats and champ_safe and alpha <= 0.6
            rows.append({
                "alpha": alpha, "S_mode": label, "S": S,
                "match_rps": round(float(rps_rows(Q, y).mean()), 4), "match_nll": round(float(nll_rows(Q, y).mean()), 4),
                "match_ece": round(ece(Q, y), 4), "match_acc": round(float((Q.argmax(1) == y).mean()), 3),
                "drps_vs_prod": round(d_rps, 4), "rps_beats_prod": beats, "gain_retained_vs_naive": round(gain_retained, 3),
                "champ_top1": cm["top1"], "champ_top3": cm["top3_share"], "champ_entropy": cm["entropy_bits"],
                "champ_n_ge1pct": cm["n_teams_ge_1pct"], "d_top3": round(d_top3, 4), "d_entropy": round(d_ent, 3),
                "champion_safe": champ_safe, "PASS": passes})

    # candidate selection among PASS rows
    pas = [r for r in rows if r["PASS"]]
    def pick(subset):
        return min(subset, key=lambda r: r["match_rps"]) if subset else None
    conservative = pick([r for r in pas if r["alpha"] == 0.25])
    balanced = pick([r for r in pas if r["alpha"] == 0.40])
    aggressive = pick([r for r in pas if r["alpha"] == 0.60])

    report = {
        "method": "alpha x S grid; match-level on 356 real fixtures; champion on synthetic bracket (3J proxy, "
                  "T-fit). PROXY assumptions => stays MODEL-LAB-ONLY.",
        "baseline": {"prod_conf": round(base_conf, 3), "rps_prod": round(rps_prod, 4), "rps_market": round(rps_market, 4),
                     "champ_top3": base_champ["top3_share"], "champ_entropy": base_champ["entropy_bits"],
                     "champ_n_ge1pct": base_champ["n_teams_ge_1pct"]},
        "thresholds": {"champ_top3_max_increase": TOP3_TOL, "champ_entropy_max_drop": ENT_TOL, "champ_top1_max_increase": TOP1_TOL,
                       "match": "RPS beats production beyond bootstrap noise"},
        "n_pass": len(pas), "grid": rows,
        "candidates": {"conservative": conservative, "balanced": balanced, "aggressive": aggressive},
        "live_data_needed_before_shadow": [
            "real per-matchup pre-match 1X2 odds for an actual resolving bracket (not a sharpening proxy)",
            "real champion-Brier vs the actual champion as the bracket resolves",
            "re-tuning S on real data + on the exact 48-team WC2026 format"],
    }
    (OUT / "champion_safe_policy_report.json").write_text(json.dumps(report, indent=2, default=str))
    with (OUT / "champion_safe_policy_grid.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    print(f"\nbaseline champ top3 {base_champ['top3_share']:.3f} entropy {base_champ['entropy_bits']:.2f} "
          f"#>=1% {base_champ['n_teams_ge_1pct']}")
    print("alpha S_mode             S     match_RPS  Δrps   gain%  champ_top3 Δtop3  champ_ent  safe  PASS")
    for r in rows:
        print(f"{r['alpha']:<5} {r['S_mode']:<18} {r['S']:<5} {r['match_rps']:.4f}   {r['drps_vs_prod']:+.4f} "
              f"{r['gain_retained_vs_naive']*100:>4.0f}%  {r['champ_top3']:.3f}   {r['d_top3']:+.3f}  "
              f"{r['champ_entropy']:.2f}      {str(r['champion_safe']):<5} {r['PASS']}")
    print("\nCANDIDATES:")
    for k, v in report["candidates"].items():
        print(f"  {k}: " + (f"alpha={v['alpha']} {v['S_mode']}(S={v['S']}) RPS {v['match_rps']} "
                            f"(gain {v['gain_retained_vs_naive']*100:.0f}%) champ_top3 {v['champ_top3']}" if v else "NONE"))
    print(f"\nWrote {OUT}/ (grid.csv, report.json)")


if __name__ == "__main__":
    main()
