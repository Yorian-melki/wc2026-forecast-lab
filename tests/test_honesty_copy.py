"""Phase 2H — reporting / model-honesty copy (display-only).

Verifies the honesty framing exists with EN+FR parity, the diagnostic tooltips are wired, the
technical "tested and won't chase" block is present, and the Scorecard + Model Lab pages still render
with no raw 'nan'. No model / probability / scorecard-calculation / data / config change.
"""
import os
import re
import warnings
from pathlib import Path

os.environ.setdefault("WC2026_DISABLE_PERSIST", "1")
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")

# user-facing keys must be defined in BOTH the EN and FR i18n dicts (parity)
PARITY_KEYS = ["sc_diag_note", "sc_ceiling_note", "sc_smalln_note",
               "sc_t1_help", "sc_t3_help", "sc_rank_help"]


def test_honesty_keys_have_en_fr_parity():
    for k in PARITY_KEYS:
        # the dict-definition form `"key":` should appear exactly twice (EN + FR)
        assert APP_PY.count(f'"{k}":') == 2, f"{k} not defined in exactly 2 dicts (EN+FR)"


def test_diagnostic_tooltips_wired_on_metrics():
    assert 'help=t("sc_t1_help")' in APP_PY
    assert 'help=t("sc_t3_help")' in APP_PY
    assert 'help=t("sc_rank_help")' in APP_PY


def test_scorecard_renders_honesty_notes():
    assert 'st.caption(t("sc_diag_note"))' in APP_PY
    assert 'st.caption(t("sc_ceiling_note"))' in APP_PY
    assert 'st.caption(t("sc_smalln_note"))' in APP_PY


def test_rank_and_exact_framed_as_diagnostics_not_targets():
    # EN copy must explicitly say these are diagnostics, not targets.
    assert "diagnostics**, not targets" in APP_PY
    assert "near-irreducible" in APP_PY


def test_limitations_block_records_frozen_math_and_negative_results():
    assert "What we tested — and won't chase" in APP_PY
    assert "Rejected (Phase 2B)" in APP_PY
    assert "Not shipped (Phase 2F)" in APP_PY
    assert "Model math frozen (Phase 2D / 2G)" in APP_PY


def test_scorecard_and_modellab_render_no_nan():
    from streamlit.testing.v1 import AppTest
    nan = re.compile(r"\bnan\b", re.I)
    at = AppTest.from_file("app.py", default_timeout=240)
    at.run()
    for page in ["📊 Scorecard", "🧮 Model Lab"]:
        at.session_state["page_nav"] = page
        at.run()
        assert not at.exception, f"{page} raised: {at.exception}"
        body = " ".join(
            str(getattr(e, "value", ""))
            for attr in ("markdown", "caption", "text")
            for e in getattr(at, attr)
        )
        assert not nan.search(body), f"raw 'nan' visible on {page}"
