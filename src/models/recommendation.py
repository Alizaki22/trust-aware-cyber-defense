from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

from src.models.findings import AgentFinding
from src.models.trust import TrustScore, WeightingOutcome
from src.models.types import Confidence, Routing, Verdict
from src.models.verification import VerificationResult


class SimulatedAction(BaseModel):
    """A simulated response action. Can never represent a real action (D-011)."""

    description: str
    executed: Literal[False] = False


class FinalRecommendation(BaseModel):
    """Final structured output consumed by the frontend and by evaluation."""

    run_id: str
    event_id: str
    phase: Literal[1, 2]
    model: str  # summary of agent_models, e.g. "detection=Qwen/...; intelligence=rules:..."
    agent_models: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    is_mock: bool = False

    classification: str
    verdict: Verdict
    confidence: Confidence
    confidence_value: float = Field(ge=0.0, le=1.0)
    routing: Routing
    routing_reason: str
    simulated_action: Optional[SimulatedAction] = None

    agent_findings: list[AgentFinding]
    verification_results: list[VerificationResult]
    trust_scores: list[TrustScore]
    trust_weighted: WeightingOutcome
    equal_weighted: WeightingOutcome
    trust_changed_outcome: bool

    disagreement_summary: Optional[str] = None
    reasoning: str
