# API Reference

This document defines the internal APIs, data schemas, and interfaces used by the project's components. Since this is a plain Python module project (not a distributed system), "API" here refers to the Python interfaces between modules, plus the data schemas that flow through the system.

> **Status:** IMPLEMENTED in Phase 1 (`feature/phase-1-baseline`). The executable source of truth is `src/models/` (schemas) and the modules named below; the schema blocks in this document are copied verbatim from those files (imports omitted). The contract is PR #8's finalized schema plus the additions listed under "Changes from PR #8". Methodology: `docs/PHASE1_IMPLEMENTATION.md`.

## Data Models (Pydantic Schemas, `src/models/`)

### Shared types and the label vocabulary (`src/models/types.py`)

`DETECTION_CLASSES` is the single source of truth for the UNSW-NB15 labels used by the Detection prompt, the Detection output schema, the dataset pipeline, Verification and evaluation.

```python
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
```

### SecurityEvent — system input (`src/models/events.py`)

```python
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
```

### AgentFinding — agent output and inter-agent message (`src/models/findings.py`)

`ModelFindingOutput` is what an agent produces; `DetectionModelOutput` is what the Detection **model** must generate (it is also the Phase 2 fine-tuning target). `agent`, `event_id`, `model` and `error` are set by code, never by a model. Agents never message each other: the Coordinator collects findings and passes them to Verification, Trust and the Recommendation Engine.

```python
_CANONICAL_CLASS = {c.lower(): c for c in DETECTION_CLASSES}


class ModelFindingOutput(BaseModel):
    """The part of a finding an LLM must generate (also the fine-tuning target)."""

    verdict: Verdict
    classification: str
    evidence: str
    confidence: Confidence
    reasoning: str


class DetectionModelOutput(ModelFindingOutput):
    """What the Detection model must generate (also its fine-tuning target).

    ``classification`` must be one of the canonical UNSW-NB15 labels
    (DETECTION_CLASSES); case and surrounding whitespace are normalised, any
    other label makes the output schema-invalid.
    """

    @field_validator("classification")
    @classmethod
    def _canonical_label(cls, value: str) -> str:
        canonical = _CANONICAL_CLASS.get(value.strip().lower())
        if canonical is None:
            raise ValueError(f"classification must be one of {list(DETECTION_CLASSES)}")
        return canonical


class AgentFinding(ModelFindingOutput):
    """Structured finding produced by a specialist agent.

    ``agent``, ``event_id``, ``model`` and ``error`` are set by code, never by
    a model. ``evidence`` is a comma-separated list of ``field=value`` pairs
    copied from the event so Verification can check it mechanically.
    """

    agent: AgentName
    event_id: str
    model: Optional[str] = None  # engine that produced it (per agent -> Detection-only Phase 2)
    error: Optional[str] = None
```

What each agent emits:

| Agent | `verdict` / `classification` values |
|---|---|
| Detection | any `Verdict`; `classification` ∈ `DETECTION_CLASSES` (or `agent_error` on failure) |
| Intelligence | `malicious` + `known_malicious_indicator` / `known_malicious_signature`; `benign` + `known_benign_signature`; `unknown` + `no_match` / `no_indicators` |
| Behavioral Analysis | `suspicious` + `baseline_deviation`; `benign` (confidence `low`) + `within_baseline`; `unknown` + `no_baseline` / `no_comparable_fields` |

### VerificationResult (`src/models/verification.py`)

```python
class VerificationResult(BaseModel):
    """Result of verifying a single agent finding."""

    agent: AgentName
    event_id: str
    status: VerificationStatus
    reason: str
```

### TrustScore and WeightingOutcome (`src/models/trust.py`)

```python
class TrustScore(BaseModel):
    agent: AgentName
    event_id: str
    historical_accuracy: float = Field(ge=0.0, le=1.0)
    verification_score: float = Field(ge=0.0, le=1.0)
    peer_agreement: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)


class WeightingOutcome(BaseModel):
    method: Literal["trust_weighted", "equal_weighted"]
    verdict: Verdict  # "unknown" when tied or no votes
    verdict_weights: Dict[str, float]
    tie: bool = False
```

### FinalRecommendation — system output (`src/models/recommendation.py`)

