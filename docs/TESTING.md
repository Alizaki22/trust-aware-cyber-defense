# Testing

This document describes the testing strategy for the project, covering test types, tools, conventions, and how testing supports the Phase 1 vs. Phase 2 comparison.

## Testing Philosophy

- **Test important functionality.** Not every line needs a test, but critical paths (agent output parsing, trust calculation, verification logic, recommendation generation) must be tested.
- **Test honestly.** Never claim tests passed without actually running them. Report failures honestly.
- **Test before claiming "it works."** Code must be verified to run before being merged.
- **Keep tests simple.** Tests should be easy to write, read, and maintain — matching the project's overall simplicity-first approach.

## Testing Tools

| Tool | Purpose |
|---|---|
| pytest | Test runner and assertion framework |
| pytest-cov (optional) | Code coverage reporting |
| Pydantic | Validates data schemas in tests |

No additional testing frameworks or libraries are required unless the team decides otherwise.

## Test Types

### Unit Tests

Test individual functions and classes in isolation.

**What to unit test:**
- Trust score calculation (given inputs, verify correct output).
- Verification logic (given a finding and event, verify correct consistency check).
- Data model validation (Pydantic schema accepts valid data, rejects invalid data).
- Input processing (raw event → normalized SecurityEvent).
- Recommendation logic (given findings and trust scores, verify correct weighted output).
- LLM output parsing (given raw LLM text, verify correct structured finding extraction).

**Example structure:**

```python
# tests/unit/test_trust_model.py

def test_trust_score_calculation():
    """Trust score should be the weighted combination of three factors."""
    score = calculate_trust(
        historical_accuracy=0.8,
        verification_result=1.0,  # verified consistent
        peer_agreement=0.5,
        weights=(0.4, 0.35, 0.25)
    )
    expected = 0.4 * 0.8 + 0.35 * 1.0 + 0.25 * 0.5  # 0.795
    assert abs(score - expected) < 0.001

def test_trust_score_with_failed_verification():
    """A verified-inconsistent finding should lower the trust score."""
    score = calculate_trust(
        historical_accuracy=0.8,
        verification_result=0.0,  # verified inconsistent
        peer_agreement=0.5,
        weights=(0.4, 0.35, 0.25)
    )
    assert score < 0.5  # Significantly lower than a consistent finding
```

### Integration Tests

Test how modules work together.

**What to integration test:**
- Coordinator dispatches event → agents produce findings → verification runs → trust evaluates → recommendation produced.
- End-to-end pipeline with a mock LLM client (returning predetermined responses).
- Trust history persistence — write scores, reload, verify consistency.

**Example structure:**

```python
# tests/integration/test_pipeline.py

def test_end_to_end_pipeline(mock_llm_client):
    """Full pipeline should produce a valid FinalRecommendation."""
    event = create_test_event("suspicious_login")
    coordinator = Coordinator(llm_client=mock_llm_client)

    recommendation = coordinator.process_event(event)

    assert recommendation.event_id == event.event_id
    assert recommendation.classification != ""
    assert recommendation.routing in ["simulated_action", "further_verification", "human_review"]
    assert len(recommendation.agent_findings) == 3
    assert len(recommendation.trust_scores) == 3
```

### Scenario-Based Tests

Test the system against predefined security scenarios with expected behaviors.

**Scenarios to test:**

| Scenario | Expected Behavior |
|---|---|
| Clear malicious event (e.g., known DDoS pattern) | All agents agree, high confidence, simulated action |
| Ambiguous event (e.g., unusual but not clearly malicious) | Agents may disagree, lower confidence, human review |
| Deliberately wrong agent finding | Trust weighting reduces the wrong agent's influence |
| Missing data (e.g., no threat intel match) | Intelligence agent reports "no match," not "benign" |
| Agent failure (e.g., LLM error) | Failed agent treated as low-confidence, system continues |
| Trust demonstration | Trust-weighted result differs from equal-weighted result |

### Phase 1 vs. Phase 2 Comparison Tests

Run the same scenario set through both Phase 1 (base LLM) and Phase 2 (fine-tuned LLM) configurations and compare:

- Are the classifications different?
- Are confidence levels different?
- Does trust weighting change the outcome differently?
- Does the fine-tuned model reduce hallucination?

See `docs/EXPERIMENTS.md` for the formal experiment design.

## Test Data Management

### Test Fixtures

- Predefined security events stored in `tests/fixtures/events/`.
- Expected agent outputs stored in `tests/fixtures/expected/`.
- Mock LLM responses stored in `tests/fixtures/llm_responses/`.

### Mock LLM Client

For unit and integration tests, use a mock LLM client that returns predetermined responses instead of calling a real API. This ensures:

- Tests are deterministic (same input → same output every time).
- Tests are fast (no API latency).
- Tests don't require API keys or network access.
- Tests don't cost money (no API charges).

```python
class MockLLMClient:
    """Returns predetermined responses for testing."""

    def __init__(self, responses: dict):
        self.responses = responses

    def generate(self, system_prompt, user_prompt, **kwargs):
        key = self._make_key(system_prompt, user_prompt)
        return self.responses.get(key, '{"error": "no mock response"}')
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/
│   ├── test_trust_model.py
│   ├── test_verification.py
│   ├── test_data_models.py
│   ├── test_input_processing.py
│   ├── test_recommendation.py
│   └── test_llm_parsing.py
├── integration/
│   ├── test_pipeline.py
│   ├── test_trust_history.py
│   └── test_agent_coordination.py
├── scenarios/
│   ├── test_clear_malicious.py
│   ├── test_ambiguous_event.py
│   ├── test_wrong_agent.py
│   └── test_trust_demonstration.py
└── fixtures/
    ├── events/
    ├── expected/
    └── llm_responses/
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only scenario tests
pytest tests/scenarios/

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/unit/test_trust_model.py

# Run a specific test function
pytest tests/unit/test_trust_model.py::test_trust_score_calculation
```

## Test Conventions

1. **File naming:** `test_<module_name>.py`
2. **Function naming:** `test_<what_is_being_tested>`
3. **One assertion per concept** (multiple asserts are fine if they test the same logical assertion).
4. **Use descriptive docstrings** explaining what the test verifies and why.
5. **Keep tests independent** — no test should depend on another test running first.
6. **Clean up after tests** — use fixtures with teardown for any file/state changes.

## Continuous Testing

During development:
- Run relevant unit tests after each code change.
- Run the full test suite before committing.
- Run scenario tests before creating a PR.
- Include test results in PR descriptions.

## Related Documentation

- `docs/EXPERIMENTS.md` — Formal experiment design using these tests
- `docs/DEVELOPMENT_GUIDE.md` — How to set up the environment and run tests
- `docs/API_REFERENCE.md` — Data schemas used in test assertions
