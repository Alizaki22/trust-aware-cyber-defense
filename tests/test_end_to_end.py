import json

import pytest
from pydantic import ValidationError

from src.api import analyze_event
from src.data.unsw_nb15 import prepare
from src.evaluation.runner import run_calibration, run_evaluation
from src.models import FinalRecommendation
from src.pipeline import build_coordinator


def test_demo_events_end_to_end(stub_config, demo_events):
    coordinator = build_coordinator(stub_config, run_id="t")
    for event in demo_events:
        rec = analyze_event(event, coordinator)
        FinalRecommendation.model_validate(rec.model_dump(mode="json"))
        assert rec.is_mock and {f.agent for f in rec.agent_findings} == {"detection", "intelligence", "behavioral"}
        assert len(rec.verification_results) == len(rec.trust_scores) == 3
    known_bad = analyze_event(demo_events[0], coordinator)
    assert {f.agent: f.verdict for f in known_bad.agent_findings}["intelligence"] == "malicious"


def test_invalid_input_is_rejected(stub_config):
    with pytest.raises(ValidationError):
        analyze_event({"event_id": "x"}, build_coordinator(stub_config, run_id="t"))


def test_agent_crash_does_not_break_pipeline(stub_config, demo_events):
    coordinator = build_coordinator(stub_config, run_id="t")

    class Broken:
        name, model_id = "behavioral", "broken"
        def analyze(self, event):
            raise RuntimeError("boom")
        def error_finding(self, event, error):
            return coordinator.agents["intelligence"].error_finding(event, error).model_copy(update={"agent": "behavioral"})
    coordinator.agents["behavioral"] = Broken()
    rec = coordinator.process_event(demo_events[0])
    behavioral = [f for f in rec.agent_findings if f.agent == "behavioral"][0]
    assert behavioral.error and "boom" in behavioral.error


def test_calibrate_then_evaluate_writes_reproducible_run(stub_config):
    prepare(stub_config.data_dir, log=lambda *_: None)
    cal = run_calibration(stub_config, log=lambda *_: None)
    assert json.loads(cal.read_text())["agents"]["detection"]["counted"] > 0
    run_dir = run_evaluation(stub_config, run_id="e2e", log=lambda *_: None)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["is_mock"] is True
    assert set(metrics) >= {"macro_f1_detection", "schema_valid_rate", "evidence_grounding_rate", "trust_impact_rate"}
    config = json.loads((run_dir / "config.json").read_text())
    assert "llm_api_key" not in config and config["trust_history_source"].endswith(".json")
    lines = (run_dir / "results.jsonl").read_text().splitlines()
    assert len(lines) == metrics["n_events"] > 0
