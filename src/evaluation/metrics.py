"""The four locked Phase 1 metrics (docs/PHASE1_IMPLEMENTATION.md §9).

Inputs: one record per evaluated event:
  {"ground_truth": {"label", "attack_cat"}, "recommendation": FinalRecommendation-dict,
   "detection_trace": {"first_attempt_valid", "final_valid", ...}}

1. Macro-F1 (Detection): 10-class UNSW-NB15 classification of the Detection
   finding vs attack_cat; unweighted mean of per-class F1 over the classes
   present in the ground truth. Invalid/unknown predictions count as wrong.
2. Schema-valid output rate: events whose FIRST Detection response parses
   into the Detection schema (exact keys, canonical enums, classification in
   the UNSW-NB15 label set) / events whose first Detection call returned a
   model response. Transport failures (server down, timeout, empty reply) and
   other execution failures produced no response to judge: they are excluded
   from the denominator and reported separately as outcomes, and still count
   as wrong in Macro-F1. After-retry rate: valid / (valid + schema_invalid).
3. Evidence grounding rate: schema-valid Detection findings that
   Verification marks verified_consistent / schema-valid Detection findings.
4. Trust impact rate: events whose trust-weighted verdict differs from the
   equal-weighted verdict / evaluated events (+ which one was right).
"""
from __future__ import annotations

from collections import Counter

from src.data.unsw_nb15 import CLASSIFICATIONS

_CANON = {c.lower(): c for c in CLASSIFICATIONS}
THREAT = {"malicious", "suspicious"}
DETECTION_OUTCOMES = ("valid", "schema_invalid", "transport_failure", "execution_failure")


def normalize_class(value: str) -> str:
    return _CANON.get(str(value).strip().lower(), "INVALID")


def f1_report(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    per_class = {}
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": round(precision, 4), "recall": round(recall, 4),
                            "f1": round(f1, 4), "support": tp + fn}
    macro = sum(v["f1"] for v in per_class.values()) / len(per_class) if per_class else 0.0
    return {"macro_f1": round(macro, 4), "per_class": per_class}


def _rate(numerator: int, denominator: int) -> dict:
    return {"value": round(numerator / denominator, 4) if denominator else None,
            "numerator": numerator, "denominator": denominator}


def binary_truth(label: int) -> str:
    return "attack" if label == 1 else "normal"


def binary_pred(verdict: str) -> str:
    return "attack" if verdict in THREAT else ("normal" if verdict == "benign" else "undetermined")


def compute_metrics(records: list[dict]) -> dict:
    n = len(records)
    y_true, y_pred = [], []
    first_valid = first_judged = final_valid = grounded = 0
    outcomes = Counter()
    changed = changed_trust_right = changed_equal_right = 0
    sys_true, sys_pred = [], []
    agent_stats = {a: Counter() for a in ("detection", "intelligence", "behavioral")}
    routing = Counter()

    for record in records:
        truth = record["ground_truth"]
        rec = record["recommendation"]
        trace = record.get("detection_trace") or {}
        findings = {f["agent"]: f for f in rec["agent_findings"]}
        statuses = {v["agent"]: v["status"] for v in rec["verification_results"]}
        detection = findings["detection"]

        y_true.append(truth["attack_cat"])
        y_pred.append(normalize_class(detection["classification"]) if not detection.get("error") else "INVALID")

        outcomes[trace.get("outcome", "execution_failure")] += 1
        first_judged += bool(trace.get("first_response_received"))
        first_valid += bool(trace.get("first_attempt_valid"))
        if trace.get("final_valid"):
            final_valid += 1
            grounded += statuses.get("detection") == "verified_consistent"

        truth_bin = binary_truth(truth["label"])
        sys_true.append(truth_bin)
        sys_pred.append(binary_pred(rec["verdict"]))
        if rec["trust_changed_outcome"]:
            changed += 1
            changed_trust_right += binary_pred(rec["trust_weighted"]["verdict"]) == truth_bin
            changed_equal_right += binary_pred(rec["equal_weighted"]["verdict"]) == truth_bin
        routing[rec["routing"]] += 1

        for agent, finding in findings.items():
            stats = agent_stats[agent]
            if finding.get("error"):
                stats["errors"] += 1
            prediction = binary_pred(finding["verdict"]) if not finding.get("error") else "undetermined"
            if prediction == "undetermined":
                stats["abstained"] += 1
            else:
                stats["voted"] += 1
                stats["correct"] += prediction == truth_bin

    labels = [c for c in CLASSIFICATIONS if c in set(y_true)]
    detection_f1 = f1_report(y_true, y_pred, labels)
    system_f1 = f1_report(sys_true, sys_pred, [c for c in ("attack", "normal") if c in set(sys_true)])
    return {
        "n_events": n,
        "macro_f1_detection": {"value": detection_f1["macro_f1"], "classes": labels,
                               "per_class": detection_f1["per_class"],
                               "invalid_predictions": y_pred.count("INVALID")},
        "schema_valid_rate": {"first_attempt": _rate(first_valid, first_judged),
                              "after_retry": _rate(outcomes["valid"], outcomes["valid"] + outcomes["schema_invalid"]),
                              "outcomes": {k: outcomes[k] for k in DETECTION_OUTCOMES}},
        "evidence_grounding_rate": _rate(grounded, final_valid),
        "trust_impact_rate": {**_rate(changed, n),
                              "when_changed": {"trust_weighted_correct": changed_trust_right,
                                               "equal_weighted_correct": changed_equal_right}},
        "secondary": {
            "system_binary_macro_f1": system_f1["macro_f1"],
            "system_binary_per_class": system_f1["per_class"],
            "undetermined_final_verdicts": sys_pred.count("undetermined"),
            "routing": dict(routing),
            "per_agent_binary": {a: {"voted": s["voted"], "abstained": s["abstained"], "errors": s["errors"],
                                     "accuracy_when_voting": round(s["correct"] / s["voted"], 4) if s["voted"] else None}
                                 for a, s in agent_stats.items()},
        },
    }
