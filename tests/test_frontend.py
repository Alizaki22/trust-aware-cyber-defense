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


def _render_crafted_result():
    """Runs inside AppTest: render a result whose model-derived text contains Markdown."""
    import json
    from pathlib import Path

    from frontend.render import render_result
    from src.models import FinalRecommendation, SecurityEvent

    root = Path.cwd()
    data = json.loads((root / "docs/frontend/fixtures/scenario_01.json").read_text())
    payload = "**bold** [click](http://evil.example) <b>x</b>"
    result = data["result"]
    result["classification"] = payload
    result["simulated_action"]["description"] = payload
    result["agent_findings"][0]["classification"] = payload
    result["agent_findings"][0]["error"] = payload
    result["verification_results"][0]["reason"] = payload
    render_result(SecurityEvent.model_validate(data["event"]), FinalRecommendation.model_validate(result))


def test_model_generated_text_is_rendered_literally():
    """R-08: Markdown in model/event-derived text is escaped, never interpreted."""
    from frontend.view import plain
    at = AppTest.from_function(_render_crafted_result, default_timeout=60).run()
    assert not at.exception
    escaped = plain("**bold** [click](http://evil.example) <b>x</b>")
    rendered = ([e.value for e in at.subheader] + [e.value for e in at.info] + [e.value for e in at.error]
                + [e.value for e in at.caption])
    assert any(escaped in text for text in at.subheader.values)
    assert any(escaped in text for text in at.info.values)
    assert any(escaped in text for text in at.error.values)
    assert not any("**bold**" in text and escaped not in text for text in rendered)


def test_sidebar_warns_when_trust_is_not_calibrated(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_BACKEND", "stub")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))  # no calibration file here
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("not calibrated" in w.value for w in at.sidebar.warning)
