import json

import pandas as pd

from src.agents.behavioral import BehavioralAgent
from src.agents.detection import DetectionAgent
from src.agents.intelligence import IntelligenceAgent
from src.agents.prompts import DETECTION_INSTRUCTION
from src.data.unsw_nb15 import create_instruction_example, format_raw_content, to_security_event
from src.models import SecurityEvent
from src.utils.llm_client import LLMError, StubLLMClient

GOOD = json.dumps({"verdict": "malicious", "classification": "DoS", "evidence": "proto=udp",
                   "confidence": "high", "reasoning": "r"})


def event(**kw):
    base = dict(event_id="e1", timestamp="2026-01-01T00:00:00Z", event_type="network_flow",
                raw_content="dur=0.1, proto=udp, service=dns, state=INT, spkts=2, dpkts=0, sbytes=146, "
                            "dbytes=0, rate=10.0, sttl=254, dttl=0, sload=1.0, dload=0.0, tcprtt=0.0")
    return SecurityEvent(**{**base, **kw})


# ---------------- Detection
def test_detection_valid_first_attempt():
    agent = DetectionAgent(StubLLMClient(lambda s, u: GOOD, "stub:good"))
    finding = agent.analyze(event())
    assert (finding.verdict, finding.classification, finding.model) == ("malicious", "DoS", "stub:good")
    assert agent.last_trace.first_attempt_valid and agent.last_trace.attempts == 1


def test_detection_retries_once_then_succeeds():
    answers = iter(["not json", GOOD])
    agent = DetectionAgent(StubLLMClient(lambda s, u: next(answers)))
    finding = agent.analyze(event())
    assert finding.error is None and not agent.last_trace.first_attempt_valid and agent.last_trace.final_valid


def test_detection_gives_error_finding_after_two_bad_answers():
    agent = DetectionAgent(StubLLMClient(lambda s, u: '{"verdict": "evil"}'))
    finding = agent.analyze(event())
    assert finding.error and finding.verdict == "unknown" and finding.confidence == "none"
    assert agent.last_trace.attempts == 2 and not agent.last_trace.final_valid


def test_detection_rejects_extra_keys():
    extra = json.dumps({**json.loads(GOOD), "label": 1})
    assert DetectionAgent(StubLLMClient(lambda s, u: extra)).analyze(event()).error


def test_detection_llm_failure_is_an_error_finding():
    def boom(s, u):
        raise LLMError("server down")
    finding = DetectionAgent(StubLLMClient(boom)).analyze(event())
    assert finding.error and "server down" in finding.error


def test_runtime_prompt_equals_fine_tuning_prompt():
    """Phase 1 must send exactly what Phase 2 is fine-tuned on (D-005)."""
    row = pd.Series({"id": 7, "dur": 0.1, "proto": "udp", "service": "dns", "state": "INT", "spkts": 2,
                     "dpkts": 0, "sbytes": 146, "dbytes": 0, "rate": 10.0, "sttl": 254, "dttl": 0,
                     "sload": 1.0, "dload": 0.0, "tcprtt": 0.0, "label": 1, "attack_cat": "DoS"})
    seen = {}
    DetectionAgent(StubLLMClient(lambda s, u: seen.update(s=s, u=u) or GOOD)).analyze(
        SecurityEvent.model_validate(to_security_event(row, "test")))
    example = create_instruction_example(row)
    assert seen["s"] == example["instruction"] == DETECTION_INSTRUCTION
    assert seen["u"] == example["input"]
    assert "attack_cat" not in seen["u"] and "label" not in seen["u"]
    assert format_raw_content(row) in seen["u"]


# ---------------- Intelligence
IOC = {"source": "test IOC", "ips": {"203.0.113.45": {"threat": "bad"}}, "domains": {"evil.invalid": {}}}


def test_intelligence_match():
    f = IntelligenceAgent(IOC).analyze(event(source_ip="203.0.113.45"))
    assert (f.verdict, f.evidence) == ("malicious", "source_ip=203.0.113.45")


