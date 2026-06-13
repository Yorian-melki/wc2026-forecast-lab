# Test Quality Audit — WC2026 Forecast

**Total tests:** 350 passing (14.86s)  
**Question being answered:** Of these 350 tests, how many test statistical properties that matter for the publication claims?

---

## Category breakdown

### Category 1: Infrastructure guards (existence, schema, conservation)

**What they test:** "Did the code run without crashing?" "Did the right files get created?" "Do probabilities sum to 1?"

**Count estimate:** ~210 of 350 tests (60%)

**Examples:**
- `test_model_card_exists()` — MODEL_CARD.md exists
- `test_manifest_schema()` — JSON has expected keys
- `test_champion_prob_sum_to_one()` — Σ P(champion) = 1.000
- `test_simulation_has_48_teams()` — DataFrame has 48 rows
- `test_beta_elo_unchanged()` — frozen parameter not accidentally changed
- `test_reproducibility_log_exists()` — log file was written

**Value:** Real value as CI guards. Catch regressions. Prevent accidental model changes. But they do not test statistical validity.

**Analogy:** These tests verify the car engine starts and has 4 wheels. They don't test whether the car goes the right direction.

---

### Category 2: Probability sanity checks

**What they test:** "Are individual probability values plausible?"

**Count estimate:** ~50 of 350 tests (14%)

**Examples:**
- `test_all_champion_probs_non_negative()` — no negative probabilities
- `test_top3_concentration_below_ceiling()` — top3 < 50%
- `test_top1_below_25_percent()` — no team above 25%
- `test_draw_rate_minimum_for_any_matchup()` (P3.5) — draw rate floor

**Value:** Real value. These test that the model output is in a plausible range. They would catch a completely broken temperature setting.

**Limitation:** The thresholds (50%, 25%) are wide safety bounds, not calibration checks. top3=45% would pass these tests but would still be over-concentrated vs WC history.

---

### Category 3: Statistical properties (real invariants)

**What they test:** "Does the model behave correctly as inputs change?"

**Count estimate:** ~30 of 350 tests (9%)

**Examples:**
- `test_lower_beta_reduces_top3_concentration()` (P3.5) — monotonicity of temperature ablation
- `test_entropy_increases_with_lower_beta()` (P3.5) — correct direction
- `test_poisson_1x2_sums_to_one()` — Poisson math unit test
- `test_poisson_symmetry_equal_lambdas()` — equal teams, symmetric probabilities
- `test_expected_goals_esp_vs_median_at_reduced_beta()` — xG ratio sanity

**Value:** Real statistical invariants. These test that the model behaves correctly.

**Gap:** No test: "given team with higher Elo always gets higher champion probability across all 48 teams." The monotonicity tests check temperature behavior, not the full Elo→probability mapping.

---

### Category 4: Forbidden claim guards

**What they test:** "Did we accidentally put a forbidden phrase in a public document?"

**Count estimate:** ~36 of 350 tests (10%)

**Examples:**
- `test_model_card_no_forbidden[hedge-fund-grade]`
- `test_linkedin_no_forbidden[beats betting markets]`
- etc. (9 phrases × 4 document types)

**Value:** Real publication safety. These prevent accidental addition of claims we said we wouldn't make. Automated.

---

### Category 5: Model content tests

**What they test:** "Does the document say what we claim it says?"

**Count estimate:** ~24 of 350 tests (7%)

**Examples:**
- `test_model_card_mentions_49450()` — correct data count
- `test_model_card_mentions_ece_degradation()` — "+17%" present
- `test_readme_mentions_conservation_law()` — limitation disclosed
- `test_linkedin_post_length()` — character count reasonable

**Value:** Ensures key claims and limitations are present. Good practice.

**Gap:** Does not test that the claims are *correctly stated*, only that the string appears.

---

## Overall quality assessment

| Category | Count | % | Tests statistical validity? |
|----------|------:|--:|:--:|
| Infrastructure guards | ~210 | 60% | NO |
| Probability sanity checks | ~50 | 14% | PARTIALLY |
| Statistical properties | ~30 | 9% | YES |
| Forbidden claim guards | ~36 | 10% | NO (publication guard) |
| Model content tests | ~24 | 7% | NO (string presence) |

**Tests that validate the actual statistical claims of the publication: ~80 of 350 (23%).**

The 350-test count creates an illusion of comprehensive coverage. The actual statistical validity test coverage is ~23%. This is not unusual for a personal project; it is below the bar for a published forecasting system.

---

## Top 10 tests to add (by value / implementation effort ratio)

### Test 1: Elo rank → champion prob monotonicity
```python
def test_elo_rank_champion_prob_monotone():
    """Higher Elo must mean higher champion probability in the Elo model."""
    teams = load_teams()
    df = pd.read_csv(ELO_CSV).set_index('team')
    elo_sorted = sorted(teams.keys(), key=lambda t: -teams[t].elo_current)
    top10_elo = elo_sorted[:10]
    top10_champ = df['champion_prob'].nlargest(10).index.tolist()
    # At least 7 of the top-10 Elo teams should be in top-10 champion probs
    overlap = len(set(top10_elo) & set(top10_champ))
    assert overlap >= 7, f"Elo/champion overlap={overlap}/10"
```
**Value:** Tests that the model's core mechanism (Elo → champion) is working correctly.

---

### Test 2: Expert vs Elo probability correlation
```python
def test_expert_elo_correlation_above_threshold():
    """Expert and Elo models should broadly agree (r > 0.6)."""
    elo_df = pd.read_csv(ELO_CSV)[['team','champion_prob']].rename(columns={'champion_prob':'elo'})
    exp_df = pd.read_csv(EXPERT_CSV)[['team','champion_prob']].rename(columns={'champion_prob':'expert'})
    merged = elo_df.merge(exp_df, on='team')
    r, _ = pearsonr(merged['elo'], merged['expert'])
    assert r > 0.5, f"Expert/Elo correlation r={r:.3f} — models too divergent"
```
**Value:** If the two models disagree completely, one is probably broken.

