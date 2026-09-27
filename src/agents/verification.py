"""Verification Agent (rule-based; checks findings, never re-classifies).

Rules, applied per finding in order:
  1. agent error                          -> inconclusive
  2. evidence not parseable as field=value -> verified_inconsistent
  3. no evidence + abstention (unknown)    -> inconclusive
  4. no evidence + a conclusion            -> verified_inconsistent (uncited claim)
  5. any cited field missing from the event, or a value that differs
     (numbers compared numerically)        -> verified_inconsistent (not grounded)
  6. Detection: a known UNSW class with a contradicting verdict
     (Normal <-> benign, attack <-> malicious/suspicious) -> verified_inconsistent
  7. otherwise                             -> verified_consistent
"""
from __future__ import annotations

from src.agents.base import event_fields, parse_pairs
from src.models import AgentFinding, SecurityEvent, VerificationResult

KNOWN_ATTACKS = {"analysis", "backdoor", "dos", "exploits", "fuzzers", "generic",
                 "reconnaissance", "shellcode", "worms"}


def _same(cited: str, actual: str) -> bool:
    if cited == actual:
        return True
    try:
        return float(cited) == float(actual)
    except ValueError:
        return cited.lower() == actual.lower()


class VerificationAgent:
    name = "verification"
    model_id = "rules:evidence-check-v1"

    def verify(self, finding: AgentFinding, event: SecurityEvent) -> VerificationResult:
        def result(status, reason):
            return VerificationResult(agent=finding.agent, event_id=event.event_id, status=status, reason=reason)

        if finding.error:
            return result("inconclusive", "Agent failed; nothing to verify.")
        try:
            cited = parse_pairs(finding.evidence)
        except ValueError:
            return result("verified_inconsistent", "Evidence is not a list of field=value pairs.")
        if not cited:
            if finding.verdict == "unknown":
                return result("inconclusive", "Agent abstained without citing evidence.")
            return result("verified_inconsistent", "A conclusion was given without citing any evidence.")
        fields = event_fields(event)
        missing = [name for name, _ in cited if name not in fields]
        wrong = [name for name, value in cited if name in fields and not _same(value, fields[name])]
        if missing or wrong:
            parts = []
            if missing:
                parts.append(f"cited fields not in the event: {', '.join(missing)}")
            if wrong:
                parts.append(f"cited values differ from the event: {', '.join(wrong)}")
            return result("verified_inconsistent", "; ".join(parts) + ".")
        if finding.agent == "detection":
            cls = finding.classification.strip().lower()
            if cls == "normal" and finding.verdict in ("malicious", "suspicious"):
                return result("verified_inconsistent", "Classification 'Normal' contradicts the verdict.")
            if cls in KNOWN_ATTACKS and finding.verdict == "benign":
                return result("verified_inconsistent", "An attack classification contradicts verdict 'benign'.")
        return result("verified_consistent", f"All {len(cited)} cited field values match the event.")

    def verify_findings(self, findings: list[AgentFinding], event: SecurityEvent) -> list[VerificationResult]:
        return [self.verify(finding, event) for finding in findings]
