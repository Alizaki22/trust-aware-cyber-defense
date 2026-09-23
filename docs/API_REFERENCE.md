# API Reference

This document defines the internal APIs, data schemas, and interfaces used by the project's components. Since this is a plain Python module project (not a distributed system), "API" here refers to the Python interfaces between modules, plus the data schemas that flow through the system.

> **Status:** PROPOSED — exact schemas are TO BE DECIDED during implementation. The structures below are illustrative.

## Data Models (Pydantic Schemas)

### SecurityEvent

The normalized input event that enters the system.

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class SecurityEvent(BaseModel):
    """A normalized security event for analysis."""
    event_id: str                           # Unique event identifier
    timestamp: datetime                     # When the event occurred
    event_type: str                         # Category: "network_flow", "email", "log_entry", etc.
    source_ip: Optional[str] = None         # Source IP address
    destination_ip: Optional[str] = None    # Destination IP address
    destination_port: Optional[int] = None  # Destination port
    protocol: Optional[str] = None          # Network protocol
    raw_content: str                        # Raw event data for analysis
    entity: Optional[str] = None            # User/host identifier for behavioral analysis
    metadata: Dict[str, Any] = {}           # Additional context
```

### AgentFinding

The standard output from any specialist agent.

```python
class AgentFinding(BaseModel):
    """Structured finding produced by a specialist agent."""
    agent: str                  # Agent identifier: "detection", "intelligence", "behavioral"
    event_id: str               # ID of the event being analyzed
    classification: str         # Classification label or assessment result
    evidence: str               # Specific evidence from the input supporting the conclusion
    confidence: str             # "high", "medium", "low", "none"
    reasoning: str              # Brief explanation of how the conclusion was reached
```

### VerificationResult

The output from the Verification Agent for a single finding.

```python
class VerificationResult(BaseModel):
    """Result of verifying a single agent finding."""
    agent: str                  # Which agent's finding was verified
    event_id: str               # ID of the event
    status: str                 # "verified_consistent", "verified_inconsistent", "inconclusive"
    reason: str                 # Explanation of why this status was assigned
```

### TrustScore

The trust evaluation output for a single agent.

```python
class TrustScore(BaseModel):
    """Trust score for an agent on a specific event."""
    agent: str                  # Agent identifier
    event_id: str               # ID of the event
    historical_accuracy: float  # Historical accuracy component (0.0–1.0)
    verification_score: float   # Verification result component (0.0–1.0)
    peer_agreement: float       # Peer agreement component (0.0–1.0)
    total_score: float          # Weighted combination of the three factors
```

### FinalRecommendation

The trust-weighted final output of the system.

```python
class FinalRecommendation(BaseModel):
    """Trust-weighted final recommendation."""
    event_id: str               # ID of the analyzed event
    classification: str         # Final classification
    confidence: str             # Overall confidence: "high", "medium", "low"
    routing: str                # "simulated_action", "further_verification", "human_review"
    agent_findings: list        # List of AgentFinding objects
    trust_scores: list          # List of TrustScore objects
    disagreement_summary: Optional[str] = None  # Summary if agents disagreed
    reasoning: str              # Explanation of how the recommendation was reached
```

## Module Interfaces

### Coordinator

```python
class Coordinator:
    """Dispatches events to agents and orchestrates the analysis pipeline."""

    def process_event(self, event: SecurityEvent) -> FinalRecommendation:
        """
        Run the full analysis pipeline for a single security event.

        1. Dispatch event to all specialist agents.
        2. Collect findings.
        3. Run verification on all findings.
        4. Run trust evaluation.
        5. Produce and return the final recommendation.
        """
        pass

    def dispatch_to_agents(self, event: SecurityEvent) -> list[AgentFinding]:
        """Send event to all specialist agents and collect findings."""
        pass
