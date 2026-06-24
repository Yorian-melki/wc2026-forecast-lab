# Phase 2C — Full Model Weakness & Solution Research Map (RESEARCH ONLY)

> **No implementation.** No model/config/data/probability change. No provider fetch, no API calls.
> This document maps the weakness space and the solution space *before* choosing the next experiment.
> Principle: **our strength is knowing our weaknesses.** Our failure mode is jumping from one dead
> hypothesis to the next plausible one (Phase 2B was exactly that risk). This map exists to stop that.
> Brutally honest by design. Optimised for *eliminating* bad paths, not sounding clever.

---

## Part 0 — Grounded facts about the current model (anti-hand-waving anchor)
Verified from the code, not memory (`calibrated_elo_model.py`):
- The **displayed scoreline distribution** comes from `scoreline_probs → expected_goals → _build_dc_flat`.
- `expected_goals` is **purely Elo-driven**: `μ = exp(log_base ± β·(Elo_a−Elo_b)/400) × knockout_mult ×
  host_boost × jet_lag`, clamped **[0.15, 3.60]**. Docstring: *"Elo-only expected goals: no analyst
  priors, no StatsBomb residuals."*
- Therefore the goal means use **NO**: market odds, lineups/injuries, recent form (as a separate term),
  style/tempo, tournament incentives/stakes, game-state. `style_drag` exists but only feeds **red-card**
  propensity in the Monte Carlo, **not** μ. `market_odds_sample.csv` exists but is **not a model input**
  ("model vs market" is a display-only comparison).
- Scoreline shape = **independent** Poisson(μ_a)⊗Poisson(μ_b) + Dixon-Coles τ on the 4 low cells
  (ρ=−0.021). ML 1X2 reweights only the W/D/L *mass* at 0.20. Grid g=8 (goals 0–7). 100k MC.
- The model is **structurally symmetric around Elo** (only asymmetries: host boost, jet lag, KO mult).

**Implication:** "model may be too symmetric / may miss market / lineups / incentives / style" are
**confirmed structural absences**, not suspicions. Whether any of them *matters* for accuracy is the
open question — absence ≠ weakness until proven to cost calibration.

---

## Part A — Measured weaknesses (with honest status)
Source: official 48-match audit `2026-06-24_14-54.json` + Phase 2B diagnostic.

| Weakness | Number | Honest status |
|---|---|---|
| Draw recall | **0/14** | **~70% decision-rule artifact.** `argmax(P_h,P_d,P_a)` is *structurally* never "draw" under symmetric DC-Poisson (μ≈1.25 ⇒ max P(draw)≈0.26–0.28 < P(home)≈0.36). Draw *probabilities* are only mildly low (pred 0.15–0.25 vs actual 0.27–0.36). Recall is the **wrong metric**; the real (mild) issue is draw *calibration*. |
| Exact score top-1 | 8.3% | **Likely near-irreducible.** Empirically the modal exact score (1-0/1-1) occurs ~8–12% of the time; a calibrated model can't beat the base rate by much. Low upside to chase. |
| Exact score top-3 | 29.2% | Some headroom, but bounded by the same irreducibility. |
| High-total / 5+ rank | mean rank **18.0** (live) | **Real but partly metric-induced.** 2B proved fattening the tail only buys ~4% rel rank while degrading Brier/RPS/NLL/ECE — a bad trade. Cause is more plausibly conditional-mean (μ too low/symmetric for specific games) AND the metric over-rewarding pinpointing rare cells. |
| Blowout rank | n=15 mean rank **13.73**, top-10 cov 26.7% | Same family as above. |
| Avg scoreline rank | **7.98** | Aggregate of the above; dominated by the high-total tail. |

**Cross-cutting truth (the deepest one):** **scoreline rank and proper calibration are partially in
tension.** A *well-calibrated* model SHOULD rank rare high scores low — because they ARE low-probability.
"Improving rank" by spreading mass to high scores = worse calibration (exactly what 2B showed). So some
of A is not a model failure at all; it is the **rank metric punishing correct humility**.

---

