"""Phase 3A — leakage-free feature derivation (offline). No model/config/data/probability change."""
import pandas as pd

from wc2026.experimental.match_features import build_rolling_features, FEATURES


def _const_elo(team, before_date=None):
    return 1500.0


DF = pd.DataFrame([
    # date, home, away, neutral, home_goals, away_goals
    ("2020-01-01", "A", "B", False, 3, 0),
    ("2020-01-08", "A", "C", True, 2, 2),
    ("2020-01-15", "B", "A", False, 0, 1),
], columns=["date", "home_team", "away_team", "neutral", "home_goals", "away_goals"])


def test_first_match_uses_priors_only_no_leak():
    f = build_rolling_features(DF, _const_elo)
    # first match: no prior history -> gf/ga/form diffs are 0 (defaults cancel), rest default
    assert f.loc[0, "gf_diff"] == 0.0 and f.loc[0, "ga_diff"] == 0.0 and f.loc[0, "form_diff"] == 0.0


def test_rolling_reflects_only_past_matches():
    f = build_rolling_features(DF, _const_elo)
    # match 2 (A vs C): A has ONE prior match (won 3-0) -> A gf=3, ga=0, pts=3; C has none (defaults)
    assert f.loc[1, "gf_diff"] == 3.0 - 1.2     # A.gf(3) - C.gf(default 1.2)
    assert f.loc[1, "ga_diff"] == 0.0 - 1.2
    assert f.loc[1, "form_diff"] == 3.0 - 1.3


def test_outcome_and_total_correct():
    f = build_rolling_features(DF, _const_elo)
    assert list(f["outcome"]) == [0, 1, 2]          # home win, draw, away win
    assert list(f["total_goals"]) == [3, 4, 1]


def test_neutral_flag_and_elo_home_adv():
    f = build_rolling_features(DF, _const_elo)
    assert f.loc[0, "neutral"] == 0.0 and f.loc[1, "neutral"] == 1.0
    # non-neutral: elo_diff = (1500+100-1500)/400 = 0.25 ; neutral: 0.0
    assert abs(f.loc[0, "elo_diff"] - 0.25) < 1e-9
    assert abs(f.loc[1, "elo_diff"] - 0.0) < 1e-9


def test_feature_columns_present():
    f = build_rolling_features(DF, _const_elo)
    for c in FEATURES:
        assert c in f.columns
