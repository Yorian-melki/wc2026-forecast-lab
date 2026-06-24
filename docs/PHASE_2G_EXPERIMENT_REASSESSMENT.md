# Phase 2G — Next experiment reassessment (ANALYSIS ONLY)

> No implementation. No model/config/data change, no recalibration, no provider fetch.
> Question: **after 2B (fat tail) and 2F (draw calibration) both failed to ship, is another model-math
> experiment truly justified now?** Brutally honest. The answer drives the recommendation, not the reverse.

## The evidence we now stand on
- **2D ceiling audit:** the model sits **near its irreducible floor** on most metrics. W/D/L proper scores
  *beat* the self-sim reference (acc 0.583 vs 0.485; RPS 0.193 vs 0.213; NLL 0.941 vs 1.026) ⇒ mildly
  **under-confident** in-sample. Exact-score top-1/3/5 at/near ceiling (top-1 ceiling only ~12.7%).
  Scoreline rank aggregate ~1 above ceiling; **only** the high-total bucket is genuinely worse
  (5+ rank 21.78 vs 7.03) — real, but ~17% of matches and rank is now a *diagnostic*, not a target.
- **2B:** globally fattening the scoreline distribution **failed** (calibration cost > rank gain).
- **2F:** draw calibration **failed/inconclusive** (RPS/Brier/ECE improved but NLL within noise; mass shift
  too large) — and it revealed the draw issue is mild **over**-prediction, with the live-48 signal unreliable.
- **Structural:** `expected_goals` is Elo-only; the ×0.55 temperature was a *deliberate* champion-level
  de-sharpening, validated via the 4-WC walk-forward.

## Per-candidate reassessment
Fields: target · evidence FOR · evidence AGAINST · data · kill-test · risk (RPS/Brier/NLL/ECE/champion) ·
complexity · overfit · now/defer.

### 1. W/D/L sharpening / temperature diagnostic
- **Target:** W/D/L under-confidence (over-dispersion). **FOR:** 2D's self-sim gap is the *largest, most
  consistent* remaining signal; it's a single global scalar we know was set heuristically. **AGAINST:** that
  scalar was added on purpose to fix champion over-concentration (top-3 66%→42%); sharpening match-level
  *re-opens* that failure. The under-confidence is **in-sample** and may not transfer to WC2026 neutral-site/
  upset conditions — i.e. the "signal" may just be the temperature we chose. **Data:** none.
  **Kill-test:** offline temperature **sweep**, plotting match-level RPS/NLL vs champion top-3 concentration +
  champion-Brier on the 4-WC walk-forward. **Risk:** LOW to match-level (it optimises them), **HIGH to
  champion** calibration — entangled. **Complexity:** LOW (scalar) / validation HIGH. **Overfit:** LOW /
  mis-generalisation HIGH. **Now/defer:** *diagnostic-only sweep* is cheap & informative, but **cannot ship**
  without champion sign-off; likely outcome = "confirms the tradeoff, not shippable."

### 2. Market-total benchmark / anchor feasibility
- **Target:** external validation + the missing conditioning signal for #3. **FOR:** market O/U is the best
  free goal predictor and an independent referee for our self-graded numbers. **AGAINST:** data not in repo
  (only a sample); **fetch forbidden this phase**; market-following erodes independence; train/serve coverage
  hard. **Data:** historical closing O/U + 1X2 for 2010-2025 **and** live — needs acquisition. **Kill-test:**
  peek at model-vs-market total bias on the existing sample (tiny-n); real test needs data. **Risk:** low as
  anchor / med as feature. **Complexity:** MED-HIGH (sourcing). **Overfit:** low-med. **Now/defer:** **DEFER —
  this is a data-acquisition decision, not an experiment.** It is the unlock for #3.

