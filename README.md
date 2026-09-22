# Fine-Tuned Multi-Agent AI for Cyber Defense

A university semester project, developed by a team of three students, building a multi-agent AI system for cybersecurity analysis. Specialized agents examine a security event, compare and verify each other's findings, and produce a final recommendation weighted by a simple, understandable trust mechanism.

This is an academic learning project — not an enterprise cybersecurity platform.

## Problem

AI agents can assist with cybersecurity analysis, but their outputs may be incorrect, incomplete, conflicting, or misleading. Trusting every agent output equally risks poor decisions when one or more agents are wrong.

## Proposed Solution

Specialized agents (Detection, Intelligence, Behavioral Analysis) analyze a security event. A Verification Agent checks their findings against the evidence cited. A trust mechanism weighs each agent's influence on the final decision based on historical accuracy, verification results, and agreement with trusted peers. The final recommendation can route to a simulated action, further verification, or human review.

## Two Development Phases

- **Phase 1 — Baseline:** built using a normal/base LLM. Establishes the multi-agent structure, verification, and trust mechanism.
- **Phase 2 — Fine-Tuned System:** extends Phase 1 by introducing a fine-tuned open-source LLM (parameter-efficient fine-tuning, e.g. LoRA/QLoRA) and compares results against the Phase 1 baseline. Which agent(s) use the fine-tuned model is **TO BE DECIDED**.

Phase 1 is the baseline for Phase 2 — Phase 2 extends the same system rather than rebuilding it.

## Architecture Overview

```
Security Information
        ↓
Coordinator
        ↓
Detection / Intelligence / Behavioral Analysis
        ↓
Verification
        ↓
Trust Evaluation
        ↓
Final Recommendation
        ↓
Simulated Action / Further Verification / Human Review
```

Full detail: `docs/ARCHITECTURE.md`, `docs/architecture/AGENT_SPECIFICATION.md`, `docs/architecture/DATA_FLOW.md`.

## Fine-Tuning

Investigated in Phase 2 only, using parameter-efficient methods on an open-source LLM with cybersecurity-related data. The exact agent(s) fine-tuned is not yet decided. See `docs/RESEARCH.md`.

## Trust-Aware Decision Making

A conceptual trust score per agent, based on historical accuracy, verification results, and agreement with trusted peers — not on an agent's self-reported confidence. Verification result is one input into the trust score, applied once. See `docs/architecture/TRUST_MODEL.md`.

## Evaluation

Phase 1 (base LLM) is compared against Phase 2 (fine-tuned LLM) on a small set of meaningful, measurable dimensions. No results are assumed in advance. See `docs/RESEARCH.md`.

## Safety

This is a defensive, academic project. The system only ever recommends or simulates actions — it never executes real actions against live infrastructure. See `docs/THREAT_MODEL.md`.

## Repository Structure

```
docs/
  PROJECT_SCOPE.md
  ARCHITECTURE.md
  DECISIONS.md
  RESEARCH.md
  THREAT_MODEL.md
  architecture/
    AGENT_SPECIFICATION.md
    TRUST_MODEL.md
    DATA_FLOW.md
AGENTS.md
README.md
```

Application source code does not exist yet — the current state of the project is the documentation foundation above.

## Documentation

- [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) — problem, goals, phases, scope
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design and components
- [`docs/architecture/AGENT_SPECIFICATION.md`](docs/architecture/AGENT_SPECIFICATION.md) — per-agent detail
- [`docs/architecture/TRUST_MODEL.md`](docs/architecture/TRUST_MODEL.md) — trust mechanism
- [`docs/architecture/DATA_FLOW.md`](docs/architecture/DATA_FLOW.md) — data flow through the system
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decision log
- [`docs/RESEARCH.md`](docs/RESEARCH.md) — research foundation
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — threats and mitigations
- [`AGENTS.md`](AGENTS.md) — instructions for AI coding agents working in this repo

## Project Status

📄 Documentation foundation stage. No application code has been written yet. See `docs/DECISIONS.md` for decisions still requiring team approval before implementation begins.

## Team

Three students. See `docs/DECISIONS.md` (D-008) for the proposed (not yet approved) task distribution.
