"""
Test that app.py does not contain forbidden overclaim words/phrases.
These checks ensure the site is honest about model limitations.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"


def _get_app_text() -> str:
    return APP_PY.read_text(encoding="utf-8")


FORBIDDEN_PHRASES = [
    "Quantum Analytics",
    "quantum analytics",
    "industry-grade",
    "market-grade",
    "investment-grade probability",
    "real xG",           # must always say "proxy" when using shots-based xG
    "live injuries",     # we don't have live injury data
    "10/10",             # maturity score cannot claim 10/10
]

REQUIRED_PHRASES = [
    "Elo",               # model type must be disclosed
    "Monte Carlo",       # simulation method must be disclosed
    "quality",           # data quality must be mentioned
    "maturity",          # maturity score must be present
]


def test_no_forbidden_phrases():
    text = _get_app_text()
    violations = []
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            # Find line number
            for i, line in enumerate(text.splitlines(), 1):
                if phrase in line:
                    violations.append(f"Line {i}: '{phrase}'")
    assert not violations, f"Forbidden phrases found in app.py:\n" + "\n".join(violations)


def test_required_phrases_present():
    text = _get_app_text()
    missing = [p for p in REQUIRED_PHRASES if p not in text]
    assert not missing, f"Required phrases missing from app.py: {missing}"


def test_maturity_score_not_inflated():
    """Global maturity score shown in sidebar must not exceed 7.5."""
    text = _get_app_text()
    import re
    # Look only for the sidebar maturity line pattern: "X.XX / 10</span>"
    # This excludes per-dimension scores like "Reproducibility 8.0/10"
    sidebar_matches = re.findall(r"(\d+\.\d+)\s*/\s*10</span>", text)
    for m in sidebar_matches:
        score = float(m)
        assert score <= 7.5, (
            f"Global maturity score {score}/10 found in app.py sidebar — "
            "must not exceed 7.5 until ECE calibration and full validation are done."
        )


def test_data_quality_page_exists():
    """Data Quality page must be registered in the navigation."""
    text = _get_app_text()
    assert "Data Quality" in text, "Data Quality page must be in navigation"
    assert "provider_status" in text.lower() or "Provider Status" in text, \
        "Data Quality page must show provider status"
