"""Canonical system input."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, IPvAnyAddress


class SecurityEvent(BaseModel):
    """A normalized security event for analysis.

    For UNSW-NB15 flows, ``raw_content`` holds the 14 Detection features as
    ``name=value`` pairs (exactly the fine-tuning ``input`` body), and
    ``metadata`` carries provenance (source, record id, split) and, for
    evaluation only, the ground truth under ``metadata["ground_truth"]``.
    Agents never read ``metadata["ground_truth"]``.
    """

    event_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    event_type: str = Field(min_length=1)
    source_ip: Optional[IPvAnyAddress] = None
    destination_ip: Optional[IPvAnyAddress] = None
    destination_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None
    raw_content: str = Field(min_length=1, max_length=10_000)
    entity: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
