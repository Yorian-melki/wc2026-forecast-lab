# Phase 2E — Next model experiment selection (SELECTION ONLY)

> No implementation. No model/config/data change, no recalibration, no provider fetch.
> Grounded in the Phase 2D validated weakness map and the Phase 2B negative result.
> Brutally honest: optimise for highest upside ÷ risk ÷ data-need ÷ kill-speed, and protect the parts
> that already work (W/D/L accuracy, RPS, **champion-level calibration**).

## Inputs (settled facts)
- **2D verdicts:** exact-score top-1/3/5 ≈ irreducible (top-1 ceiling ~12.7%); scoreline rank = diagnostic,
  not a target; draw recall 0/14 = decision-rule artifact. **Real, bounded weaknesses:** (a) high-total/
  blowout *conditional* ranking (5+ real 21.78 vs ceiling 7.03; ~17% of matches), (b) mild draw
  under-calibration (−3.6pp), (c) mild W/D/L under-confidence (model over-dispersed; in-sample).
- **2B lesson:** globally fattening the scoreline tail FAILED (degraded Brier/RPS/NLL/ECE for ~4% rel rank).
  **Do not globally fatten.** Any high-total fix must be *conditional* + gated.
- **Model facts:** `expected_goals` is Elo-only (no market/lineups/style/incentives in μ). Config already
  has a `use_isotonic_calibrator` hook (currently **off**) + a W/D/L reweight path (`_reweight_flat_to_wdl`).
  The ×0.55 temperature was added *specifically* to fix champion over-concentration (top-3 66%→42%).

## Per-candidate analysis

### 1. Conditional high-total / blowout mean adjustment
- **Target:** the one real ranking weakness (5+ rank 21.78 vs ceiling 7.03), conditional on match type.
- **Upside:** bounded — ~17% of matches; aggregate proper-score gain likely small (low-total games already
  beat ceiling and would be put at risk).
- **Risk to RPS/Brier/NLL/ECE:** **MED-HIGH.** Raising μ for "high-total" games is the same lever 2B showed
  degrades W/D/L calibration; conditioning narrows but doesn't remove the risk.
- **Required data:** a *pre-match* signal that predicts high totals (style/tempo/market). **We don't have a
  proven one** — Elo gap alone doesn't separate blowouts from open games. This is the blocker.
- **Complexity:** HIGH (new conditional μ term + re-fit + gate). **Overfit:** HIGH (~17% positive rate).
- **Kill-test:** offline OOS regression — does ANY available pre-match feature (Elo gap, Elo sum, team
  historical goal rates) predict actual total goals better than the base rate out-of-sample? If R²≈0 → kill.
- **Now/defer:** **DEFER** until a conditioning signal is proven (its own cheap kill-test, and/or candidate 4).

### 2. Draw probability calibration
- **Target:** the −3.6pp draw under-calibration (confirmed real, mild).
- **Upside:** SMALL but clean and proper-score-relevant (drawn matches ≈ 22%); modest RPS/NLL gain.
- **Risk to RPS/Brier/NLL/ECE:** **LOW-MED.** A monotone draw-mass recalibration is gentle; main risk is
  over-shifting and the MC champion knock-on (W/D/L feeds the tournament sim) — both checkable.
- **Required data:** **NONE new** (in-repo historical results).
- **Complexity:** **LOW-MED** (1–2 params; fits the existing reweight / `use_isotonic_calibrator` hook).
  **Overfit:** **LOW** (1–2 params, large data).
- **Kill-test:** offline draw-inflation grid / isotonic on a training split; accept only if RPS **and** NLL
  improve OOS on walk-forward with ECE + outcome-accuracy + champion calibration not regressing. Else kill.
- **Now/defer:** **TEST NOW.** Real target, low risk, in-repo data, champion-safe-ish, fast to kill.