## Part B — Possible hidden weaknesses (status after grounding)
| Suspected | Status |
|---|---|
| Underuses tournament incentives (dead rubbers, must-win, rotation in decided groups) | **Confirmed absent** from μ. Plausibly real for specific late-group games. Hard to get clean labels. |
| Misses lineup/rotation/injury | **Confirmed absent.** Real in principle; data is timely-but-noisy, hard to backfill historically. |
| Misses game-state incentives (in-play) | Out of scope for a *pre-match* forecast; `inplay_model.py` is separate. |
| Misses style/tempo mismatches | **Confirmed absent from μ.** Could matter for totals; needs style data with proven signal. |
| Misses market-implied goal totals | **Confirmed absent.** Market is the strongest free benchmark; not even used as an anchor. |
| Too symmetric around Elo | **Confirmed structurally true.** Whether it costs accuracy is unproven. |
| Calibrated for W/D/L but not scoreline rank | **True by construction** — fit objective is goal-NLL + DC; the ML layer targets W/D/L. Rank is not in any objective. |
| Rank metric over-punishes rare correct scores | **True** (see Part A cross-cutting truth). A metric-design issue, not a model issue. |
| Historical validation ≠ WC2026 conditions | **Real.** 10,555 set is mostly friendlies/qualifiers; different goal environment, no neutral-site KO intensity. |
| Live-48 too small / selection-biased | **Real.** n=48, group-stage only, no knockouts, specific teams. CIs are wide; draw "0/14" is 14 events. |
| Draw weakness = decision-rule artifact | **Mostly true** (Part A). |
| Exact-score weakness = irreducible noise | **Mostly true** for top-1. |

---

## Part C — Unknown-unknowns actively searched (newly named)
Categories not in the original list, surfaced by deliberate search:
1. **Elo staleness / source-graph risk** — the calibrated Elos are a 2026-06-09 snapshot; live updates
   ride on ESPN. If the Elo *inputs* drift or a provider mislabels a result, every downstream metric moves
   with no model bug. *Weakness in the data pipeline, not the math.*
2. **Neutral-site assumption** — WC2026 treats all non-host teams as neutral, but altitude (Mexico City),
   heat/humidity, travel distance across a continent-sized host region are unmodeled. Could bias totals.
3. **Within-tournament non-stationarity** — teams improve/decline across a tournament (cohesion, fatigue);
   a static pre-tournament Elo can't capture it; live Elo updates lag.
4. **Correlation/SoS leakage in validation** — walk-forward over 4 WCs = effectively n≈4 independent
   tournament draws for champion-level claims; "validated on 4 WCs" is weaker than it sounds.
5. **Grid truncation at 7 goals** — any 8+ goal game folds into the boundary; rare but a silent cap.
6. **Objective/eval mismatch as the true root cause** — we keep measuring "rank" but optimising "NLL";
   the system has no single coherent objective, so every experiment is judged on a metric it wasn't built for.
7. **Self-grading risk** — "maturity 6.93/10" and ECE numbers are self-computed; no external referee.

---

## Part D — 15 research lenses
Compact per lens: **Suspected weakness · Hidden failure mode · Data wanted · Approach · Addresses ·
New risk it creates · Data availability · Complexity · Overfit risk · Upside · Testability · Why it
might fail · Simplest kill/validate test.**

**1. Probability/distribution theorist** — Suspects independence + thin tail. FM: over-concentration on
1-0/1-1. Data: none (in-repo). Approach: bivariate/correlated counts, NegBin, mixtures. Addresses: high-total
rank. New risk: W/D/L calibration loss. Avail: in-repo. Complexity: med. Overfit: med. Upside: **LOW
(2B already falsified the marginal-tail version).** Testability: high. Why fail: rank↔calibration tension.
Kill test: *done* (2B). Correlated-count variant: re-score with one correlation param, same gate → expect same fail.

