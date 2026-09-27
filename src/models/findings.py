"""Agent output = the inter-agent message (agents never message each other)."""
from typing import Optional

from pydantic import BaseModel

from src.models.types import AgentName, Confidence, Verdict


class ModelFindingOutput(BaseModel):
    """The part of a finding an LLM must generate (also the fine-tuning target)."""

    verdict: Verdict
    classification: str
    evidence: str
    confidence: Confidence
    reasoning: str


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