```python
class SimulatedAction(BaseModel):
    """A simulated response action. Can never represent a real action (D-011)."""

    description: str
    executed: Literal[False] = False


class FinalRecommendation(BaseModel):
    """Final structured output consumed by the frontend and by evaluation."""

    run_id: str
    event_id: str
    phase: Literal[1, 2]
    model: str  # summary of agent_models, e.g. "detection=Qwen/...; intelligence=rules:..."
    agent_models: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    is_mock: bool = False

    classification: str
    verdict: Verdict
    confidence: Confidence
    confidence_value: float = Field(ge=0.0, le=1.0)
    routing: Routing
    routing_reason: str
    simulated_action: Optional[SimulatedAction] = None

    agent_findings: list[AgentFinding]
    verification_results: list[VerificationResult]
    trust_scores: list[TrustScore]
    trust_weighted: WeightingOutcome
    equal_weighted: WeightingOutcome
    trust_changed_outcome: bool

    disagreement_summary: Optional[str] = None
    reasoning: str
```

### Changes from PR #8's schema

All additive except the stricter IP and label typing:

1. `SecurityEvent.source_ip` / `destination_ip` are `IPvAnyAddress` (PR #8 described IP typing but kept `str`).
2. `DetectionModelOutput` restricts the Detection `classification` to `DETECTION_CLASSES`.
3. `AgentFinding.model` records the engine behind each finding; `FinalRecommendation.agent_models` records all of them (`model` stays as a summary string). This makes a Detection-only Phase 2 (D-010) representable.

## Module Interfaces

### Coordinator (`src/coordinator/coordinator.py`)

```python
class Coordinator:
    def __init__(self, agents: dict, verifier: VerificationAgent, trust: TrustEvaluator,
                 recommender: RecommendationEngine, run_id: str, phase: int = 1): ...

    def process_event(self, event: SecurityEvent | dict) -> FinalRecommendation:
        """Validate the event, run Detection -> Intelligence -> Behavioral Analysis
        (independently), verify every finding, score trust, recommend."""

    def dispatch_to_agents(self, event: SecurityEvent) -> list[AgentFinding]:
        """An exception inside an agent becomes that agent's error finding;
        the pipeline continues."""
```

Built from configuration by `src.pipeline.build_coordinator(config, detection_llm=None, run_id=None, history=None)`.

### Agents (`src/agents/`)

```python
class BaseAgent(ABC):
    name: str       # "detection" | "intelligence" | "behavioral"
    model_id: str   # e.g. "Qwen/Qwen3-4B-Instruct-2507", "rules:ioc-and-signature-lookup-v2"

    @abstractmethod
    def analyze(self, event: SecurityEvent) -> AgentFinding: ...

class DetectionAgent(BaseAgent):                 # LLM; the Phase 2 fine-tuning target
    def __init__(self, llm: LLMClient, max_attempts: int = 2): ...
    last_trace: DetectionTrace                  # outcome: valid | schema_invalid | transport_failure | execution_failure

class IntelligenceAgent(BaseAgent):              # rules: IOC + train-split flow signatures
    @classmethod
    def from_file(cls, path: Path, signatures_path: Path | None = None) -> "IntelligenceAgent": ...

class BehavioralAgent(BaseAgent):                # rules: entity / train-split normal-profile comparison
    @classmethod
    def from_files(cls, profiles_path: Path, entities_path: Path) -> "BehavioralAgent": ...

class VerificationAgent:                         # rules: evidence grounding + consistency
    def verify(self, finding: AgentFinding, event: SecurityEvent) -> VerificationResult: ...
    def verify_findings(self, findings: list[AgentFinding], event: SecurityEvent) -> list[VerificationResult]: ...
```

The Detection prompt (`src/agents/prompts.py`: `DETECTION_INSTRUCTION`, `format_detection_input`) is shared with the fine-tuning data builder, so Phase 1 and Phase 2 send identical prompts.

### Trust (`src/trust/`)

```python
class TrustHistory:
    def __init__(self, accuracy: dict[str, float] | None = None, initial: float = 0.5, source: str = "default"): ...
    def get(self, agent: str) -> float: ...
    @classmethod
    def load(cls, path: Path, initial: float = 0.5) -> "TrustHistory": ...

def calibrate(agents: dict, events: list, config_summary: dict) -> dict:
    """Historical accuracy per agent on the validation calibration subset (never test)."""

class TrustEvaluator:
    def __init__(self, history: TrustHistory, w_hist: float = 0.40, w_ver: float = 0.35, w_peer: float = 0.25): ...
    def evaluate(self, findings: list[AgentFinding],
                 verification: list[VerificationResult]) -> list[TrustScore]: ...
```

Trust is not updated online during evaluation; history changes only by re-running calibration.

### RecommendationEngine (`src/recommendation/recommender.py`)

```python
class RecommendationEngine:
    def __init__(self, confidence_threshold: float = 0.60): ...
    def recommend(self, *, event_id: str, run_id: str, phase: int, agent_models: dict[str, str],
                  is_mock: bool, findings: list[AgentFinding], verification_results: list[VerificationResult],
                  trust_scores: list[TrustScore], action_target: str) -> FinalRecommendation: ...
```

### LLMClient (`src/utils/llm_client.py`)

```python
class LLMClient:
    model_id: str
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Raises LLMError on transport/server failure (distinct from an unparseable answer)."""

class OpenAICompatibleClient(LLMClient): ...   # any OpenAI-compatible server (vLLM, Ollama) via the OpenAI SDK
class StubLLMClient(LLMClient): ...            # deterministic offline stand-in; model ids start with "stub:"

def build_llm_client(config: SystemConfig, agent: str = "detection") -> LLMClient: ...
```

Structured parsing happens in the Detection agent (`parse_model_output` → `DetectionModelOutput`), not in the client.

### Backend API for the frontend (`src/api.py`)

```python
def analyze_event(event: dict | SecurityEvent, coordinator: Coordinator | None = None) -> FinalRecommendation:
    """Validate and run the full pipeline in-process. Raises pydantic.ValidationError on bad input."""
```

### Evaluation (`src/evaluation/`)

```python
def run_calibration(config: SystemConfig, detection_llm=None, limit=None, log=print) -> Path: ...
def run_evaluation(config: SystemConfig, detection_llm=None, limit=None, run_id=None, log=print,
                   allow_uncalibrated: bool = False) -> Path:
    """Raises CalibrationMissingError (real model, no calibration) or
    CalibrationMismatchError (stale calibration)."""
def compute_metrics(records: list[dict]) -> dict: ...   # the four D-016 metrics
```

## Configuration (`src/config.py`)

`SystemConfig` is built from environment variables by `SystemConfig.from_env()`; no secrets are stored in code, and the API key is never written to run outputs.

| Field | Env var | Default |
|---|---|---|
| `phase` | `PHASE` | `1` |
| `llm_backend` | `LLM_BACKEND` | `openai` (`stub` for offline runs) |
| `llm_base_url` | `LLM_BASE_URL` | `http://localhost:8000/v1` |
| `llm_model` | `LLM_MODEL` | `Qwen/Qwen3-4B-Instruct-2507` |
| `llm_api_key` | `LLM_API_KEY` | `EMPTY` (local servers ignore it) |
| `agent_models` | `DETECTION_MODEL` | `{}`; Phase 2 sets `{"detection": "<fine-tuned id>"}` |
| `llm_temperature`, `llm_max_tokens`, `llm_timeout_s`, `llm_seed` | — | `0.0`, `512`, `120`, `42` |
| `trust_weight_historical` / `_verification` / `_peer` | — | `0.40` / `0.35` / `0.25` (must sum to 1) |
| `confidence_threshold` | — | `0.60` |
| `initial_trust_score` | — | `0.50` (only for agents without calibration votes; recorded per run) |
| `data_dir`, `runs_dir` | `DATA_DIR`, `RUNS_DIR` | `data/`, `runs/` |

## Error Responses

| Scenario | Behavior |
|---|---|
| Model server failure (down, timeout, empty reply) | Detection returns an error finding (`verdict: unknown`, `confidence: none`); trace outcome `transport_failure` |
| Unparseable / schema-invalid model output | One retry; then an error finding; trace outcome `schema_invalid` |
| Exception inside any agent | That agent's error finding; the pipeline continues; Detection trace outcome `execution_failure` |
| Missing reference data (no indicator match, no baseline) | Explicit abstention (`no_match`, `no_indicators`, `no_baseline`), never benign |
| Invalid input event | `pydantic.ValidationError` with field details (CLI/frontend show them) |
| Real evaluation without calibration | `CalibrationMissingError`, CLI exit 1 |
| Stale calibration (agents or reference data changed) | `CalibrationMismatchError`, CLI exit 1 |

## REST API (If Required)

If the team decides to expose a REST API (FastAPI, per D-007), the endpoints would be:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Submit a security event for analysis |
| `GET` | `/results/{event_id}` | Retrieve analysis results for an event |
| `GET` | `/trust/{agent}` | Get current trust scores for an agent |
| `GET` | `/health` | Health check |

> **Note:** Not built in Phase 1. The frontend calls `src.api.analyze_event()` in-process (see the D-013 proposal in PR #8).

## Related Documentation

- `docs/SYSTEM_ARCHITECTURE.md` — Module architecture and project structure
- `docs/AGENT_DESIGN.md` — Agent design patterns and error handling
- `docs/architecture/DATA_FLOW.md` — Data flow through the system
- `docs/architecture/TRUST_MODEL.md` — Trust score formula details
