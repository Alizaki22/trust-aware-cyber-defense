"""Detection prompt, shared by the runtime agent AND the fine-tuning dataset.

Phase 2 fine-tunes on (system=DETECTION_INSTRUCTION, user=format_detection_input,
assistant=target JSON). Phase 1 sends exactly the same system/user messages to the
base model, so the only difference between phases is the model (D-005).
"""

INPUT_HEADER = "Analyze this network security event:"

# The allowed labels are stated in the prompt: without them a zero-shot base
# model invents label names, so Phase 1 Macro-F1 would measure vocabulary
# guessing and Phase 2 would "win" just by learning the names (audit C1).
from src.models.types import DETECTION_CLASSES  # noqa: E402  (single source of truth)

DETECTION_INSTRUCTION = (
    "You are the Detection Agent. "
    "Analyze the network security event "
    "and determine whether it is normal "
    "or malicious. If malicious, identify "
    "the attack category. "
    "Respond only with a JSON object with the keys "
    "verdict (malicious|suspicious|benign|unknown), "
    "classification (exactly one of: " + ", ".join(DETECTION_CLASSES) + "), "
    "evidence (feature=value pairs copied "
    "from the event), confidence (high|medium|low|none) "
    "and reasoning. "
    "Use classification Normal with verdict benign for normal traffic, "
    "and an attack category with verdict malicious for an attack."
)

RETRY_SUFFIX = (
    "\n\nYour previous answer was not a valid JSON object with exactly the keys "
    "verdict, classification, evidence, confidence, reasoning. "
    "Reply again with only that JSON object."
)


def format_detection_input(raw_content: str) -> str:
    return f"{INPUT_HEADER}\n{raw_content}"
