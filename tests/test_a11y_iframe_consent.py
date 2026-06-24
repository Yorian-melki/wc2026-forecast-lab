"""Phase 1D-A — static a11y assertions for invisible functional iframes + cookie banner.

Display-only checks. No model / config / forecast / scorecard / data involved.
Deterministic source-text assertions, no browser, no AppTest.
"""
from pathlib import Path

from wc2026 import web_analytics

ROOT = Path(__file__).resolve().parents[1]
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")
ANALYTICS_PY = Path(web_analytics.__file__).read_text(encoding="utf-8")


def test_analytics_shim_labels_and_hides_iframe():
    # The injected analytics shim must label + hide the invisible (height=0) "st.iframe".
    assert "window.frameElement" in ANALYTICS_PY
    assert "fe.title=" in ANALYTICS_PY
    assert "aria-hidden" in ANALYTICS_PY
    assert "tabindex" in ANALYTICS_PY


def test_countdown_iframe_labelled_and_hidden():
    # app.py countdown components.html iframe likewise labelled + hidden from a11y tree.
    assert "window.frameElement" in APP_PY
    assert "_fe.title=" in APP_PY
    assert "aria-hidden" in APP_PY


def test_consent_banner_mobile_safe_area_and_overflow():
    # Banner must respect mobile safe-area and never cover the full viewport.
    assert "env(safe-area-inset-bottom)" in ANALYTICS_PY
    assert "max-height" in ANALYTICS_PY
    assert "overflow:auto" in ANALYTICS_PY


def test_consent_banner_is_aria_region():
    assert "role','region'" in ANALYTICS_PY
    assert "aria-label" in ANALYTICS_PY


def test_consent_buttons_remain_semantic():
    # Accept/Decline must stay real <button> elements, not links.
    assert 'id="wc-accept"' in ANALYTICS_PY
    assert 'id="wc-reject"' in ANALYTICS_PY
    assert "<button" in ANALYTICS_PY
