"""Pure display helpers (FRONTEND_SPEC §6.2). Every state = icon + words, never colour alone."""

VERDICT = {"malicious": ("🔴", "Malicious"), "suspicious": ("🟠", "Suspicious"),
           "benign": ("🟢", "Benign"), "unknown": ("⚪", "No conclusion")}
VERIFICATION = {"verified_consistent": ("✅", "Evidence matches the event"),
                "verified_inconsistent": ("❌", "Evidence does not match the event"),
                "inconclusive": ("❔", "Nothing to verify")}
ROUTING = {"simulated_action": ("⚙️", "Simulated action"),
           "further_verification": ("🔍", "Further verification"),
           "human_review": ("👤", "Human review")}
CONFIDENCE_BARS = {"high": "▮▮▮", "medium": "▮▮▯", "low": "▮▯▯", "none": "▯▯▯"}
ABSTAIN_LABELS = {"no_match": "No known indicator", "no_indicators": "No indicators to look up",
                  "no_baseline": "No baseline available",
                  "agent_error": "Agent failed"}


def verdict_label(verdict: str, classification: str = "") -> str:
    icon, text = VERDICT.get(verdict, ("⚪", verdict))
    if verdict == "unknown" and classification in ABSTAIN_LABELS:
        text = ABSTAIN_LABELS[classification]
    elif verdict == "benign" and classification == "within_baseline":
        text = "Benign (within baseline, weak signal)"
    return f"{icon} {text}"


def trust_text(score: float) -> str:
    """Trust is a weighting heuristic, never shown as a percentage."""
    return f"{score:.2f}"


def confidence_text(label: str, value: float | None = None) -> str:
    bars = CONFIDENCE_BARS.get(label, "▯▯▯")
    return f"{bars} {label}" + (f" ({value:.2f})" if value is not None else "")