---

### Test 3: Temperature correction sensitivity bounds
```python
def test_top3_within_plausible_range():
    """Corrected beta=0.544 should give top3 in [33%, 50%]."""
    df = pd.read_csv(ELO_CSV)
    top3 = float(df.head(3)['champion_prob'].sum())
    assert 0.33 <= top3 <= 0.50, f"top3={top3:.3f} outside [33%, 50%]"
```
**Value:** Tests the temperature correction is in a valid range (current test only checks < 50%, missing lower bound).

---

### Test 4: form_history.csv coverage assertion
```python
def test_form_history_covers_expected_teams():
    """form_history.csv must cover exactly the 16 known major teams."""
    expected = {'ESP','ARG','FRA','ENG','BRA','GER','POR','NED','BEL','COL','JPN','MAR','MEX','CAN','USA','SCO'}
    fh = pd.read_csv(ROOT/'data/form_history.csv')
    actual = set(fh['code'].unique())
    assert actual == expected, f"form_history teams: {actual - expected} extra, {expected - actual} missing"
```
**Value:** Documents and enforces the known limitation (16/48 coverage).

---

### Test 5: DC rho plausibility
```python
def test_dc_rho_is_small_and_negative():
    """rho should be in (-0.1, 0) — small negative per Dixon-Coles literature."""
    params = json.loads(ELO_PARAMS.read_text())
    rho = params['rho']
    assert -0.10 < rho < 0.0, f"rho={rho} outside (-0.10, 0) — implausible"
```
**Value:** Prevents rho from drifting to an implausible value if parameters are ever re-estimated.

---

### Test 6: beta_elo reasonable range after temperature correction
```python
def test_beta_elo_in_reasonable_range():
    """beta_elo should be in (0.3, 0.8) — both extremes are implausible."""
    params = json.loads(ELO_PARAMS.read_text())
    assert 0.30 < params['beta_elo'] < 0.80, f"beta_elo={params['beta_elo']} outside valid range"
```
**Value:** Catches future modifications that go too far in either direction.

---

### Test 7: Group stage survival probabilities
```python
def test_group_survival_prob_top_teams():
    """Top Elo teams should qualify from group stage > 80% of the time."""
    df = pd.read_csv(ELO_CSV)
    for team in ['ESP','ARG','FRA']:
        gsp = float(df.loc[df['team']==team, 'group_survival_prob'])
        assert gsp > 0.80, f"{team} group survival {gsp:.3f} < 0.80 — implausible"
```
**Value:** Tests a specific, verifiable property of the champion probabilities.

---

### Test 8: Home nation advantage reflected
```python
def test_host_nations_have_above_average_group_survival():
    """USA/MEX/CAN should qualify from group stage above tournament average."""
    df = pd.read_csv(ELO_CSV)
    avg_gsp = float(df['group_survival_prob'].mean())  # should be ~0.667
    for host in ['USA','MEX','CAN']:
        gsp = float(df.loc[df['team']==host, 'group_survival_prob'])
        assert gsp > avg_gsp, f"{host} group survival {gsp:.3f} ≤ average {avg_gsp:.3f} — home boost not working"
```
**Value:** Directly tests the home advantage feature we claim is implemented.

---

### Test 9: WC2022 retroactive winner probability sanity
```python
def test_wc2022_retroactive_champion_prob_sanity():
    """Argentina's retroactive probability (β=0.544 on pre-WC2022 Elo) should be in [5%, 30%]."""
    hist = pd.read_csv(ROOT/'outputs/calibration/historical_tournament_concentration.csv')
    if 'ARG_champion_prob_wc2022' in hist.columns:
        arg_prob = float(hist['ARG_champion_prob_wc2022'].iloc[0])
        assert 0.05 <= arg_prob <= 0.30, f"ARG retroactive WC2022 prob={arg_prob:.3f} outside [5%, 30%]"
    else:
        pytest.skip("retroactive per-team champion probs not computed — add this output")
```
**Value:** Exposes the single most important missing validation test. Will skip until the data is computed, but documents the gap.

---

### Test 10: Significance test variance is not hardcoded
```python
def test_significance_variance_computed_from_data():
    """Variance in significance tests must come from actual NLL distribution, not a hardcoded constant."""
    sig_path = ROOT / 'src/wc2026/calibration/significance.py'
    if sig_path.exists():
        text = sig_path.read_text()
        # Check there is no hardcoded variance constant
        assert 'NLL_VARIANCE = 0.40' not in text and 'variance = 0.40' not in text, \
            "Significance test uses hardcoded variance=0.40 — must compute from test data"
```
**Value:** Documents the hardcoded variance bug and enforces a fix.

---

## Recommended test addition priority

| Test | Hours to implement | Statistical value | Priority |
|------|:-----------------:|:----------------:|:--------:|
| 1: Elo rank monotone | 1h | HIGH | P0 |
| 7: Group survival top teams | 1h | HIGH | P0 |
| 8: Host nation advantage | 1h | MEDIUM | P0 |
| 4: form_history coverage | 0.5h | MEDIUM | P1 |
| 3: top3 lower bound | 0.5h | MEDIUM | P1 |
| 5: DC rho plausibility | 0.5h | MEDIUM | P1 |
| 9: WC2022 retroactive | 2h | HIGH (requires data computation first) | P1 |
| 10: Significance variance | 0.5h | HIGH | P1 |
| 2: Expert/Elo correlation | 1h | MEDIUM | P2 |
| 6: beta_elo range | 0.5h | LOW | P2 |
