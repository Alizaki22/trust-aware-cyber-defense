# Project Scope

## Project Title

Fine-Tuned Multi-Agent AI for Cyber Defense

## Project Overview

This is a university semester project developed by a team of **three students**. The project builds a multi-agent AI system for cybersecurity analysis, in which multiple specialized agents examine security information, compare and verify each other's findings, and produce a final recommendation weighted by a simple trust mechanism. The project is developed in two connected phases: a baseline built on a normal/base LLM, and an extension that introduces a fine-tuned open-source LLM.

This is **not** an enterprise cybersecurity product. It is an academic, defensive-only, learning-first prototype.

## Problem Statement

AI agents can assist with cybersecurity analysis, but their outputs may be incorrect, incomplete, conflicting, uncertain, or misleading. When multiple AI agents cooperate, blindly trusting every output can lead to poor cybersecurity decisions. This project explores a simple multi-agent approach in which agent outputs are analyzed, compared, verified, evaluated using a simple trust mechanism, and used to produce a final recommendation.

## Proposed Solution

Specialized agents (Detection, Intelligence, Behavioral Analysis, Verification) analyze a security event and produce structured findings. A verification step checks findings for consistency. A trust mechanism scores each agent based on historical accuracy, verification results, and agreement with trusted peers. A final recommendation is produced and may be routed to a simulated action, further verification, or human review.

## Learning Objectives

1. Learn AI and LLM development.
2. Learn multi-agent AI.
3. Learn cybersecurity concepts.
4. Learn LLM fine-tuning.
5. Learn collaborative software development.
6. Learn Git and GitHub workflows.
7. Build a working and demonstrable academic prototype.
8. Evaluate what is built.

## Team

Three students. Task distribution is proposed in `DECISIONS.md` and is not final until the team approves it. All members are expected to understand the complete system, not only their assigned area.

## Two-Phase Development

**Phase 1 is the baseline for Phase 2.** Phase 2 extends Phase 1; it does not replace or rebuild it.

### Phase 1 Scope — Baseline (Normal/Base LLM)

- Use a normal/base LLM (no fine-tuning) for all agents.
- Build the multi-agent structure: Detection, Intelligence, Behavioral Analysis, Verification.
- Implement agent communication and structured outputs.
- Implement a simple verification step.
- Implement a simple, conceptual trust mechanism.
- Produce a working, demonstrable end-to-end prototype.
- Establish the evaluation baseline.

### Phase 2 Scope — Fine-Tuned System

- Introduce a fine-tuned open-source LLM (parameter-efficient methods such as LoRA/QLoRA to be investigated).
- Reuse the Phase 1 multi-agent structure, verification, and trust mechanism.
- Compare Phase 1 (base LLM) against Phase 2 (fine-tuned LLM) using a small set of meaningful metrics.
- **Which agent(s) use the fine-tuned model is TO BE DECIDED**, based on dataset availability, hardware, training feasibility, time, student skill level, experimental design, and educational value. No agent is assumed to be fine-tuned by default.

### Multi-Agent Scope

Four logical responsibilities: Detection, Intelligence, Behavioral Analysis, Verification. These are logical responsibilities, not necessarily four independent models, databases, or services — the implementation should stay as simple as the team can justify educationally.

### Trust Scope

A conceptual, non-final trust model based on three understandable factors: historical accuracy, verification result, and agreement with trusted peers. No specific weights, thresholds, or update frequencies are fixed by this document — see `docs/architecture/TRUST_MODEL.md`. The trust score is not a guaranteed probability of correctness.

### Fine-Tuning Scope

Investigated only in Phase 2. Applies parameter-efficient fine-tuning to an open-source LLM using cybersecurity-related data, scoped to what is feasible on available hardware and student skill level. Target agent(s) not yet decided.

### Evaluation Scope

Compare Phase 1 vs. Phase 2 on a small number of meaningful, actually-measurable metrics (see `docs/RESEARCH.md`). No metrics or results are assumed in advance.

## Expected Deliverables

- Working Phase 1 prototype (base LLM, multi-agent, verification, trust).
- Working Phase 2 prototype (fine-tuned LLM, same architecture).
- Evaluation comparing the two phases.
- Complete project documentation (this set of files).
- A team capable of explaining and defending the system.

## Success Criteria

- Phase 1 runs end-to-end on at least one realistic security scenario.
- Phase 2 runs end-to-end using a fine-tuned model in place of (or alongside) the base LLM.
- The trust mechanism visibly affects at least one final decision in a demonstrable way.
- Evaluation results (whatever they turn out to be) are reported honestly.
- All three students can explain the full system.

## Included Features

- Multi-agent analysis (Detection, Intelligence, Behavioral Analysis, Verification).
- Verification of agent findings.
- Trust-aware weighting of agent outputs.
- Final recommendation with a human-review path.
- Phase 1 → Phase 2 fine-tuning comparison.

## Excluded Features

- Real automated response actions against live systems — **all actions are simulated only**.
- Enterprise infrastructure (microservices, distributed systems) unless a clear educational reason is documented and approved.
- Vector databases, RAG, or additional agents beyond the four listed, unless approved.
- Any offensive security capability.

## Safety Boundaries

This is an academic, defensive-only project. All experiments use authorized environments and synthetic or appropriately licensed data. No unauthorized attacks against real systems. **The system never executes real actions against live infrastructure — any response the system produces is a simulated action, presented for human review, not an automated real-world action.**

## Scope-Change Policy

Any new agent, major architecture change, new external service, or feature outside this document requires a team-approved decision recorded in `DECISIONS.md` before implementation. No AI coding agent may expand scope unilaterally.
