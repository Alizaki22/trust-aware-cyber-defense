"""Shared literal types (docs/PHASE1_IMPLEMENTATION.md §3)."""
from typing import Literal

Verdict = Literal["malicious", "suspicious", "benign", "unknown"]
Confidence = Literal["high", "medium", "low", "none"]
VerificationStatus = Literal["verified_consistent", "verified_inconsistent", "inconclusive"]
Routing = Literal["simulated_action", "further_verification", "human_review"]
AgentName = Literal["detection", "intelligence", "behavioral"]

AGENT_NAMES: tuple[str, ...] = ("detection", "intelligence", "behavioral")

# Canonical UNSW-NB15 label vocabulary: the ONLY source of truth for the
# Detection prompt, the Detection output schema, the dataset pipeline,
# Verification and evaluation. First entry is the normal class.
DETECTION_CLASSES: tuple[str, ...] = (
    "Normal", "Analysis", "Backdoor", "DoS", "Exploits", "Fuzzers",
    "Generic", "Reconnaissance", "Shellcode", "Worms",
)
NORMAL_CLASS: str = DETECTION_CLASSES[0]
ATTACK_CLASSES: tuple[str, ...] = DETECTION_CLASSES[1:]
