import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models import AgentFinding, FinalRecommendation, SecurityEvent, SimulatedAction

ROOT = Path(__file__).resolve().parents[1]
BASE = dict(event_id="e1", timestamp="2026-01-01T00:00:00Z", event_type="network_flow", raw_content="proto=tcp")


def test_valid_event():
    assert SecurityEvent(**BASE, source_ip="203.0.113.5", destination_port=443).destination_port == 443


@pytest.mark.parametrize("bad", [{"source_ip": "not-an-ip"}, {"destination_port": 70000},
                                 {"raw_content": ""}, {"event_id": ""}, {"timestamp": "yesterday"}])
def test_invalid_event_rejected(bad):
    with pytest.raises(ValidationError):
        SecurityEvent(**{**BASE, **bad})


def test_simulated_action_can_never_be_executed():
    with pytest.raises(ValidationError):
        SimulatedAction(description="x", executed=True)


def test_finding_enums_enforced():
    with pytest.raises(ValidationError):
        AgentFinding(agent="detection", event_id="e", verdict="very bad", classification="x",
                     evidence="", confidence="high", reasoning="r")
    with pytest.raises(ValidationError):
        AgentFinding(agent="verification", event_id="e", verdict="benign", classification="x",
                     evidence="", confidence="high", reasoning="r")


def test_frontend_fixtures_match_the_contract():
    for path in sorted((ROOT / "docs/frontend/fixtures").glob("scenario_*.json")):
        data = json.loads(path.read_text())
        SecurityEvent.model_validate(data["event"])
        FinalRecommendation.model_validate(data["result"])