def test_intelligence_no_match_is_not_benign():
    f = IntelligenceAgent(IOC).analyze(event(source_ip="192.0.2.1"))
    assert f.verdict == "unknown" and f.classification == "no_match"


def test_intelligence_no_indicators_abstains():
    f = IntelligenceAgent(IOC).analyze(event())
    assert (f.verdict, f.classification, f.evidence) == ("unknown", "no_indicators", "")


def test_intelligence_metadata_indicator():
    f = IntelligenceAgent(IOC).analyze(event(metadata={"indicators": {"domains": ["EVIL.invalid"]}}))
    assert f.verdict == "malicious" and f.evidence == "indicator_domains_0=EVIL.invalid"


# ---------------- Behavioral
PROFILES = {"profiles": {"udp|dns": {"n": 100, "numeric": {"sbytes": [100, 200], "spkts": [1, 4], "rate": [0, 50]},
                                     "sets": {"state": ["INT"], "sttl": ["254"], "dttl": ["0"]}}}}


def test_behavioral_within_baseline_is_low_confidence_benign():
    f = BehavioralAgent(PROFILES).analyze(event())
    assert (f.verdict, f.classification, f.confidence) == ("benign", "within_baseline", "low")
    assert f.evidence  # cites the checked profile fields (verifiable)


def test_behavioral_deviation_is_suspicious_never_malicious():
    e = event(raw_content="proto=udp, service=dns, state=CON, spkts=90, sbytes=99999, rate=10.0, sttl=62, dttl=0")
    f = BehavioralAgent(PROFILES).analyze(e)
    assert f.verdict == "suspicious" and f.confidence == "high"
    assert set(dict(p.split("=") for p in f.evidence.split(", "))) == {"state", "spkts", "sbytes", "sttl"}


def test_behavioral_no_baseline_abstains():
    f = BehavioralAgent(PROFILES).analyze(event(raw_content="proto=tcp, service=smtp, sbytes=10"))
    assert (f.verdict, f.classification) == ("unknown", "no_baseline")


def test_behavioral_entity_baseline_takes_precedence():
    entities = {"entities": {"host-1": {"numeric": {"sbytes": [0, 10]}, "sets": {"state": ["FIN"]}}}}
    f = BehavioralAgent(PROFILES, entities).analyze(event(entity="host-1"))
    assert f.verdict == "suspicious" and "entity baseline" in f.reasoning


def test_prompt_states_the_unsw_label_set():
    """C1: the base model must be told the allowed labels (fair Phase 1 Macro-F1)."""
    from src.agents.prompts import DETECTION_CLASSES
    from src.data.unsw_nb15 import CLASSIFICATIONS
    assert list(DETECTION_CLASSES) == CLASSIFICATIONS
    for label in CLASSIFICATIONS:
        assert label in DETECTION_INSTRUCTION


# ---------------- Intelligence: flow-signature reputation (C2)
SIGS = {"source": "test signatures", "signatures": {
    "udp|dns|INT|254|0": {"reputation": "malicious", "support": 500, "attack_share": 1.0, "top_attack_cat": "Generic"},
    "tcp|-|FIN|31|29": {"reputation": "benign", "support": 40, "attack_share": 0.0, "top_attack_cat": None}}}


def test_intelligence_known_malicious_signature_is_grounded():
    from src.agents.verification import VerificationAgent
    e = event()
    f = IntelligenceAgent(IOC, SIGS).analyze(e)
    assert (f.verdict, f.classification, f.confidence) == ("malicious", "known_malicious_signature", "high")
    assert VerificationAgent().verify(f, e).status == "verified_consistent"


def test_intelligence_known_benign_signature():
    e = event(raw_content="dur=0.1, proto=tcp, service=-, state=FIN, spkts=2, dpkts=0, sbytes=146, "
                          "dbytes=0, rate=10.0, sttl=31, dttl=29, sload=1.0, dload=0.0, tcprtt=0.0")
    f = IntelligenceAgent(IOC, SIGS).analyze(e)
    assert (f.verdict, f.classification, f.confidence) == ("benign", "known_benign_signature", "medium")


