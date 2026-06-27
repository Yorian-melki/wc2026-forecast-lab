# Phase 3H-B — Market-Odds Integration Design (DESIGN ONLY)

> **Design only. No implementation, no production change, no provider calls, no secrets.** Grounds:
> the 3E→3H-A evidence chain + the existing model mechanics (`calibrated_elo_model._reweight_flat_to_wdl`,
> and the precedent `ml_weight_mode: "dynamic"` regime weighting in `model_stack_config.json`).
> Final recommendation at the bottom: **READY_FOR_MODEL_LAB_PROTOTYPE**.

## Evidence recap (why this is worth designing)
Market-implied 1X2 beats the **full** frozen production W/D/L (Elo→DC→ML@0.20) out-of-sample beyond
bootstrap noise — WC (3F: RPS 0.202 vs 0.234), generalised across competitions (3G: pooled non-WC 0.177
vs 0.199), better calibrated (ECE ~0.05 vs ~0.10), and the edge is **heterogeneous** (large where the model
is weak — AFC/CAF/WC-final; ≈ zero on the Euro). Live pre-match WC2026 1X2 is available (3H-A: The Odds API
15/15, Sportmonks 19/41). RPS reconciliation (3F-B) confirmed no formula/orientation bug.

---

## 1. Provider architecture
- **Primary = The Odds API.** Rationale: dedicated odds API, clean `h2h` (= 3-way 1X2), **full upcoming
  coverage (15/15)**, and **quota-efficient** — one `/v4/sports/soccer_fifa_world_cup/odds?markets=h2h`
  call returns *all* upcoming events at once (1 credit × regions × markets), so a few polls/day fit easily
  in the 500/mo free tier. No trial-expiry dependency.
- **Fallback / cross-check = Sportmonks.** Same provider as the *validated historical* pipeline (consistent
  team ids, richer fields incl. `latest_bookmaker_update` + `probability`); needs a **paid plan after the
  2026-07-09 trial** → a cost decision. Use it to cross-check the primary and as failover.
- **Provider disagreement rule:** at lock time compute no-vig 1X2 from each available source. If both present
  and per-outcome |Δ| ≤ ~4pp → use the **consensus (mean)**. If |Δ| larger → prefer the source with **more
  bookmakers + fresher timestamp**, and **log the disagreement**. If only one present → use it (flag
  low-redundancy). If neither usable → **fall back to the frozen model**.
- **Rejected:** TheStatsAPI as a live odds source (3H-A: `odds` 404 on scheduled matches — finished-match
  odds only). Keep it WATCHLIST for post-match odds/xG later.

## 2. De-vig / aggregation (freeze the validated method)
- Per bookmaker per outcome: `implied = 1 / decimal_odds`.
- **No-vig:** normalise the 3 outcomes to sum 1 (basic multiplicative). *This is exactly what 3E–3G
  validated — do NOT change it now.* (Shin / power de-vig are future options, only if re-validated.)
- **Multi-bookmaker:** **median across books of the per-outcome implied prob, then normalise** (the 3E–3G
  rule; robust to outliers). Require **≥3 bookmakers** else flag low-coverage.
- **Last pre-match snapshot:** fix a **lock time = kickoff − 15 min** (configurable). Use the latest book
  update ≤ lock; freeze it for the match (never update in-play).
- **Stale detection:** newest book update older than threshold (e.g. >24h pre-kickoff) OR < 3 books →
  mark **STALE** → do not use market for that match (fall back to model).

