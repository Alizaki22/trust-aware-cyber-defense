"""Shared literal types (docs/PHASE1_IMPLEMENTATION.md §3)."""
from typing import Literal

Verdict = Literal["malicious", "suspicious", "benign", "unknown"]
Confidence = Literal["high", "medium", "low", "none"]
VerificationStatus = Literal["verified_consistent", "verified_inconsistent", "inconclusive"]
Routing = Literal["simulated_action", "further_verification", "human_review"]
AgentName = Literal["detection", "intelligence", "behavioral"]

AGENT_NAMES: tuple[str, ...] = ("detection", "intelligence", "behavioral")
