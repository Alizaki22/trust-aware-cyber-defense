# API Reference

This document defines the internal APIs, data schemas, and interfaces used by the project's components. Since this is a plain Python module project (not a distributed system), "API" here refers to the Python interfaces between modules, plus the data schemas that flow through the system.

> **Status:** FINALIZED (Day 2) for the shapes below. Numeric values inside them (trust weights, confidence threshold, initial trust score) remain **TO BE DECIDED** — see `docs/architecture/TRUST_MODEL.md` and `SystemConfig` below. This document incorporates the schema proposal from `docs/frontend/SCHEMA_PROPOSAL.md` (Member 3, Day 1) — see M1's response at the bottom of that file for what was adopted, changed, or deferred.

## Shared Types

```python
from typing import Literal

Verdict = Literal["malicious", "suspicious", "benign", "unknown"]
"""Comparable outcome scale used by every agent and by the final recommendation.
Agents answer different underlying questions (a classification, an IOC match,
an anomaly assessment); `verdict` is the single scale that lets Trust
Evaluation combine them, compute peer agreement, and let the frontend show
them comparably. `unknown` means the agent abstained (e.g. "no match" or
"no baseline available") rather than asserting benign — see AGENT_SPECIFICATION
for why "no data" must never collapse into "benign"."""

Confidence = Literal["high", "medium", "low", "none"]
VerificationStatus = Literal["verified_consistent", "verified_inconsistent", "inconclusive"]
Routing = Literal["simulated_action", "further_verification", "human_review"]
AgentName = Literal["detection", "intelligence", "behavioral"]
```

## Data Models (Pydantic Schemas)

### SecurityEvent

The normalized input event that enters the system.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class SecurityEvent(BaseModel):
    """A normalized security event for analysis."""
    event_id: str = Field(min_length=1, max_length=64)            # Unique event identifier
    timestamp: datetime                     # ISO 8601. When the event occurred
    event_type: str                         # Category: "network_flow", "email", "log_entry", etc.
    source_ip: Optional[str] = None         # Source IP address (IPv4/IPv6 if present)
    destination_ip: Optional[str] = None    # Destination IP address (IPv4/IPv6 if present)
    destination_port: Optional[int] = Field(default=None, ge=0, le=65535)  # Destination port
    protocol: Optional[str] = None          # Network protocol
    raw_content: str = Field(min_length=1, max_length=10_000)  # Raw event data for analysis. Untrusted — see Security Notes below
    entity: Optional[str] = None            # User/host identifier for behavioral analysis
    metadata: Dict[str, Any] = {}           # Additional context. metadata.source = "SYNTHETIC" flags synthetic test data
```

**Security note:** `raw_content` is untrusted input (it may be attacker-controlled, e.g. a phishing email body). It is treated purely as data to analyze, never as instructions — agent prompts keep it separate from the system prompt (see `docs/AGENT_DESIGN.md`), and any UI rendering it must escape it as plain text, never HTML/Markdown. See `docs/THREAT_MODEL.md` (prompt injection).

**`raw_content` length limit:** 10,000 characters is a starting placeholder pending confirmation from M2 on token-cost impact once a base model is selected (D-007's `LLM_MODEL` is still TBD). Revisit once real token budgets are known.

**File input:** one `SecurityEvent` per `.json` file. Multi-event upload/batch input is out of scope for the MVP.

### AgentFinding

The standard output from any specialist agent — this **is** the inter-agent message format. There is no separate message envelope: agents don't message each other directly (see the Coordinator sequence in `docs/AGENT_DESIGN.md`), so `AgentFinding` is both the agent's structured output *and* the unit of information the Coordinator collects and passes downstream to Verification and Trust Evaluation. Sender = `agent`; receiver is always the Coordinator; task identifier = `event_id`.

```python
class AgentFinding(BaseModel):
    """Structured finding produced by a specialist agent."""
    agent: AgentName            # Which agent produced this finding
    event_id: str               # ID of the event being analyzed
    verdict: Verdict            # Comparable outcome scale — used for peer agreement and voting
    classification: str         # Free-text, detailed classification label (e.g. "ddos_attack", "known_malicious_ip")
    evidence: str                # Specific evidence from the input supporting the conclusion
    confidence: Confidence      # "high", "medium", "low", "none"
    reasoning: str               # Brief explanation of how the conclusion was reached
    error: Optional[str] = None  # Set when the agent failed (LLM/parse/API error) — distinct from an agent that ran but is unsure. See Error Responses below.
```

`verdict` vs `classification`: `verdict` is the coarse, comparable scale every agent shares (needed so Trust Evaluation can compute peer agreement and a weighted vote across agents that otherwise answer different kinds of questions). `classification` stays as the agent's detailed, free-text label. `verdict: "unknown"` is how an agent abstains — e.g. Intelligence's "no known indicator" or Behavioral's "no baseline available" — and must never be conflated with `verdict: "benign"` (see `docs/architecture/AGENT_SPECIFICATION.md`).

`error` vs `confidence: "none"`: both can occur together, but they mean different things. `error` set means the agent's call itself failed (timeout, parse failure) — a technical fault. `confidence: "none"` with no `error` means the agent ran successfully but has no basis for a conclusion (e.g. no threat-intel data available). Keeping them separate lets the system (and the UI) show "this agent failed" distinctly from "this agent is honestly unsure."

### VerificationResult

The output from Verification for a single finding.

```python
class VerificationResult(BaseModel):
    """Result of verifying a single agent finding."""
    agent: AgentName             # Which agent's finding was verified
    event_id: str                # ID of the event
    status: VerificationStatus   # "verified_consistent", "verified_inconsistent", "inconclusive"
    reason: str                  # Explanation of why this status was assigned
