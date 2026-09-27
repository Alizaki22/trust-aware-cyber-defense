"""Detection Agent (LLM; the Phase 2 fine-tuning target).

Sends exactly the fine-tuning prompt (system=DETECTION_INSTRUCTION,
user=INPUT_HEADER + raw_content) to the configured model, parses the JSON
answer into ModelFindingOutput, and retries once on an unparseable answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError

from src.agents.base import BaseAgent
from src.agents.prompts import DETECTION_INSTRUCTION, RETRY_SUFFIX, format_detection_input
from src.models import AgentFinding, ModelFindingOutput, SecurityEvent
from src.utils.llm_client import LLMClient, LLMError, extract_json_object


@dataclass
class DetectionTrace:
    """Per-event record used by evaluation (schema-valid rate) and run logs."""
    raw_responses: list[str] = field(default_factory=list)
    first_attempt_valid: bool = False
    final_valid: bool = False
    attempts: int = 0
    error: Optional[str] = None


def parse_model_output(text: str) -> ModelFindingOutput:
    """Raises ValueError/ValidationError if the text is not a valid finding."""
    data = extract_json_object(text)
    extra = set(data) - set(ModelFindingOutput.model_fields)
    if extra:
        raise ValueError(f"unexpected keys {sorted(extra)}")
    return ModelFindingOutput.model_validate(data)


class DetectionAgent(BaseAgent):
    name = "detection"

    def __init__(self, llm: LLMClient, max_attempts: int = 2):
        self.llm = llm
        self.model_id = llm.model_id
        self.max_attempts = max_attempts
        self.last_trace = DetectionTrace()

    def analyze(self, event: SecurityEvent) -> AgentFinding:
        trace = DetectionTrace()
        self.last_trace = trace
        user_prompt = format_detection_input(event.raw_content)
        for attempt in range(1, self.max_attempts + 1):
            trace.attempts = attempt
            prompt = user_prompt if attempt == 1 else user_prompt + RETRY_SUFFIX
            try:
                text = self.llm.generate(DETECTION_INSTRUCTION, prompt)
            except LLMError as error:
                trace.error = str(error)
                return self.error_finding(event, f"LLM call failed: {error}")
            trace.raw_responses.append(text)
            try:
                output = parse_model_output(text)
            except (ValueError, ValidationError) as error:
                trace.error = f"unparseable output: {str(error)[:200]}"
                continue
            trace.first_attempt_valid = attempt == 1
            trace.final_valid = True
            trace.error = None
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                **output.model_dump())
        return self.error_finding(event, f"failed to parse structured output after "
                                         f"{self.max_attempts} attempts ({trace.error})")
