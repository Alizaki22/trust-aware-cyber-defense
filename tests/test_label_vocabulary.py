"""C1: one canonical UNSW-NB15 label vocabulary everywhere."""
import json

import pytest
from pydantic import ValidationError

from src.agents import verification
from src.agents.detection import DetectionAgent, parse_model_output
from src.agents.prompts import DETECTION_INSTRUCTION
from src.data import unsw_nb15
from src.evaluation.metrics import normalize_class
from src.models import ATTACK_CLASSES, DETECTION_CLASSES, NORMAL_CLASS, DetectionModelOutput, SecurityEvent
from src.utils.llm_client import StubLLMClient

UNSW_LABELS = ["Normal", "Analysis", "Backdoor", "DoS", "Exploits", "Fuzzers",
               "Generic", "Reconnaissance", "Shellcode", "Worms"]


def test_vocabulary_is_the_unsw_label_set():
    assert list(DETECTION_CLASSES) == UNSW_LABELS
    assert NORMAL_CLASS == "Normal" and list(ATTACK_CLASSES) == UNSW_LABELS[1:]


def test_dataset_prompt_verification_and_metrics_share_the_vocabulary():
    assert unsw_nb15.CLASSIFICATIONS == list(DETECTION_CLASSES)
    assert unsw_nb15.NORMAL_CLASS == NORMAL_CLASS
    assert unsw_nb15.ATTACK_CATEGORIES == list(ATTACK_CLASSES)
    assert verification.KNOWN_ATTACKS == {c.lower() for c in ATTACK_CLASSES}
    assert "(exactly one of: " + ", ".join(DETECTION_CLASSES) + ")" in DETECTION_INSTRUCTION
    for label in DETECTION_CLASSES:
        assert normalize_class(label) == label
        assert normalize_class(f"  {label.upper()} ") == label
    assert normalize_class("Port scan") == "INVALID"


def test_training_targets_use_the_vocabulary():
    for label, attack_cat in [(0, "Normal"), (1, "Exploits")]:
        row = {f: 1 for f in unsw_nb15.DETECTION_FEATURES} | {"proto": "tcp", "service": "-", "state": "FIN",
                                                              "label": label, "attack_cat": attack_cat}
        example = unsw_nb15.create_instruction_example(row)
        assert example["instruction"] == DETECTION_INSTRUCTION
        output = DetectionModelOutput.model_validate_json(example["output"])
        assert output.classification in DETECTION_CLASSES
        assert unsw_nb15.check_training_record(example) == []


@pytest.mark.parametrize("given,expected", [("Normal", "Normal"), ("dos", "DoS"), (" RECONNAISSANCE ", "Reconnaissance")])
def test_detection_schema_canonicalises_case(given, expected):
    out = DetectionModelOutput(verdict="malicious", classification=given, evidence="", confidence="low", reasoning="")
    assert out.classification == expected


@pytest.mark.parametrize("label", ["Port scan", "DDoS", "attack", ""])
def test_detection_schema_rejects_labels_outside_the_vocabulary(label):
    with pytest.raises(ValidationError):
        DetectionModelOutput(verdict="malicious", classification=label, evidence="", confidence="low", reasoning="")


def test_out_of_vocabulary_label_is_schema_invalid_at_runtime():
    answer = json.dumps({"verdict": "malicious", "classification": "Port scan", "evidence": "proto=tcp",
                         "confidence": "high", "reasoning": "x"})
    with pytest.raises(ValidationError):
        parse_model_output(answer)
    agent = DetectionAgent(StubLLMClient(lambda s, u: answer))
    event = SecurityEvent(event_id="e", timestamp="2026-01-01T00:00:00Z", event_type="network_flow",
                          raw_content="proto=tcp")
    finding = agent.analyze(event)
    assert finding.error and agent.last_trace.first_attempt_valid is False
    assert agent.last_trace.outcome == "schema_invalid"
