from pathlib import Path

from streamlit.testing.v1 import AppTest

from frontend.view import trust_text, verdict_label

APP = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")


def test_view_helpers_never_use_percent_or_colour_only():
    assert trust_text(0.6912) == "0.69" and "%" not in trust_text(0.5)
    assert verdict_label("unknown", "no_match") == "⚪ No known indicator"
    assert verdict_label("malicious").endswith("Malicious")


def test_app_live_pipeline_with_stub(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "stub")
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception and at.subheader, "result should render"


def test_app_saved_examples_mode():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Saved examples").run()
    assert not at.exception and at.subheader


def test_app_reports_invalid_pasted_event(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "stub")
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.text_area[0].input('{"event_id": "x", "source_ip": "nope"}').run()
    at.button[0].click().run()
    assert not at.exception and at.error
