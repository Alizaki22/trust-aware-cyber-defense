"""Intelligence Agent (deterministic IOC lookup against local reference data).

Looks up the event's indicators (source/destination IP, optional
metadata["indicators"]) in a local, SYNTHETIC IOC file. "No match" and "no
indicators" are abstentions (verdict "unknown"), never "benign".
"""
from __future__ import annotations

import json
from pathlib import Path

from src.agents.base import BaseAgent
from src.models import AgentFinding, SecurityEvent

IOC_KINDS = ("ips", "domains", "hashes")


class IntelligenceAgent(BaseAgent):
    name = "intelligence"
    model_id = "rules:ioc-lookup-v1"

    def __init__(self, ioc_data: dict):
        self.source = ioc_data.get("source", "unknown source")
        self.iocs = {kind: {str(k).lower(): v for k, v in ioc_data.get(kind, {}).items()} for kind in IOC_KINDS}

    @classmethod
    def from_file(cls, path: Path) -> "IntelligenceAgent":
        return cls(json.loads(Path(path).read_text()) if Path(path).exists() else {})

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
