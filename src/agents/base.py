"""Common agent interface: analyze(SecurityEvent) -> AgentFinding."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.models import AgentFinding, SecurityEvent


def parse_pairs(text: str) -> list[tuple[str, str]]:
    """Parse 'a=1, b=2' into [('a','1'), ('b','2')]; ignores empty parts."""
    pairs = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"not a field=value pair: {part!r}")
        name, value = part.split("=", 1)
        pairs.append((name.strip(), value.strip()))
    return pairs


def event_fields(event: SecurityEvent) -> dict[str, str]:
    """All checkable field=value facts of an event (raw_content pairs + typed fields)."""
    fields: dict[str, str] = {}
    try:
        fields.update(dict(parse_pairs(event.raw_content)))
    except ValueError:
        pass  # free-text raw_content (e.g. an email body): only typed fields are checkable
    for name in ("event_type", "source_ip", "destination_ip", "destination_port", "protocol", "entity"):
        value = getattr(event, name)
        if value is not None:
            fields[name] = str(value)
    indicators = event.metadata.get("indicators", {}) if isinstance(event.metadata, dict) else {}
    for kind in ("ips", "domains", "hashes"):
        for index, value in enumerate(indicators.get(kind, []) or []):
            fields[f"indicator_{kind}_{index}"] = str(value)
    return fields


class BaseAgent(ABC):
    name: str
    model_id: str

    @abstractmethod
    def analyze(self, event: SecurityEvent) -> AgentFinding: ...

    def error_finding(self, event: SecurityEvent, error: str, model: Optional[str] = None) -> AgentFinding:
        return AgentFinding(agent=self.name, event_id=event.event_id, verdict="unknown",
                            classification="agent_error", evidence="", confidence="none",
                            reasoning="The agent failed; no conclusion was produced.",
                            model=model or self.model_id, error=error[:500])