```

### TrustScore

The trust evaluation output for a single agent.

```python
class TrustScore(BaseModel):
    """Trust score for an agent on a specific event."""
    agent: AgentName             # Agent identifier
    event_id: str                # ID of the event
    historical_accuracy: float = Field(ge=0.0, le=1.0)  # Historical accuracy component
    verification_score: float = Field(ge=0.0, le=1.0)   # Verification result component
    peer_agreement: float = Field(ge=0.0, le=1.0)        # Peer agreement component
    total_score: float = Field(ge=0.0, le=1.0)           # Weighted combination of the three factors
```

### WeightingOutcome / SimulatedAction (helper models)

```python
class WeightingOutcome(BaseModel):
    """One aggregation method's verdict and how it got there."""
    method: Literal["trust_weighted", "equal_weighted"]
    verdict: Verdict                    # "unknown" when tied or no findings
    verdict_weights: Dict[str, float]   # verdict -> summed weight, for display
    tie: bool = False                   # No single winning verdict

class SimulatedAction(BaseModel):
    """A simulated response action. Can never represent a real action (D-011)."""
    description: str                    # e.g. "Would block 203.0.113.45 at the firewall"
    executed: Literal[False] = False    # Always False — makes D-011 part of the schema itself
```

### FinalRecommendation

The trust-weighted final output of the system — this is what the frontend/API consumer receives.

```python
class FinalRecommendation(BaseModel):
    """Trust-weighted final recommendation."""
    event_id: str                       # ID of the analyzed event
    run_id: str                         # Unique identifier for this run (links Phase Comparison rows back to runs)
    phase: Literal[1, 2]                # Which phase produced this result
    model: str                          # Model identifier actually used (names the model without assuming which agent is fine-tuned — D-010)
    created_at: datetime                # When this recommendation was produced
    is_mock: bool = False               # True when served from fixtures/mock data rather than a real run

    verdict: Verdict                    # Final verdict on the comparable scale
    classification: str                 # Final free-text classification
    confidence: Confidence              # Overall confidence label
    confidence_value: float = Field(ge=0.0, le=1.0)  # Numeric confidence backing the label, so routing has a threshold to compare against
    routing: Routing                    # "simulated_action", "further_verification", "human_review"
    routing_reason: str                 # Why this routing was chosen (e.g. "winning share 0.51 below threshold 0.60")
    simulated_action: Optional[SimulatedAction] = None  # Present only when routing == "simulated_action"

    agent_findings: list[AgentFinding]
    verification_results: list[VerificationResult]
    trust_scores: list[TrustScore]

    trust_weighted: WeightingOutcome    # The actual aggregation method used to reach `verdict`
    equal_weighted: WeightingOutcome    # Same findings aggregated with all agents weighted equally — the control condition for Experiment 2
    trust_changed_outcome: bool         # True when trust_weighted.verdict != equal_weighted.verdict

    disagreement_summary: Optional[str] = None  # Summary if agents disagreed
    reasoning: str                      # Explanation of how the recommendation was reached
```

`confidence` vs `confidence_value`: `confidence_threshold` in `SystemConfig` is a float, so routing needs a number to compare against; `confidence_value` is that number, and `confidence` is the label derived from it for display. Both are returned so the API doesn't force the frontend to re-derive one from the other.

`trust_weighted` / `equal_weighted` are both always computed and returned, not just the winning one — this directly supports Experiment 2 (trust-weighting demonstration) and lets the frontend show the "Trust Impact" comparison without recomputing aggregation logic client-side. Aggregation method, tie-breaking, and routing thresholds are implementation details of the Coordinator/RecommendationEngine and remain **TO BE DECIDED** during Day 3–4 implementation; this schema only fixes their *shape*, not their values.

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
        event_id: str,
        run_id: str,
        phase: Literal[1, 2],
        model: str,
        findings: list[AgentFinding],
        verification_results: list[VerificationResult],
        trust_scores: list[TrustScore]
    ) -> FinalRecommendation:
        """
        Combine agent findings weighted by trust scores into a final recommendation.
        Computes both trust_weighted and equal_weighted outcomes (so the two can
        be compared), sets trust_changed_outcome, and produces a routing
        suggestion, routing_reason, and disagreement summary.
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

All modules follow consistent error handling. `AgentFinding.error` distinguishes a technical failure from honest uncertainty — see the note under `AgentFinding` above.

| Scenario | Behavior |
|---|---|
| LLM API failure | Return finding with `confidence: "none"`, `error` set to a short message, log the full error |
| Invalid LLM output | Return finding with `confidence: "none"`, `error` set (e.g. "failed to parse structured output"), log raw output |
| Missing input data (e.g. no IOC/baseline available) | Return explicit "no data" finding: `verdict: "unknown"`, `confidence: "none"` or `"low"`, `error` left `None` — this is not a failure, do not default to benign |
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
