# Fine-Tuned Trust-Aware LLM Agents for Secure Multi-Agent Cyber Defense

A multi-agent cybersecurity defense system composed of specialized, fine-tuned LLMs. Each agent is fine-tuned (via a shared base model + role-specific LoRA/QLoRA adapters) for a distinct cybersecurity role — detection, threat intelligence, behavioral analysis, or verification. Agents collaborate through a LangGraph-based coordinator, but their outputs are not treated equally: a dynamic, system-calculated trust mechanism evaluates each agent's reliability using objectively checkable signals (historical accuracy, verification pass rate, agreement with trusted peers) and adjusts its influence on the final decision. The system can simulate a compromised or unreliable agent and demonstrate that the trust mechanism detects and reduces that agent's influence while still reaching a correct final decision.

## Status

🚧 Early stage — project scope, architecture, and research foundations are being defined in `docs/`. No code yet.

## Project Docs

- [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) — problem statement, goals, MVP/V2/Advanced scope
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system components, data flow, tech stack
- [`docs/RESEARCH.md`](docs/RESEARCH.md) — fine-tuning approach, datasets, related work
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — trust boundaries, threat actors, attack scenarios
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — running log of team decisions

## Core Idea

- **Fine-tuned agents**: one shared open-source base LLM, specialized into four cybersecurity experts via role-specific LoRA adapters (Detection, Intelligence, Behavioral, Verification).
- **Multi-agent orchestration**: agents collaborate via a LangGraph coordinator, each producing structured verdicts (classification + evidence + confidence).
- **Trust-aware decision-making**: a Trust Manager scores each agent based on verifiable outcomes (not self-reported confidence) and weights its influence on the final decision accordingly.
- **Adversarial demonstration**: an injected unreliable/compromised agent shows the trust score dropping and the agent being down-weighted or quarantined, while the system still reaches the correct final verdict.

## Team

3-person team. Work is split by interface boundary so members can build in parallel:

| Member | Owns | Contract exposed |
|---|---|---|
| Member 1 | `/finetuning`, `/models` | `run_inference(agent_role, input_text) -> dict` |
| Member 2 | `/agents`, `/orchestration` | `run_pipeline(event) -> dict` |
| Member 3 | `/data`, `/dashboard`, `/eval` | consumes Member 2's output |

Shared data contracts live in `/shared` and require review from all three members before merging.

## Roadmap

**Stage 1** — prove the core claim: fine-tuned LLM(s) + multi-agent collaboration, simple aggregation, no trust layer yet.

**Stage 2** — add Verification Agent, Trust Manager, weighted Decision Engine, adversarial-injection demo, dashboard, and evaluation layer (accuracy/precision/recall against ground truth).

See `docs/PROJECT_SCOPE.md` for the full MVP / V2 / Advanced breakdown.

## Getting Started

> To be added once the initial code scaffolding lands (Stage 1 setup).

## License

> To be decided by the team.
