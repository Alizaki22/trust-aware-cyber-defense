# Threat Model

## Purpose

Identify realistic, student-level risks relevant to a defensive, academic multi-agent cybersecurity prototype, so the team designs the system with an awareness of its own limitations rather than presenting it as more robust than it is.

## Assets

- The integrity of the final recommendation produced by the system.
- The trust scores associated with each agent (if manipulated, they could mislead the whole system).
- Any real or synthetic security data used for testing.
- The credibility of the project's evaluation results.

## Trust Boundaries

- Between the raw security event (external, untrusted input) and the agents that process it.
- Between individual agents (each agent's output is untrusted input to Verification and Trust Evaluation, not automatically accepted).
- Between the system's final recommendation and any downstream response — which is always a **simulated action**, never a real one, and is itself a trust boundary the system must not cross.

## Threat Actors

For an academic, defensive-only project, the realistic threat actors are conceptual/simulated rather than real adversaries: a deliberately misconfigured or "compromised" agent introduced by the team itself for demonstration purposes, and, in a general sense, whoever supplies the input event data (since the system must not blindly trust arbitrary input).

## Threats

### Threat: Incorrect Agent Outputs

**Description:** An agent produces a wrong classification or assessment due to model limitations, ambiguous input, or insufficient training/prompting.

**Impact:** Could bias the final recommendation if not caught by verification/trust weighting.

**Affected component:** Any specialist agent (Detection, Intelligence, Behavioral Analysis).

**Possible mitigation:** Verification step; trust-weighting reduces a chronically inaccurate agent's influence over time.

**Remaining limitation:** Verification and trust weighting reduce, but do not eliminate, the impact of an incorrect output — especially on the first occurrence, before trust history accumulates.

### Threat: Conflicting Agent Information

**Description:** Agents produce genuinely contradictory findings on the same event.

**Impact:** Ambiguous or unstable final recommendation if not handled explicitly.

**Affected component:** Trust Evaluation / Final Recommendation.

**Possible mitigation:** Trust-weighted aggregation; explicit routing to human review when disagreement is significant.

**Remaining limitation:** Trust weighting can still produce a confident-looking wrong answer if the higher-trust agent happens to be wrong on a given event.

### Threat: LLM Hallucination

**Description:** An LLM-based agent states a conclusion not actually supported by the input evidence (e.g., citing an indicator that isn't in the event).

**Impact:** Misleading finding entering the pipeline.

**Affected component:** Any LLM-based agent.

**Possible mitigation:** Verification explicitly checks cited evidence against the actual input.

**Remaining limitation:** Verification is itself an LLM-based component (unless implemented otherwise) and can itself be wrong or fooled; this is a known, unresolved limitation, not something this project claims to fully solve.

### Threat: Prompt Injection (Where Relevant)

**Description:** If any agent processes raw, potentially attacker-influenced text (e.g., a phishing email body) as part of its prompt, that text could attempt to manipulate the agent's behavior.

**Impact:** Could cause an agent to misclassify an event or produce misleading output.

**Affected component:** Any agent that includes raw external content directly in its prompt.

**Possible mitigation:** Treat raw event content as data to be analyzed, not as instructions; keep agent system prompts separate from analyzed content; verification cross-checks outputs against the original event.

**Remaining limitation:** Prompt injection defenses in this project are basic and academic in scope, not a hardened security control.

### Threat: Trust Manipulation

**Description:** In the adversarial demonstration scenario, or hypothetically in a real deployment, a series of crafted inputs could attempt to game an agent's trust score upward or downward artificially.

**Impact:** Could cause the system to over- or under-weight a specific agent incorrectly.

**Affected component:** Trust Evaluation.

**Possible mitigation:** Base trust updates on verifiable outcomes rather than self-reported signals; rate-limit how much a single event can move a trust score.

**Remaining limitation:** With a small number of demo events, trust scores are statistically thin and easier to skew than they would be with a large, real-world event history.

### Threat: Data Poisoning

**Description:** If Phase 2 fine-tuning data is drawn from an untrusted or unvetted source, it could bias the fine-tuned model in unintended ways.

**Impact:** Fine-tuned agent could perform worse or behave unpredictably compared to the base LLM.

**Affected component:** Phase 2 fine-tuned model (specific agent not yet decided — see `docs/DECISIONS.md`, D-010).

**Possible mitigation:** Use vetted, appropriately licensed datasets; inspect training data before use; compare fine-tuned model behavior against the Phase 1 baseline.

**Remaining limitation:** A small student team cannot fully audit a large dataset for subtle poisoning; this project relies on using reputable, established sources rather than proving data purity.

### Threat: Human Over-Reliance on AI Decisions

**Description:** A human reviewer could over-trust the system's final recommendation simply because it is presented confidently or with a numeric trust score.

**Impact:** Reduces the value of the human-review safety path if the human doesn't actually scrutinize the recommendation.

**Affected component:** Human Review stage of the Final Recommendation.

**Possible mitigation:** Present trust scores and disagreement explicitly, with clear framing that this is a heuristic, not a certified probability of correctness.

**Remaining limitation:** This project cannot control how a human reviewer chooses to interpret or act on the system's output.

## Security Assumptions

- The project operates only in authorized, controlled academic environments using synthetic or appropriately licensed data.
- No component of this system is connected to, or takes action against, live production infrastructure — **all system actions are simulated, never real** (see `docs/DECISIONS.md`, D-011).
- Verification is assumed to be a good-faith component, not itself adversarial — its own reliability is a documented limitation, not a threat vector this project defends against.

## Mitigations Summary

No mitigation listed above is claimed to fully eliminate its associated threat. All mitigations are partial, academic-scope measures appropriate to a semester project, not production-grade security controls.
