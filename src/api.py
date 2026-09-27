"""In-process backend API consumed by the frontend (no HTTP layer needed for the MVP)."""
from __future__ import annotations

from typing import Optional

from src.config import SystemConfig
from src.coordinator.coordinator import Coordinator
from src.models import FinalRecommendation, SecurityEvent
from src.pipeline import build_coordinator

_default: Optional[Coordinator] = None


def get_coordinator(config: Optional[SystemConfig] = None) -> Coordinator:
    global _default
    if config is not None:
        return build_coordinator(config)
    if _default is None:
        _default = build_coordinator()
    return _default


def analyze_event(event: dict | SecurityEvent, coordinator: Optional[Coordinator] = None) -> FinalRecommendation:
    """Validate an event and run the full pipeline. Raises pydantic.ValidationError on bad input."""
    event = event if isinstance(event, SecurityEvent) else SecurityEvent.model_validate(event)
    return (coordinator or get_coordinator()).process_event(event)