### 3. W/D/L sharpening / temperature adjustment
- **Target:** W/D/L under-confidence (over-dispersion from ×0.55).
- **Upside:** potentially the LARGEST on match-level proper scores (affects all matches).
- **Risk:** **HIGH & ENTANGLED.** Sharpening re-concentrates champion probabilities — the exact failure the
  temperature was added to fix. And the under-confidence is **in-sample**; may not hold OOS / under WC neutral-site
  conditions. Trades a tournament-credibility property for a match-level metric.
- **Required data:** none new. **Complexity:** LOW (a scalar) but **validation** complexity HIGH (must check
  match-level AND champion-level). **Overfit:** LOW (1 scalar); **mis-generalisation:** HIGH.
- **Kill-test:** offline **diagnostic sweep** of the temperature multiplier; plot match-level RPS/NLL **vs**
  champion top-3 concentration + champion-Brier on the 4-WC walk-forward. If every match-level gain breaches
  the documented champion guardrail → the tradeoff kills it.
- **Now/defer:** **DEFER as a shipping change.** A *diagnostic-only* sweep (no ship) is worth running to map
  the frontier — but not as the first change.

### 4. Market-total benchmark / anchor
- **Target:** supplies candidate 1's missing conditioning signal + an independent validation anchor.
- **Upside:** HIGH as a diagnostic; MED-HIGH as a feature (market O/U is the best free goal predictor).
- **Risk:** market-following erodes independence ("probabilities, not predictions"); leakage if naive; needs
  historical **and** live coverage.
- **Required data:** historical closing O/U + 1X2 for 2010–2025 **and** live — **not in repo**; only a small
  `market_odds_sample.csv` exists. **Fetch is forbidden this phase.**
- **Complexity:** MED-HIGH (sourcing/dedup/integration). **Overfit:** LOW-MED (anchor) / MED (feature).
- **Kill-test:** with the existing sample only, compare model-implied vs market-implied totals for systematic
  bias (small-n peek); the real test needs a data-acquisition step.
- **Now/defer:** **DEFER** — data-blocked + fetch-prohibited now. It is the *gate* for candidate 1.

### 5. No model change — reporting only
- **Target:** the META weakness — we keep grading on rank/exact (the wrong metrics). Surface proper scores
  (RPS/Brier/NLL) + CIs + ceiling context in-app; demote rank/exact to labelled diagnostics; honest copy that
  exact-score is near-irreducible.
