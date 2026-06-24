"""Phase 1C guard: no raw 'nan' (or NaN/None artifacts) is ever shown to users — especially on
the Nation DNA squad-DNA fields, which previously rendered "nan" for teams without StatsBomb
coverage. Display-only; does not touch the model/data.
"""
import os
import re
import warnings

import pytest

os.environ.setdefault("WC2026_DISABLE_PERSIST", "1")  # never let an AppTest run mutate live data
warnings.filterwarnings("ignore")

from streamlit.testing.v1 import AppTest  # noqa: E402

_NAN = re.compile(r"\bnan\b", re.I)

PAGES = ["🚀 Release Status", "🏆 Champion Tracker", "📊 Scorecard", "⚽ Live Standings",
         "🎯 Match Predictor", "🧬 Nation DNA", "⚔️ Head-to-Head", "📜 Historical Records",
         "🔮 Bracket Paths", "🧮 Model Lab", "📡 Data Quality"]


def _body(at) -> str:
    parts = []
    for attr in ("markdown", "caption", "text"):
        parts += [str(getattr(e, "value", "")) for e in getattr(at, attr)]
    return " ".join(parts)


def _team_codes():
    try:
        import pandas as pd
        return sorted(c for c in pd.read_csv("data/teams.csv")["code"].dropna().tolist())
    except Exception:
        return ["ESP", "ARG", "FRA", "ALG", "JOR", "CUW", "UZB", "HAI"]


def test_no_raw_nan_across_all_pages():
    at = AppTest.from_file("app.py", default_timeout=240)
    at.run()
    for page in PAGES:
        at.session_state["page_nav"] = page   # stable nav (radio[0] isn't always the nav radio)
        at.run()
        assert not at.exception, f"{page} raised: {at.exception}"
        assert not _NAN.search(_body(at)), f"raw 'nan' visible on page {page}"


def test_no_raw_nan_nation_dna_every_team():
    codes = _team_codes()
    at = AppTest.from_file("app.py", default_timeout=240)
    at.run()
    for c in codes:
        at.session_state["dna_sel"] = c
        at.session_state["page_nav"] = "🧬 Nation DNA"
        at.run()
        assert not at.exception, f"Nation DNA {c} raised: {at.exception}"
        assert not _NAN.search(_body(at)), f"raw 'nan' in Nation DNA for team {c}"


def test_format_optional_number_helper():
    # import the helper without running the whole Streamlit script
    import importlib.util
    from pathlib import Path
    src = Path("app.py").read_text()
    start = src.index("def format_optional_number")
    end = src.index("\ndef ", start + 1)
    ns = {"math": __import__("math")}
    exec(src[start:end], ns)  # noqa: S102 — isolated extraction of one pure helper for testing
    f = ns["format_optional_number"]
    assert f(float("nan"), "{:.2f}", "X") == "X"
    assert f(None, "{:.2f}", "X") == "X"
    assert f(float("inf"), "{:.2f}", "X") == "X"
    assert f("not a number", "{:.2f}", "X") == "X"
    assert f(6.0, "{:.2f}", "X") == "6.00"
    assert f(0.3, "{:.0%}", "X") == "30%"
