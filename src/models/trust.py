from typing import Dict, Literal

from pydantic import BaseModel, Field

from src.models.types import AgentName, Verdict


class TrustScore(BaseModel):
    agent: AgentName
    event_id: str
    historical_accuracy: float = Field(ge=0.0, le=1.0)
    verification_score: float = Field(ge=0.0, le=1.0)
    peer_agreement: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)


class WeightingOutcome(BaseModel):
    method: Literal["trust_weighted", "equal_weighted"]
    verdict: Verdict  # "unknown" when tied or no votes
    verdict_weights: Dict[str, float]
    tie: bool = False