## 3. Blend strategy (identity-preserving; reject α=1.0)
The blend-grid optimum was α=1.0 (pure market) — **rejected**: that is a *bookmaker wrapper*, destroying the
independent forecast. Candidate α policies (in order of intended adoption):
| Policy | Definition | Pros | Cons / verdict |
|---|---|---|---|
| **Benchmark-only (α=0)** | market shown as a benchmark; model unchanged | zero risk, honest calibration check | no accuracy gain — *the safe first app step* |
| **Conservative fixed α (≈0.3–0.5)** | `blend = (1−α)·model + α·market`, fixed | captures much of the gain, keeps model's voice | leaves gain on the table where market is much better — **prototype default** |
| **Regime-aware α** | α larger where model is weak (high entropy / less-modelled confederations / large model–market gap); smaller where strong (Euro/European, low entropy). Mirror the existing `ml_weight_mode:"dynamic"` (`w_eff = w/(1+|elo_gap|/scale)`) | matches the 3G heterogeneity; principled | needs OOS tuning of the regime signal — **target policy** |
| **Confidence-gated α** | use market more when model entropy is high / disagreement large | sharpest | most overfit-prone — refinement only |
**Rules:** α is **fit on a train split and validated OOS (walk-forward)**, never hand-set; **cap α ≤ 0.6**
so the model always keeps a majority voice (identity); the regime signal must beat fixed-α OOS to be adopted.
Document explicitly that capping below the RPS-optimal α=1.0 is a deliberate accuracy-for-identity tradeoff.

## 4. Scoreline-grid integration (reuse existing machinery)
- Set `target = blended W/D/L` and call the **existing** `_reweight_flat_to_wdl(flat, target)` — it scales
  each home/draw/away region of the scoreline grid to the target and renormalises, **preserving the
  within-region (conditional) scoreline shape and total-goal structure**. This is the *same* mechanism the
  ML ensemble already uses → the market blend slots in as another "ensemble member," minimal new surface.
- **No scoreline/totals redesign.** Totals-market integration is explicitly deferred (this phase is W/D/L
  only). Goal-difference tiebreaks and draw scorelines remain governed by the DC grid.

## 5. Champion Monte-Carlo guardrails (the critical risk)
- The blended (sharper) W/D/L feeds the 100k MC via the reweighted grid → changes champion probabilities.
- **Risk:** market odds are sharper → sharpening match W/D/L can **re-concentrate champion probabilities** —
  the exact failure the ×0.55 temperature was added to fix. **Guardrails (must pass before any prod):**
  1. re-run the 4-WC walk-forward; **top-3 concentration stays in the credible band** (~42% target);
  2. **champion-Brier does not regress** vs the frozen baseline;
  3. conservation laws hold (Σ P(champion)=1, Σ P(finalist)=2);
  4. if the blend pushes concentration too high → **cap α** and/or **keep the champion-level temperature
     applied after the blend** (preserve the existing champion-calibration philosophy).
- Build an **offline champion-MC validation harness** (reuse `run_tournament_walkforward_validation.py`).

## 6. Live serving architecture
- **`MarketOddsProvider` interface** (mirrors `src/wc2026/providers/`): `TheOddsApiProvider` +
  `SportmonksOddsProvider`, each returning normalised no-vig 1X2 + metadata (timestamp, n_books, source).
- **Scheduler:** poll the bulk odds endpoint a few ×/day + a final poll near each match's lock time; **cache
  locally** (Upstash Redis already in the stack, or a JSON cache) keyed by fixture.
- **Lock + freeze:** snapshot at kickoff−15min, freeze per match.
- **Fallback chain:** primary feed → secondary feed → **frozen model** (graceful degradation; the model
  works for every match regardless).
- **Quota protection:** bulk endpoint + cache + track `x-requests-remaining`; back off when low.
- **Secret handling:** keys from env only (existing lazy-init pattern); never logged/committed. (Note: a
  stale `THESTATSAPI_KEY` in repo `.env` must be cleaned — use the current `.env.yorian` value.)
- **Team-name mapping:** complete + test a Sportmonks/Odds-API name → lab team-code map for all 48 WC teams
  (the 3G `norm()` alias map is a start, not complete).

## 7. Product identity (honest presentation)
| Mode | What it is | Honesty |
|---|---|---|
| Independent model | lab's own Elo→DC→ML, no market input (current) | "our model" |
| **Market-informed model** | model **blended at a capped weight** with market consensus; still an independent forecast that *listens to* the market where uncertain | **recommended** — label the blend weight, show model-only AND blended, explain market is a calibration anchor where the model is unsure |
| Bookmaker wrapper (α=1.0) | re-showing odds | **REJECT** — not a forecast; abandons "probabilities, not predictions" |
**Recommendation:** if ever integrated, present as **market-informed** with explicit copy (extends the
Phase 2H honesty work): never present odds as "our prediction"; surface both numbers + the weight.