### 3. Conditional high-total / blowout mean adjustment
- **Target:** the one *real* ranking weakness (2D: 5+ rank 21.78 vs ceiling 7.03 = genuine mis-specification).
  **FOR:** strongest "real model weakness" evidence we have; ~30% of matches are 4+ goals. **AGAINST:** 2B
  proved the obvious lever backfires; the *right* lever needs a pre-match high-total signal we **don't have**
  (Elo-only μ); low-total games (majority) currently beat ceiling and would be put at risk; and **rank is a
  demoted diagnostic now** — succeeding improves a non-target. **Data:** a proven pre-match total-goals signal
  (market #2, or style/tempo with OOS lift). **Kill-test (cheap, in-repo, decisive):** OOS regression — does
  ANY in-repo pre-match feature (Elo gap, Elo sum, team historical goal rates) predict actual total goals
  beyond the base rate? **If R²≈0 → permanently close #3.** **Risk:** MED-HIGH to W/D/L calibration.
  **Complexity:** HIGH. **Overfit:** HIGH. **Now/defer:** **DEFER the lever**; the kill-test can be run to
  *close or open* the path with evidence (it commits to no fix — unlike 2B/2F).

### 4. Reporting-only / model honesty improvements
- **Target:** the meta-weakness — we grade on rank/exact (wrong metrics) and the UI presents them as if they
  were targets. **FOR:** **zero model risk**; operationalises every 2D conclusion (surface proper scores +
  CIs + ceiling context; demote rank/exact to labelled diagnostics; honest copy that exact-score is near-
  irreducible); prevents future metric-chasing; aligns with "probabilities, not predictions." It is the **only
  path with unambiguous positive value** after 2B+2F. **AGAINST:** no accuracy gain by definition; touches
  `app.py` display (GREEN-LANE display-only, like Phase 1E). **Data:** none. **Kill-test:** n/a (framing, not a
  hypothesis). **Risk:** **ZERO** to model metrics. **Complexity:** LOW-MED. **Overfit:** none. **Now/defer:**
  **DO NOW** (design-first). Not a model experiment.

### 5. No model change (to the math)
- **Target:** discipline. **FOR:** 2D ceiling audit + two failed experiments + the only real signal being
  data-blocked or champion-entangled = strong cumulative evidence that further model-math tinkering has **low
  expected value and real downside** (champion calibration). **AGAINST:** forecloses #1/#3 — but both are
  blocked/entangled anyway. **Now/defer:** **ADOPT as the standing stance for the model math.**

## 1. Ranked recommendation
1. **Reporting-only / honesty (#4) — DO NEXT** (design-first; GREEN-LANE display). Highest expected value,
   zero model risk, operationalises 2D.
2. **No change to the model math (#5) — ADOPT now** alongside #1. Stop spending on model tinkering until new
   evidence/data appears.
3. *(Optional, cheap, offline)* **Two decisive DIAGNOSTICS to formally close the open questions** — not
   shipping experiments: (3a) high-total feature→total-goals OOS regression (kill-test for #3); (3b)
   temperature/champion frontier sweep (#1, diagnostic-only). Run only if we want #1/#3 *closed with evidence*
   rather than left "deferred."
4. **Market data acquisition (#2) — DEFER** as a separate data decision; the only thing that could later
   unlock #3 as a real (non-blind) lever.

## 2. Paths eliminated now (and why)
- **Draw calibration:** CLOSED by 2F (failed gate; mild and over-predicted, not under). Do not revisit without
  new evidence.
- **Global distribution shape change (fat tail / marginal):** CLOSED by 2B.
- **Optimising exact-score top-1/3 or scoreline rank as targets:** eliminated by 2D (at/near ceiling; rank
  demoted to diagnostic).

## 3. Paths deferred — and what would unlock them
- **#3 conditional high-total mean** — unlock = a *proven* pre-match total-goals signal. Cheapest probe: the
  in-repo feature→total OOS regression (3a). If it shows real OOS lift, the path opens; if R²≈0, close it.
- **#2 market anchor** — unlock = acquiring clean historical + live O/U odds (a data decision; fetch is barred
  this phase). It also feeds #3.
- **#1 temperature sharpening** — unlock = a champion-level guardrail that a sweep (3b) shows is not breached;
  given the temperature was deliberately chosen, this is unlikely but worth measuring once.

## 4. Is "no model change" now the strongest option?
**For the model math: yes — paired with reporting-only.** The honest reading of 2D + 2B + 2F is that the model
is near its achievable ceiling, and every remaining model-math lever is either blocked on data we can't fetch,
entangled with a deliberately-chosen champion tradeoff, or aimed at a demoted diagnostic metric. Continuing to
tinker has low upside and real downside. The strongest posture is: **freeze the model math, ship the honesty/
reporting improvements, and keep the two cheap diagnostics available to close #1/#3 with evidence if desired.**

## 5. If a next experiment is recommended, why it survives where 2B/2F didn't
If we run anything beyond reporting, run **only the high-total feature kill-test (3a)** — and it survives the
2B/2F failure mode precisely because **it is not a fix-and-hope experiment.** 2B and 2F each *assumed* a lever
(fatter tail; more/less draw mass) and tested whether it helped — and it didn't. 3a commits to **no** lever: it
asks whether a usable conditioning signal *exists at all* before anyone builds one. Its only outcomes are
"permanently close #3" (most likely) or "open #3 with proof" — both strictly better than another blind attempt.
That is the discipline Phase 2C demanded: **stop jumping to the next plausible fix; test the precondition
first, and prefer the move that can only eliminate a path.**

**Bottom line:** the next move is **not** a model-math change. It is to (a) ship reporting/honesty improvements
and (b) freeze the math — optionally running the two cheap diagnostics to formally close the remaining open
questions. After two honest negatives, knowing when to stop *is* the win.
