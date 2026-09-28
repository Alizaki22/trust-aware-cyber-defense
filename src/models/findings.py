"""Agent output = the inter-agent message (agents never message each other)."""
from typing import Optional

from pydantic import BaseModel, field_validator

from src.models.types import DETECTION_CLASSES, AgentName, Confidence, Verdict

_CANONICAL_CLASS = {c.lower(): c for c in DETECTION_CLASSES}


class ModelFindingOutput(BaseModel):
    """The part of a finding an LLM must generate (also the fine-tuning target)."""

    verdict: Verdict
    classification: str
    evidence: str
    confidence: Confidence
    reasoning: str


class DetectionModelOutput(ModelFindingOutput):
    """What the Detection model must generate (also its fine-tuning target).

    ``classification`` must be one of the canonical UNSW-NB15 labels
    (DETECTION_CLASSES); case and surrounding whitespace are normalised, any
    other label makes the output schema-invalid.
    """

    @field_validator("classification")
    @classmethod
    def _canonical_label(cls, value: str) -> str:
        canonical = _CANONICAL_CLASS.get(value.strip().lower())
        if canonical is None:
            raise ValueError(f"classification must be one of {list(DETECTION_CLASSES)}")
        return canonical


class AgentFinding(ModelFindingOutput):
    """Structured finding produced by a specialist agent.

    ``agent``, ``event_id``, ``model`` and ``error`` are set by code, never by
    a model. ``evidence`` is a comma-separated list of ``field=value`` pairs
    copied from the event so Verification can check it mechanically.
    """

    agent: AgentName
    event_id: str
    model: Optional[str] = None  # engine that produced it (per agent -> Detection-only Phase 2)
    error: Optional[str] = None