**2. Football domain modeler** — Suspects μ ignores style/tempo/matchup. FM: systematically low totals in
open games. Data: style metrics with proven predictive signal. Approach: tempo term in μ. Addresses:
high-total rank via conditional mean. New risk: overfit to noisy style tags; asymmetry bugs. Avail: partial
(`style_metrics.csv` exists, signal unproven). Complexity: med-high. Overfit: **high**. Upside: med. Testability:
med. Why fail: style tags may be circular/low-signal. Kill test: regress actual total goals on a style-mismatch
feature, out-of-sample — if R² ≈ 0, kill before any model work.

**3. Betting-market quant** — Suspects we ignore the best free benchmark. FM: model totals biased vs market
with no detection. Data: historical closing 1X2 + O/U totals. Approach: market as **anchor/validator first**,
input later. Addresses: nearly all (diagnostic for where we're wrong). New risk: market-following kills
independence; leakage if used naively. Avail: free-ish (scrape risk) / paid clean. Complexity: low (as
diagnostic). Overfit: low (as diagnostic). Upside: **HIGH for diagnosis, med as feature.** Testability: high.
Why fail: clean historical odds are annoying to source. Kill test: compare model O/U implied total vs market
on any odds sample — quantify bias.

**4. Causal inference researcher** — Suspects confounds (host, altitude, rest days) treated as noise. FM:
biased μ for hosts/high-altitude. Data: venue/altitude/rest. Approach: adjust μ for measured confounders.
Addresses: neutral-site assumption. New risk: tiny-n adjustment overfit. Avail: free (venue/altitude). Complexity:
med. Overfit: med. Upside: low-med. Testability: med. Why fail: effects small vs Elo. Kill test: residual-vs-altitude
plot on historical neutral matches.

**5. Feature-engineering specialist** — Suspects μ underfit (1 feature: Elo). FM: leakage/over-engineering.
Data: form, rest, travel, h2h. Approach: small GBM on μ residuals. Addresses: conditional mean. New risk:
**overfit + opacity + leakage** (worst offender). Avail: in-repo+free. Complexity: high. Overfit: **very high**.
Upside: med. Testability: med (needs strict walk-forward). Why fail: 10k matches, dozens of features → memorise.
Kill test: permutation importance under walk-forward; if features don't beat Elo-only OOS, kill.

**6. Data-acquisition / API hunter** — Suspects we lack lineups, xG, odds, injuries. FM: data we can't backfill
historically → train/serve skew. Data: lineups, pre-match xG, odds, injuries. Approach: source + dedup. Addresses:
B-list gaps. New risk: train/serve mismatch (have it live, not historically). Avail: mixed (see Part 6). Complexity:
med. Overfit: n/a. Upside: enabling. Testability: low until acquired. Why fail: timeliness + historical coverage.
Kill test: can we get the SAME feature for 2010–2025 AND live? If not, it's serve-only → likely unusable.

**7. Bayesian modeler** — Suspects point-estimate Elos hide uncertainty. FM: overconfident tails. Data: none.
Approach: posterior over Elo/params → predictive distribution; partial pooling for weak teams. Addresses:
calibration, weak-team variance, champion-band honesty. New risk: complexity, slow MC. Avail: in-repo. Complexity:
high. Overfit: low (regularising). Upside: med (honesty++, accuracy ~flat). Testability: high (proper scores).
Why fail: may not move point accuracy. Kill test: does posterior-predictive beat plug-in on NLL OOS?

**8. Tournament-incentives specialist** — Suspects dead-rubber/rotation effort changes. FM: wrong μ for decided
groups. Data: pre-match qualification state + labelled effort. Approach: stakes feature. Addresses: a thin slice
of group games. New risk: tiny labelled set → overfit. Avail: derivable (state) but **effort is unlabelled**.
Complexity: high. Overfit: high. Upside: **low (few affected matches).** Testability: low. Why fail: too few clean
cases. Kill test: count historically how many WC matches were true dead rubbers — if ~handful, deprioritise.

**9. Robust-validation / anti-overfit researcher** — Suspects our validation overstates skill. FM: SoS/correlation
leakage, n≈4 tournaments for champion claims, live-48 selection bias. Data: none. Approach: blocked/nested CV,
bootstrap CIs, by-era splits. Addresses: **trust in every other result.** New risk: none (only tightens claims).
Avail: in-repo. Complexity: low-med. Overfit: n/a. Upside: **HIGH (meta).** Testability: high. Why fail: may just
confirm wide CIs. Kill test: bootstrap CI on the live-48 metrics — if CIs are huge, stop over-reading the audit.

**10. Simplicity-first production engineer** — Suspects we're adding complexity for noise. FM: maintenance + drift
debt. Data: none. Approach: prefer 1-param fixes; reject anything not provably beating Elo-only OOS. Addresses:
discipline. New risk: under-fitting. Avail: in-repo. Complexity: trivial. Overfit: lowest. Upside: med (prevents
waste). Testability: high. Why fail: n/a. Kill test: "does it beat Elo-only on a proper score OOS by > noise?"
as a gate on *everything*.

**11. Adversarial red-team** — Suspects metrics are gameable / hidden bugs. FM: someone "improves" recall by a
draw-threshold hack (metric-gaming); silent NaN/cap bugs. Data: none. Approach: try to break each metric; fuzz
inputs. Addresses: integrity. New risk: none. Avail: in-repo. Complexity: low. Upside: med (prevents fake wins).
Testability: high. Why fail: n/a. Kill test: attempt the draw-threshold hack and show it tanks Brier — pre-empts it.

**12. Metric-design / objective researcher** — Suspects **we optimise NLL but grade rank** — incoherent objective.
FM: chasing rank degrades calibration (2B!). Data: none. Approach: declare a **single proper-scoring primary
objective** (RPS/Brier/log-loss); demote exact-score rank to a *diagnostic*, not a target. Addresses: **the root
cause of 2B-style traps.** New risk: none (clarifies, doesn't change the model). Avail: in-repo. Complexity:
**trivial (docs/eval)**. Overfit: none. Upside: **HIGH (prevents future waste; reframes whether A is even real).**
Testability: high. Why fail: doesn't add accuracy by itself. Kill test: re-read 2B under a proper-score-primary lens
— it already shows tail "wins" were calibration losses.

**13. Live-operations / real-time researcher** — Suspects pipeline/provider drift dominates model error live. FM:
silent provider mislabels move metrics with no model bug. Data: provider logs. Approach: data-quality monitors,
not model changes. Addresses: live trust. New risk: none. Avail: in-repo (logs). Complexity: low. Upside: med.
Testability: med. Why fail: may find pipeline is fine. Kill test: spot-check the 48 audited results vs a second source.

**14. Ensemble / model-stacking researcher** — Suspects a single stack underperforms a blend. FM: stacking on tiny
data overfits the blend weights. Data: none new. Approach: stack Elo-DC + ML + market (if available). Addresses:
modest accuracy. New risk: **blend-weight overfit on n≈4 tournaments.** Avail: in-repo. Complexity: med. Overfit:
high. Upside: low-med. Testability: med. Why fail: too little data to learn weights. Kill test: nested-CV the blend
weight — if it's unstable across folds, kill.

**15. "Irreducible uncertainty" skeptic** — Suspects most of A is noise, not failure. FM: we burn months chasing a
ceiling. Data: none. Approach: estimate the **entropy floor** — best achievable exact-score top-1/RPS given inherent
randomness (e.g., Poisson-with-true-λ ceiling, or market's own exact-score hit rate). Addresses: expectation-setting.
New risk: none. Avail: in-repo + market ref. Complexity: low. Upside: **HIGH (kills false targets).** Testability:
high. Why fail: n/a. Kill test: simulate from the model's *own* λ and measure exact top-1 — if ≈8%, our 8.3% is at
the ceiling and is **not a weakness**.

---

## Synthesis

### 1. Complete weakness map
- **Measured & real (worth proper-score attention):** draw *calibration* (mild), high-total conditional mean
  (maybe), avg-rank tail (partly metric).
- **Measured but mostly artifact/irreducible (low/zero upside):** draw *recall* 0/14 (decision-rule),
  exact-score top-1 8.3% (entropy floor), much of avg-rank (rank↔calibration tension).
- **Suspected & structurally confirmed-absent (matter unproven):** market anchor, style/tempo in μ, incentives,
  lineups, symmetry, neutral-site/altitude.
- **Unknowns to investigate:** validation leakage (n≈4 tournaments), live pipeline/provider drift, grid truncation,
  objective/eval mismatch, self-grading.
- **Likely irreducible limits:** exact-score pinpointing; champion-level discrimination at n≈4; draw being the modal
  outcome.

### 2. Complete solution-family map (with a verdict on each)
- **Distribution changes (NegBin/correlation):** ❌ largely falsified by 2B for the marginal case; correlation
  variant likely same trap.
- **Conditional-mean changes (tempo/matchup μ):** ⚠️ plausible but data-risky & overfit-prone; **gate behind a
  market-anchor diagnostic** to avoid another blind jump.
- **Draw calibration (isotonic/Platt/1 param):** ✅ small, real, proper-score-validated, low overfit.
- **Scoreline-ranking objective changes:** ✅✅ *reframe* — adopt proper-scoring primary, demote rank to diagnostic.
- **Market-data integration:** ✅ as **validator first** (high diagnostic value, low risk), feature later.
- **Lineup/injury:** ⚠️ blocked by historical-coverage / train-serve-skew; park until data proven.
- **Style/tempo features:** ⚠️ only if a simple OOS regression shows real signal first.
- **Tournament-incentive features:** ❌ too few clean cases; deprioritise.
- **Bayesian uncertainty layer:** ✅ for *honesty* (champion bands), neutral for point accuracy.
- **Ensemble/stacking:** ❌ blend-weight overfit on n≈4; not now.
- **Validation redesign:** ✅✅ meta-high-value; tightens trust in everything else.
- **Metric redesign:** ✅✅ (same as scoreline-objective) — the highest-leverage, lowest-risk move.
- **Live-data monitoring:** ✅ cheap insurance; not a model change.
- **Human-in-the-loop data layer:** ⚠️ only for curated lineups/odds if pursued; high ops cost.

### 3. Inside-the-box but under-tested
- Bootstrap **confidence intervals** on the live-48 metrics (we quote point values for n=48).
- **Entropy-floor** estimate for exact-score and RPS (are we already at the ceiling?).
- **Draw probability calibration** validated on RPS/NLL (never isolated and tested).
- **Market-vs-model bias** scan on totals (never done).

### 4. Outside-the-box but plausible
- Treat **market closing odds as the held-out "truth"** and grade the model's *information edge* vs market, per
  match type — a different, harder, more honest objective than scoreline rank.
- **Mixture-of-regimes** μ (low-block vs open game) instead of one symmetric Elo map — only if style signal proven.
- **Posterior-predictive** champion bands replacing the current β-sampling floor.

### 5. Fake sophistication — eliminate immediately
- ❌ Neural/deep score models (10k matches, dozens of teams → memorisation; opaque; no proof edge).
- ❌ Per-team bespoke parameters (48×k params, no data).
- ❌ Exotic copulas / full correlated bivariate-NegBin (marginal gain; 2B trend says calibration cost).
- ❌ News/sentiment/social features for goals (noise).
- ❌ RL on the bracket. ❌ Auto-ML over hundreds of features. ❌ Stacking many models on n≈4 tournaments.

### 6. Data sources / APIs to investigate later (NOT now — no fetch)
- **Free / open:** football-data.co.uk (historical 1X2 + O/U closing odds, club-heavy), Wikipedia/Wikidata venues
  & altitude, openfootball, FBref/StatsBomb-open (xG, partial). *Scrape-risk:* FBref ToS.
- **Paid clean:** odds APIs (the-odds-api, OddsPortal exports), Opta/StatsBomb full (xG, lineups), historical
  closing-line databases.
- **Manual/curated:** lineup confirmations (timely, not backfillable), injury reports.
- **Impossible / not worth it:** reliable historical "effort/motivation" labels; true dead-rubber intent.
- **Decision rule for any source:** must be obtainable for BOTH 2010–2025 (training) AND live (serving), or it's
  serve-only and probably unusable.

### 7. Simplicity-first shortlist (best upside ÷ complexity ÷ overfit ÷ data-need)
1. **Metric/objective reframe** — proper score primary, rank as diagnostic. *(cost ~0, risk 0, prevents future waste)*
2. **Validation hardening + bootstrap CIs + entropy floor** — tells us which "weaknesses" are real vs ceiling. *(in-repo)*
3. **Market-anchor diagnostic** — quantify where the model is actually biased. *(needs a small odds sample)*
4. **Draw probability calibration** — the one genuinely real, cheap *model* tweak, proper-score-gated.

### 8. Research priority ranking (impact · proof · feasibility · simplicity · downside · kill-speed)
| Rank | Candidate | Impact | Proof quality | Feasible | Simple | Downside | Kill-speed |
|---|---|---|---|---|---|---|---|
| 1 | Metric/objective reframe | High (meta) | High | ✅ in-repo | ✅✅ | none | instant |
| 2 | Validation + CIs + entropy floor | High (meta) | High | ✅ in-repo | ✅ | none | fast |
| 3 | Market-anchor diagnostic | High (dx) | High | ⚠️ small data | ✅ | low | fast |
| 4 | Draw calibration | Med | High | ✅ in-repo | ✅ | low | fast |
| 5 | Conditional-mean/tempo | Med | Med | ⚠️ data/overfit | ✗ | med | slow |
| 6 | Bayesian honesty layer | Med (honesty) | High | ✅ | ✗ | low | med |
| 7 | Distribution/correlation | Low | High (likely fail) | ✅ | ✗ | med | done-ish |

### 9. Top 3 future experiments (DEFINED, not implemented)
- **E1 — Objective & ceiling audit (offline, in-repo):** recompute all metrics as proper scores with bootstrap
  CIs on the live-48; estimate the entropy floor by simulating from the model's own λ. *Output:* which Part-A
  "weaknesses" are real vs at-ceiling vs metric-induced. *Kills or validates the entire A list.*
- **E2 — Market-anchor bias diagnostic (offline, on a captured odds sample):** compare model-implied W/D/L and
  O/U totals to market on a held-out set; locate systematic bias by match type. *Output:* go/no-go + direction for
  any conditional-mean work. *Read-only; no market input to production.*
- **E3 — Draw calibration (offline):** fit a 1–2 param draw-mass calibrator; accept only if RPS/NLL/ECE improve
  OOS via walk-forward. *Output:* a small, honest, proper-score-validated improvement or a clean rejection.

### 10. Single best next experiment — **E1 (Objective & ceiling audit)**
**Why E1 first, and why not the others:**
- **Why E1:** every model experiment is currently judged partly on **scoreline rank**, a metric in tension with
  calibration — 2B "improved" rank while degrading Brier/RPS/ECE. Until we (a) fix the yardstick to a proper score
  and (b) know the **entropy floor**, we cannot tell a real weakness from a metric artifact or an irreducible
  ceiling. E1 is in-repo, ~zero risk, fast to kill, and it may **delete half of Part A as non-problems** — the
  highest-leverage thing we can do. It directly serves the core principle: *know our weaknesses before chasing them.*
- **Not E2 (market):** higher value as a *feature* later, but it needs a clean odds sample we don't yet have, and
  its conclusions are only trustworthy once E1 fixes the objective. Sequence it second.
- **Not E3 (draw calibration):** real but small, and "draw recall 0/14" is mostly a decision-rule artifact — E1
  will tell us whether draw *calibration* is even worth the change before we touch it.
- **Not conditional-mean/tempo/distribution:** the most complex, most overfit-prone, most data-hungry, and 2B
  already shows the high-total problem is partly metric-induced. Gating it behind E1+E2 is precisely how we avoid
  the "next plausible hypothesis" trap.

**Bottom line:** the next move is **not a model change** — it is to fix what we measure and learn the irreducible
floor. That is the highest-upside, simplest, most testable path, and it is the most honest one.
