"""Intelligence Agent (deterministic lookup against local reference data).

Two reference sources, checked in order:
  1. IOC lookup: source/destination IP and metadata["indicators"] against a
     local, SYNTHETIC IOC file (demo events).
  2. Flow-signature reputation: the event's (proto, service, state, sttl, dttl)
     tuple against signatures learned from the UNSW-NB15 TRAIN split only
     (data/processed/intel_signatures.json). A signature can be known
     malicious or known benign (like an allowlist entry).
"No match" and "no indicators" are abstentions (verdict "unknown"), never "benign".

LIMITATION: The flow signature uses `sttl` and `dttl`. In the UNSW-NB15 dataset, `sttl` and `dttl` (Time to Live) are known artifacts that artificially leak the attack label because of how the synthetic attacks were generated. This means the Intelligence agent exploits a dataset artifact rather than learning general cybersecurity intelligence.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.agents.base import BaseAgent, event_fields
from src.data.unsw_nb15 import SIGNATURE_FEATURES, signature_key
from src.models import AgentFinding, SecurityEvent

IOC_KINDS = ("ips", "domains", "hashes")


class IntelligenceAgent(BaseAgent):
    name = "intelligence"
    model_id = "rules:ioc-and-signature-lookup-v2"

    def __init__(self, ioc_data: dict, signature_data: dict | None = None):
        self.source = ioc_data.get("source", "unknown source")
        self.iocs = {kind: {str(k).lower(): v for k, v in ioc_data.get(kind, {}).items()} for kind in IOC_KINDS}
        signature_data = signature_data or {}
        self.signature_source = signature_data.get("source", "flow-signature reference")
        self.signatures = signature_data.get("signatures", {})

    @classmethod
    def from_file(cls, path: Path, signatures_path: Path | None = None) -> "IntelligenceAgent":
        load = lambda p: json.loads(Path(p).read_text()) if p is not None and Path(p).exists() else {}
        return cls(load(path), load(signatures_path))

    def _signature_finding(self, event: SecurityEvent) -> AgentFinding | None:
        fields = event_fields(event)
        if not self.signatures or not all(f in fields for f in SIGNATURE_FEATURES):
            return None
        info = self.signatures.get(signature_key(fields))
        evidence = ", ".join(f"{f}={fields[f]}" for f in SIGNATURE_FEATURES)
        if info is None:
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="unknown", classification="no_match", evidence=evidence,
                                confidence="low",
                                reasoning=f"The flow signature is not a known signature in the {self.signature_source}. "
                                          "No match is not evidence of benign.")
        high = info["support"] >= 100 and (info["attack_share"] >= 0.99 or info["attack_share"] <= 0.01)
        if info["reputation"] == "malicious":
            attack = f" (most often {info['top_attack_cat']})" if info.get("top_attack_cat") else ""
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="malicious", classification="known_malicious_signature",
                                evidence=evidence, confidence="high" if high else "medium",
                                reasoning=f"This flow signature is known malicious{attack}: "
                                          f"{info['attack_share']:.0%} of {info['support']} reference flows were attacks.")
        return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                            verdict="benign", classification="known_benign_signature",
                            evidence=evidence, confidence="high" if high else "medium",
                            reasoning=f"This flow signature is known benign: {1 - info['attack_share']:.0%} of "
                                      f"{info['support']} reference flows were normal traffic.")

    def _indicators(self, event: SecurityEvent) -> list[tuple[str, str, str]]:
        found = []
        for field in ("source_ip", "destination_ip"):
            value = getattr(event, field)
            if value is not None:
                found.append((field, str(value), "ips"))
        for kind in IOC_KINDS:
            for index, value in enumerate(event.metadata.get("indicators", {}).get(kind, [])):
                found.append((f"indicator_{kind}_{index}", str(value), kind))
        return found

    def analyze(self, event: SecurityEvent) -> AgentFinding:
        indicators = self._indicators(event)
        ioc_hit = any(v.lower() in self.iocs[k] for _, v, k in indicators)
        if not ioc_hit:
            signature = self._signature_finding(event)
            if signature is not None and signature.verdict != "unknown":
                return signature
            if not indicators and signature is not None:
                return signature  # "no_match" on the flow signature
        if not indicators:
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="unknown", classification="no_indicators", evidence="",
                                confidence="none",
                                reasoning="The event contains no IP/domain/hash indicator to look up.")
        matches = [(f, v, self.iocs[k][v.lower()]) for f, v, k in indicators if v.lower() in self.iocs[k]]
        if matches:
            field, value, info = matches[0]
            threat = info.get("threat", "known malicious indicator") if isinstance(info, dict) else str(info)
            evidence = ", ".join(f"{f}={v}" for f, v, _ in matches)
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="malicious", classification="known_malicious_indicator",
                                evidence=evidence, confidence="high",
                                reasoning=f"{value} matches {threat} in {self.source}.")
        evidence = ", ".join(f"{f}={v}" for f, v, _ in indicators)
        return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                            verdict="unknown", classification="no_match", evidence=evidence,
                            confidence="low",
                            reasoning=f"No indicator matched {self.source}. No match is not evidence of benign.")