def test_intelligence_unknown_signature_is_no_match_not_benign():
    e = event(raw_content="dur=0.1, proto=tcp, service=http, state=CON, spkts=2, dpkts=0, sbytes=146, "
                          "dbytes=0, rate=10.0, sttl=62, dttl=252, sload=1.0, dload=0.0, tcprtt=0.0")
    f = IntelligenceAgent(IOC, SIGS).analyze(e)
    assert (f.verdict, f.classification) == ("unknown", "no_match")


def test_intelligence_ioc_match_takes_precedence_over_benign_signature():
    e = event(source_ip="203.0.113.45", raw_content="proto=tcp, service=-, state=FIN, sttl=31, dttl=29")
    f = IntelligenceAgent(IOC, SIGS).analyze(e)
    assert (f.verdict, f.classification) == ("malicious", "known_malicious_indicator")


def test_build_intel_signatures_thresholds():
    from src.data.unsw_nb15 import build_intel_signatures
    rows = ([dict(proto="udp", service="dns", state="INT", sttl=254, dttl=0, label=1, attack_cat="Generic")] * 25
            + [dict(proto="tcp", service="-", state="FIN", sttl=31, dttl=29, label=0, attack_cat="Normal")] * 25
            + [dict(proto="tcp", service="http", state="FIN", sttl=62, dttl=252, label=l, attack_cat=c)
               for l, c in [(1, "Exploits"), (0, "Normal")] * 15]          # mixed -> no signature
            + [dict(proto="arp", service="-", state="INT", sttl=0, dttl=0, label=1, attack_cat="DoS")] * 5)  # too rare
    sigs = build_intel_signatures(pd.DataFrame(rows))["signatures"]
    assert sigs["udp|dns|INT|254|0"]["reputation"] == "malicious"
    assert sigs["tcp|-|FIN|31|29"]["reputation"] == "benign"
    assert "tcp|http|FIN|62|252" not in sigs and "arp|-|INT|0|0" not in sigs


# ---------------- E4: Detection outcome categories
def _seq_llm(*answers):
    """Stub whose successive calls return answers; an Exception instance is raised."""
    from src.utils.llm_client import LLMClient
    class Seq(LLMClient):
        model_id = "test:seq"
        def __init__(self):
            self.answers = list(answers)
        def generate(self, system_prompt, user_prompt):
            answer = self.answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer
    return Seq()


def test_detection_outcome_categories():
    from src.utils.llm_client import LLMError
    good = json.dumps({"verdict": "benign", "classification": "Normal", "evidence": "proto=tcp",
                       "confidence": "low", "reasoning": "r"})
    cases = [((good,), "valid", True, True), (("nonsense", good), "valid", True, False),
             (("nonsense", "nonsense"), "schema_invalid", True, False),
             ((LLMError("down"),), "transport_failure", False, False),
             (("nonsense", LLMError("down")), "transport_failure", True, False)]
    for answers, outcome, received, first_valid in cases:
        agent = DetectionAgent(_seq_llm(*answers))
        agent.analyze(event())
        t = agent.last_trace
        assert (t.outcome, t.first_response_received, t.first_attempt_valid) == (outcome, received, first_valid), answers


def test_detection_crash_is_an_execution_failure(stub_config, demo_events):
    from src.models import SecurityEvent
    from src.pipeline import build_coordinator
    coordinator = build_coordinator(stub_config)
    def boom(system_prompt, user_prompt):
        raise RuntimeError("bug")
    coordinator.agents["detection"].llm.responder = boom
    result = coordinator.process_event(SecurityEvent.model_validate(demo_events[0]))
    assert coordinator.agents["detection"].last_trace.outcome == "execution_failure"
    assert next(f for f in result.agent_findings if f.agent == "detection").error