## 8. Implementation risks (and mitigations)
- **Leakage** → snapshot pre-match only (lock time); never in-play/settlement (method already validated).
- **Provider downtime / missing odds** → fallback chain to model; per-match coverage flag.
- **Quota / rate limit** → bulk endpoint + cache + backoff (built in 3G).
- **Schedule changes / postponements** → re-fetch schedule; lock relative to *actual* kickoff.
- **Team-name mapping** → tested 48-team map; unmapped → model fallback + alert.
- **Timestamp ambiguity** → prefer explicit `latest_bookmaker_update`; for The Odds API poll near lock.
- **Recent-era odds gap** (2023–2025 finals lacked usable 1X2 historically) → does NOT block live serving
  (live upcoming odds confirmed present), but blocks *recent historical re-validation* — note it.

## 9. Validation plan (before ANY production)
1. **Offline replay** — chosen α policy on the frozen 3E–3G datasets: OOS proper-score gain holds + champion
   guardrail passes (walk-forward).
2. **Live shadow mode** — for WC2026, fetch live odds + compute blended W/D/L but **do not serve**; log
   model / market / blend / actual per match; measure live OOS RPS/NLL/ECE. (No production change — a logger.)
3. **Champion-MC validation** — 100k MC with blended W/D/L on a historical WC; concentration/Brier/conservation.
4. **Calibration validation** — ECE of blend vs model vs market on held-out + shadow.
5. **Fallback validation** — simulate missing/stale odds → graceful model fallback, no NaN/crash.
Only after 1–5 pass (esp. **live shadow** + **champion guardrail**) is production even considered.

---

## Rejected options (summary)
- **α=1.0 pure-market replacement** — bookmaker wrapper; kills identity. ❌
- **TheStatsAPI live odds** — finished-match only (3H-A). ❌ (keep for post-match xG/odds later).
- **Changing the no-vig method now** — would invalidate the 3E–3G evidence. ❌
- **Totals/scoreline redesign** — out of scope; W/D/L reweight only. ❌
- **Hand-tuned α without OOS fit** — violates the project's evidence discipline. ❌

## Exact implementation phases (when/if approved — NOT now)
- **P1 (lab prototype, offline):** `MarketOddsProvider` interface + de-vig (frozen method) + a **shadow
  logger**; α policies (fixed → regime-aware) fit/validated offline on 3E–3G data. Behind a flag in the
  experimental package; **no production path touched.**
- **P2 (champion-MC + calibration validation):** run guardrail harness; tune α cap to keep champion
  concentration in band.
- **P3 (live shadow on WC2026):** serve nothing; log live model/market/blend/actual; accumulate real OOS.
- **P4 (production proposal):** only if P1–P3 clear, propose a flagged, identity-preserving market-informed
  blend with full rollback — a separate, explicitly-approved phase with version bump + champion re-validation.

## Tests required before production
- de-vig unit tests (identity at single book; normalisation; median aggregation; stale detection);
- blend math tests (α=0 = model; cap enforced; orientation);
- `_reweight_flat_to_wdl` parity (blend target reproduced; scoreline shape preserved);
- champion-MC guardrail tests (concentration band, champion-Brier non-regression, conservation);
- fallback tests (missing/stale odds → model, no NaN);
- live-shadow integration test (logger writes, no production mutation);
- team-name mapping coverage test (all 48 WC teams resolve).

## Final recommendation: **READY_FOR_MODEL_LAB_PROTOTYPE**
The evidence supports building an **offline lab prototype + live shadow logger** (behind a flag, in the
experimental package), **not** a production change. It is **not** READY_FOR_PRODUCTION_IMPLEMENTATION yet
because: champion-MC impact is unvalidated, the regime-aware α is untuned, live shadow has not run, the
48-team name map is incomplete, the recent-era historical odds gap stands, the Sportmonks-paid-vs-OddsAPI
cost choice is open, and the **market-informed-vs-independent identity call is Yorian's product decision**.
The prototype + shadow mode generate exactly the evidence needed to make the production call later — with no
risk to the frozen, deployed model. Model math remains FROZEN until then.