```

### BaseAgent

```python
class BaseAgent(ABC):
    """Abstract base class for all specialist agents."""

    @abstractmethod
    def analyze(self, event: SecurityEvent) -> AgentFinding:
        """Analyze a security event and return a structured finding."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the role-specific system prompt for this agent."""
        pass

    def format_event_for_prompt(self, event: SecurityEvent) -> str:
        """Convert a SecurityEvent to a string for inclusion in the LLM prompt."""
        pass
```

### VerificationAgent

```python
class VerificationAgent:
    """Checks agent findings for consistency with cited evidence."""

    def verify_findings(
        self,
        findings: list[AgentFinding],
        event: SecurityEvent
    ) -> list[VerificationResult]:
        """
        Verify each agent finding against the original event.
        Returns one VerificationResult per finding.
        """
        pass
```

### TrustEvaluator

```python
class TrustEvaluator:
    """Computes trust scores for agents based on three factors."""

    def evaluate(
        self,
        findings: list[AgentFinding],
        verification_results: list[VerificationResult]
    ) -> list[TrustScore]:
        """
        Compute trust scores for each agent.
        Combines historical accuracy, verification result, and peer agreement.
        """
        pass

    def update_history(self, agent: str, was_correct: bool) -> None:
        """Update an agent's historical accuracy record."""
        pass

    def get_historical_accuracy(self, agent: str) -> float:
        """Get an agent's current historical accuracy score."""
        pass
```

### RecommendationEngine

```python
class RecommendationEngine:
    """Produces the trust-weighted final recommendation."""

    def recommend(
        self,
        findings: list[AgentFinding],
        trust_scores: list[TrustScore]
    ) -> FinalRecommendation:
        """
        Combine agent findings weighted by trust scores into a final recommendation.
        Include routing suggestion and disagreement summary.
        """
        pass
```

### LLMClient

```python
class LLMClient:
    """Wrapper around LLM API calls."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ) -> str:
        """
        Send a prompt to the LLM and return the text response.
        Handles API errors, retries, and rate limiting.
        """
        pass

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel]
    ) -> BaseModel:
        """
        Send a prompt and parse the response into a Pydantic model.
        Raises an error if parsing fails after retries.
        """
        pass
```

## Configuration

```python
class SystemConfig(BaseModel):
    """System-wide configuration."""
    llm_model: str                          # Model identifier
    llm_api_key: str                        # API key (loaded from env var)
    trust_weight_historical: float = 0.4    # w1 — TO BE DECIDED
    trust_weight_verification: float = 0.35 # w2 — TO BE DECIDED
    trust_weight_peer: float = 0.25         # w3 — TO BE DECIDED
    confidence_threshold: float = 0.6       # Threshold for human review — TO BE DECIDED
    initial_trust_score: float = 0.5        # Starting trust for new agents — TO BE DECIDED
    data_dir: str = "./data"
    log_level: str = "INFO"
```

## Error Responses

All modules follow consistent error handling:

| Scenario | Behavior |
|---|---|
| LLM API failure | Return finding with `confidence: "none"`, log error |
| Invalid LLM output | Return finding with `confidence: "none"`, log raw output |
| Missing input data | Return explicit "no data" finding, do not default to benign |
| Schema validation failure | Raise `ValidationError` with details |
| Configuration error | Raise on startup with clear message |

## REST API (If Required)

If the team decides to expose a REST API (FastAPI, per D-007), the endpoints would be:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Submit a security event for analysis |
| `GET` | `/results/{event_id}` | Retrieve analysis results for an event |
| `GET` | `/trust/{agent}` | Get current trust scores for an agent |
| `GET` | `/health` | Health check |

> **Note:** A REST API is only built if the team decides it is needed. The system works as a Python library without one.

## Related Documentation

- `docs/SYSTEM_ARCHITECTURE.md` — Module architecture and project structure
- `docs/AGENT_DESIGN.md` — Agent design patterns and error handling
- `docs/architecture/DATA_FLOW.md` — Data flow through the system
- `docs/architecture/TRUST_MODEL.md` — Trust score formula details