- **Upside:** HIGH on **trust** and on preventing future wasted experiments (the project's #1 value). Zero
  accuracy gain by definition.
- **Risk to RPS/Brier/NLL/ECE:** **ZERO** (no model change).
- **Required data:** none. **Complexity:** LOW-MED (display/copy, GREEN-LANE display-only later). **Overfit:** none.
- **Kill-test:** n/a — it's a framing fix, not a hypothesis.
- **Now/defer:** **DO IN PARALLEL, regardless** — but it is *not a model experiment*.

## 1. Ranked comparison table
| Rank | Candidate | Target weakness | Upside | RPS/Brier/NLL/ECE risk | Data | Complexity | Overfit | Kill-speed | Now/defer |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Draw calibration** | draw −3.6pp | small-real | low-med | in-repo | low-med | low | fast | **NOW** |
| 2 | **Temperature sweep (diagnostic only)** | W/D/L under-confidence | potentially large | high (champion) | in-repo | low / val-high | low | instant | now *(measure only)* |
| 3 | Conditional high-total mean | 5+ rank | bounded | med-high | **missing signal** | high | high | medium | defer |
| 4 | Market-total anchor | high-total signal + validation | high (dx) | med | **not in repo** | med-high | low-med | medium | defer (data) |
| — | Reporting-only | meta / trust | trust (0 acc) | none | none | low-med | none | n/a | **parallel, always** |

## 2. Eliminated / deferred paths and why
- **Conditional high-total mean (3rd):** *deferred, not eliminated.* No proven pre-match signal separates
  blowouts from open games; building the lever blind = the 2B trap again. Gate it behind a feature-signal
  kill-test and/or market data.
- **Market anchor (4th):** *deferred* — blocked by data acquisition (forbidden to fetch this phase). It is the
  prerequisite/unlock for the conditional-mean path, so it sequences *before* candidate 1, not as the first run.
- **Nothing is hard-eliminated** — but candidates 1 and 4 are explicitly *not first*.

## 3. Top 2 plausible paths (runnable now, offline, in-repo)
- **A — Draw probability calibration** (real, low-risk, champion-safe, fast kill).
- **B — Temperature/champion frontier sweep, diagnostic-only** (maps the biggest surfaced signal vs its
  champion cost; informs whether any sharpening is ever safe; ships nothing).
- *(Plus the parallel, non-experiment Reporting-only track — zero risk, high trust.)*

## 4. Single recommended next offline experiment
**Candidate 2 — Draw probability calibration**, run offline as fit-on-train → validate-on-walk-forward, with a
strict proper-score gate (accept only if RPS **and** NLL improve OOS with ECE, outcome accuracy, and champion
calibration not regressing). It is the **only** path that is simultaneously: a *confirmed-real* weakness,
*low-risk* to the metrics that matter, *champion-safe*, needs *no new data*, fits an *existing hook*, and is
*fast to kill*. Modest upside — but a clean win or a clean rejection, with no entanglement.

## 5. Experiment design (high level — NOT implemented)
- New offline script `scripts/exp_draw_calibration.py` (scratch `experimental/` only; never imported by app).
- Reuse the deterministic historical feature build + the production scoreline distribution.
- Calibrators to compare: (i) a single multiplicative **draw-mass factor** then renormalise W/D/L; (ii) an
  **isotonic/Platt** map of predicted P(draw)→calibrated. Fit on a **time-blocked / walk-forward** train split.
- Evaluate OOS: RPS, Brier_wdl, NLL_wdl, ECE, draw-calibration gap, outcome accuracy, **+ champion-level
  concentration/Brier guardrail** (W/D/L feeds the MC, so verify the tournament outputs barely move).
- Output: a tradeoff report + accept/reject verdict. **No production write.** Shipping = a separate Phase 2F.

## 6. Files that would be touched LATER if implemented (all RED LINE, separate approval)
- **Candidate 2 (recommended):** `src/wc2026/calibrated_elo_model.py` (draw calibrator in the W/D/L reweight
  path), `data/model_stack_config.json` (enable `use_isotonic_calibrator` / a draw-cal flag),
  `data/elo_calibrated_params.json` (calibrator params) — version bump + `CHANGELOG_MODEL.md` + archive.
- Candidate 1: same model file (`expected_goals` conditional term) + params + config + likely a new feature
  source. Candidate 3: `data/elo_calibrated_params.json` temperature/β + heavy champion re-validation.
  Candidate 4: a new market data source + integration. Candidate 5: `app.py` display + copy only (GREEN LANE).

## 7. Why this is the best next move after Phase 2D
2D proved most "weaknesses" are artifacts or irreducible, and 2B proved the obvious distribution fix backfires.
That leaves three real but constrained levers. Of them, **draw calibration is the only one that is real,
cheap, low-risk, champion-safe, and needs no new data** — so it is the move that respects every hard-won
constraint instead of reopening the champion-temperature tension (candidate 3) or building a conditional lever
with no proven signal (candidate 1) or fetching data we're barred from this phase (candidate 4). It is a clean
win-or-kill. The bigger swings are explicitly *sequenced behind* a diagnostic (3) or a data step (4→1), which is
exactly the discipline Phase 2C demanded: stop jumping to the next plausible hypothesis; take the provable,
reversible step first. Reporting-only (5) should proceed in parallel because it costs nothing and directly
serves "our strength is knowing our weaknesses."
