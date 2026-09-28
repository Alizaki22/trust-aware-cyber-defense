import pytest

from src.evaluation.metrics import compute_metrics, f1_report, normalize_class


def record(truth_cat, det_cls, final="benign", changed=False, first=True, grounded=True, eq="benign"):
    label = 0 if truth_cat == "Normal" else 1
    return {"ground_truth": {"label": label, "attack_cat": truth_cat},
            "detection_trace": {"first_attempt_valid": first, "final_valid": det_cls is not None,
                                "first_response_received": True,
                                "outcome": "valid" if det_cls is not None else "schema_invalid"},
            "recommendation": {
                "verdict": final, "routing": "human_review", "trust_changed_outcome": changed,
                "trust_weighted": {"verdict": final}, "equal_weighted": {"verdict": eq},
                "agent_findings": [{"agent": "detection", "verdict": "benign" if det_cls == "Normal" else "malicious",
                                    "classification": det_cls or "agent_error", "error": None if det_cls else "x"},
                                   {"agent": "intelligence", "verdict": "unknown", "classification": "no_indicators"},
                                   {"agent": "behavioral", "verdict": "suspicious", "classification": "d"}],
                "verification_results": [{"agent": "detection",
                                          "status": "verified_consistent" if grounded else "verified_inconsistent"}]}}


def test_f1_report_hand_computed():
    rep = f1_report(["A", "A", "B", "B"], ["A", "B", "B", "B"], ["A", "B"])
    assert rep["per_class"]["A"]["f1"] == pytest.approx(2 / 3, abs=1e-4)   # P=1, R=0.5
    assert rep["per_class"]["B"]["f1"] == pytest.approx(0.8, abs=1e-4)     # P=2/3, R=1
    assert rep["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2, abs=1e-4)


def test_normalize_class():
    assert normalize_class(" dos ") == "DoS" and normalize_class("ddos") == "INVALID"


def test_four_metrics():
    records = [record("Normal", "Normal"),
               record("DoS", "DoS", final="malicious", changed=True, eq="benign"),
               record("DoS", "Normal", first=False, grounded=False),
               record("Exploits", None, first=False)]
    m = compute_metrics(records)
    assert m["n_events"] == 4
    assert m["schema_valid_rate"]["first_attempt"] == {"value": 0.5, "numerator": 2, "denominator": 4}
    assert m["schema_valid_rate"]["after_retry"]["numerator"] == 3
    assert m["evidence_grounding_rate"] == {"value": 0.6667, "numerator": 2, "denominator": 3}
    assert m["trust_impact_rate"]["numerator"] == 1 and m["trust_impact_rate"]["value"] == 0.25
    assert m["trust_impact_rate"]["when_changed"] == {"trust_weighted_correct": 1, "equal_weighted_correct": 0}
    # Normal: P=1/2 R=1 -> 2/3 ; DoS: P=1 R=1/2 -> 2/3 ; Exploits: 0
    assert m["macro_f1_detection"]["value"] == pytest.approx((2 / 3 + 2 / 3 + 0) / 3, abs=1e-4)
    assert m["macro_f1_detection"]["invalid_predictions"] == 1


def _trace_record(trace):
    det = {"agent": "detection", "verdict": "benign", "classification": "Normal", "error": None}
    rec = {"agent_findings": [det], "verification_results": [{"agent": "detection", "status": "verified_consistent"}],
           "verdict": "benign", "trust_changed_outcome": False, "routing": "further_verification",
           "trust_weighted": {"verdict": "benign"}, "equal_weighted": {"verdict": "benign"}}
    return {"ground_truth": {"label": 0, "attack_cat": "Normal"}, "recommendation": rec, "detection_trace": trace}


def test_detection_outcomes_are_reported_separately():
    """E4: valid / schema-invalid / transport failure / execution failure never mix."""
    valid = {"outcome": "valid", "first_response_received": True, "first_attempt_valid": True, "final_valid": True}
    retried = {"outcome": "valid", "first_response_received": True, "first_attempt_valid": False, "final_valid": True}
    invalid = {"outcome": "schema_invalid", "first_response_received": True, "first_attempt_valid": False}
    down = {"outcome": "transport_failure", "first_response_received": False, "transport_error": True}
    # attempt 1 answered but was invalid, attempt 2 hit a server error: attempt 1 still counts as invalid
    invalid_then_down = {"outcome": "transport_failure", "first_response_received": True,
                         "first_attempt_valid": False, "transport_error": True}
    crashed = {"outcome": "execution_failure", "first_response_received": False}
    m = compute_metrics([_trace_record(t) for t in (valid, retried, invalid, down, invalid_then_down, crashed)])
    s = m["schema_valid_rate"]
    assert s["outcomes"] == {"valid": 2, "schema_invalid": 1, "transport_failure": 2, "execution_failure": 1}
    assert s["first_attempt"] == {"value": 0.25, "numerator": 1, "denominator": 4}   # 4 judged first answers
    assert s["after_retry"] == {"value": 0.6667, "numerator": 2, "denominator": 3}  # valid / (valid + schema_invalid)
    assert sum(s["outcomes"].values()) == m["n_events"]
