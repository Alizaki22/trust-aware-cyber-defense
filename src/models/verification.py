from pydantic import BaseModel

from src.models.types import AgentName, VerificationStatus


class VerificationResult(BaseModel):
    """Result of verifying a single agent finding."""

    agent: AgentName
    event_id: str
    status: VerificationStatus
    reason: str
