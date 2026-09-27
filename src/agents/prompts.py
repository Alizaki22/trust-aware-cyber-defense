"""Detection prompt, shared by the runtime agent AND the fine-tuning dataset.

Phase 2 fine-tunes on (system=DETECTION_INSTRUCTION, user=format_detection_input,
assistant=target JSON). Phase 1 sends exactly the same system/user messages to the
base model, so the only difference between phases is the model (D-005).
"""

INPUT_HEADER = "Analyze this network security event:"

DETECTION_INSTRUCTION = (
    "You are the Detection Agent. "
    "Analyze the network security event "
    "and determine whether it is normal "
    "or malicious. If malicious, identify "
    "the attack category. "
    "Respond only with a JSON object with the keys "
    "verdict (malicious|suspicious|benign|unknown), "
    "classification, evidence (feature=value pairs copied "
    "from the event), confidence (high|medium|low|none) "
    "and reasoning."
)

RETRY_SUFFIX = (
    "\n\nYour previous answer was not a valid JSON object with exactly the keys "
    "verdict, classification, evidence, confidence, reasoning. "
    "Reply again with only that JSON object."
)


def format_detection_input(raw_content: str) -> str:
    return f"{INPUT_HEADER}\n{raw_content}"
