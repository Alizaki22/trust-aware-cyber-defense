import pytest

from src.agents.verification import VerificationAgent
from src.models import AgentFinding, SecurityEvent

EVENT = SecurityEvent(event_id="e", timestamp="2026-01-01T00:00:00Z", event_type="network_flow",
                      raw_content="proto=tcp, sbytes=258, sttl=252", source_ip="203.0.113.45")


def finding(**kw):
    base = dict(agent="detection", event_id="e", verdict="malicious", classification="DoS",
                evidence="proto=tcp, sbytes=258", confidence="high", reasoning="r")
    return AgentFinding(**{**base, **kw})


@pytest.mark.parametrize("kw, status", [
    ({}, "verified_consistent"),
    ({"evidence": "sbytes=258.0"}, "verified_consistent"),               # numeric comparison
    ({"evidence": "source_ip=203.0.113.45", "agent": "intelligence"}, "verified_consistent"),
    ({"evidence": "sbytes=999"}, "verified_inconsistent"),               # altered value
    ({"evidence": "dbytes=5"}, "verified_inconsistent"),                 # field not in event
    ({"evidence": "high traffic volume"}, "verified_inconsistent"),      # not field=value
    ({"evidence": ""}, "verified_inconsistent"),                         # uncited conclusion
    ({"evidence": "", "verdict": "unknown"}, "inconclusive"),            # abstention
    ({"error": "timeout", "verdict": "unknown", "evidence": ""}, "inconclusive"),
    ({"classification": "Normal", "verdict": "malicious"}, "verified_inconsistent"),
    ({"classification": "Exploits", "verdict": "benign"}, "verified_inconsistent"),
])
def test_rules(kw, status):
    assert VerificationAgent().verify(finding(**kw), EVENT).status == status
