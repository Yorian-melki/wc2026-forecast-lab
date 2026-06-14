"""
Tests for provider freshness and live data file health.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


class TestSourceFreshnessFiles:
    def test_elo_live_params_exists(self):
        p = ROOT / "data" / "elo_live_params.json"
        assert p.exists(), "elo_live_params.json must exist — run scripts/update_live_data.py"

    def test_elo_live_params_has_valid_elos(self):
        p = ROOT / "data" / "elo_live_params.json"
        if not p.exists():
            import pytest; pytest.skip("elo_live_params.json not found")
        data = json.loads(p.read_text())
        assert "team_elos" in data
        assert len(data["team_elos"]) >= 48, "Must have Elo for all 48 WC2026 teams"
        for code, elo in data["team_elos"].items():
            assert isinstance(elo, (int, float))
            assert 800 <= elo <= 3000, f"{code} Elo={elo} out of expected range"

    def test_elo_live_params_has_calibrated_beta(self):
        """Production beta_elo must be in range [0.3, 1.5]."""
        p = ROOT / "data" / "elo_live_params.json"
        if not p.exists():
            import pytest; pytest.skip("elo_live_params.json not found")
        data = json.loads(p.read_text())
        beta = data.get("beta_elo", 0)
        assert 0.3 <= beta <= 1.5, f"beta_elo={beta} out of expected range [0.3, 1.5]"

    def test_wc2026_live_json_has_matches(self):
        p = ROOT / "data" / "wc2026_live.json"
        assert p.exists()
        data = json.loads(p.read_text())
        matches = data.get("completed_matches", [])
        assert isinstance(matches, list)

    def test_live_summary_csv_conservation(self):
        """Champion probability sum must equal 1.0 within tolerance."""
        import pandas as pd
        p = ROOT / "outputs" / "tournament_run" / "live_summary.csv"
        if not p.exists():
            import pytest; pytest.skip("live_summary.csv not found")
        df = pd.read_csv(p)
        total = df["champion_prob"].sum()
        assert abs(total - 1.0) < 0.001, f"Champion prob sum = {total}, expected 1.0"

    def test_live_summary_all_teams_present(self):
        """All 48 WC2026 teams must appear in live summary."""
        import pandas as pd
        p = ROOT / "outputs" / "tournament_run" / "live_summary.csv"
        teams_p = ROOT / "data" / "teams.csv"
        if not p.exists() or not teams_p.exists():
            import pytest; pytest.skip("live_summary.csv or teams.csv not found")
        summary = pd.read_csv(p)
        teams = pd.read_csv(teams_p)
        summary_codes = set(summary["team"])
        team_codes = set(teams["code"])
        missing = team_codes - summary_codes
        assert not missing, f"Teams missing from live_summary.csv: {missing}"

    def test_backtest_json_exists_and_valid(self):
        """Historical backtest results must exist and contain WC2022 data."""
        p = ROOT / "outputs" / "audit" / "wc_historical_backtest.json"
        if not p.exists():
            import pytest; pytest.skip("wc_historical_backtest.json not found")
        data = json.loads(p.read_text())
        assert "tournaments" in data
        assert "wc2022" in data["tournaments"]
        wc22 = data["tournaments"]["wc2022"]
        assert "brier_scores" in wc22
        # Champion Brier is a per-team mean over 48 teams; sanity-check it is a finite small value
        # and that the model ranked the actual champion sensibly. No 0.250 coin-flip framing — the
        # honest null for this metric is the uniform 1/48 baseline (~0.0204), not 0.250.
        brier_champ = wc22["brier_scores"]["champion"]
        assert 0.0 < brier_champ < 0.05, (
            f"WC2022 champion Brier={brier_champ:.4f} outside the sane range for a 48-team mean-Brier."
        )
        assert wc22.get("actual_champion_rank", 99) <= 8, (
            "WC2022 actual champion (ARG) should rank within the model's top 8 picks."
        )

    def test_bootstrap_ci_json_exists(self):
        p = ROOT / "outputs" / "audit" / "beta_bootstrap_ci.json"
        if not p.exists():
            import pytest; pytest.skip("beta_bootstrap_ci.json not found")
        data = json.loads(p.read_text())
        assert "bootstrap_results" in data
        br = data["bootstrap_results"]["beta_elo"]
        assert br["ci_95_lo"] < br["ci_95_hi"]
        # CI should be narrow (model stable)
        ci_width = br["ci_95_hi"] - br["ci_95_lo"]
        assert ci_width < 0.5, f"Beta CI too wide: {ci_width:.4f} — model unstable"


class TestProviderFiles:
    def test_all_live_dir_files_parseable(self):
        live_dir = ROOT / "data" / "live"
        if not live_dir.exists():
            import pytest; pytest.skip("data/live/ not generated")
        for json_file in live_dir.glob("*.json"):
            try:
                json.loads(json_file.read_text())
            except json.JSONDecodeError as e:
                raise AssertionError(f"{json_file.name} is not valid JSON: {e}")

    def test_provider_status_has_required_providers(self):
        p = ROOT / "data" / "live" / "provider_status.json"
        if not p.exists():
            import pytest; pytest.skip("provider_status.json not generated")
        data = json.loads(p.read_text())
        providers = data.get("providers", {})
        required = {"openfootball", "api_football"}
        missing = required - set(providers.keys())
        assert not missing, f"Missing providers in status: {missing}"
