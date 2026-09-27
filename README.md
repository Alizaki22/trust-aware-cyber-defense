# Fine-Tuned Multi-Agent AI for Cyber Defense

A university semester project, developed by a team of three students, building a multi-agent AI system for cybersecurity analysis. Specialized agents examine a security event, compare and verify each other's findings, and produce a final recommendation weighted by a simple, understandable trust mechanism.

This is an academic learning project — not an enterprise cybersecurity platform.

## Problem

AI agents can assist with cybersecurity analysis, but their outputs may be incorrect, incomplete, conflicting, or misleading. Trusting every agent output equally risks poor decisions when one or more agents are wrong.

## Proposed Solution

Specialized agents (Detection, Intelligence, Behavioral Analysis) analyze a security event. A Verification Agent checks their findings against the evidence cited. A trust mechanism weighs each agent's influence on the final decision based on historical accuracy, verification results, and agreement with trusted peers. The final recommendation can route to a simulated action, further verification, or human review.

## Two Development Phases

- **Phase 1 — Baseline:** built using a normal/base LLM. Establishes the multi-agent structure, verification, and trust mechanism.
- **Phase 2 — Fine-Tuned System:** extends Phase 1 by introducing a fine-tuned open-source LLM (parameter-efficient fine-tuning, e.g. LoRA/QLoRA) and compares results against the Phase 1 baseline. The fine-tuned model is used by the **Detection agent only** (team decision; see `docs/PHASE1_IMPLEMENTATION.md`).

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
src/                     Phase 1 implementation (python -m src.cli ...)
  models/                Pydantic schemas (SecurityEvent, AgentFinding, FinalRecommendation, ...)
  agents/                detection (LLM), intelligence, behavioral, verification (rules), prompts
  trust/                 trust formula + calibration-based historical accuracy
  recommendation/        trust-weighted vs equal-weighted vote, routing
  coordinator/           pipeline orchestration
  data/unsw_nb15.py      UNSW-NB15 preparation, leakage checks, frozen subsets
  evaluation/            the four metrics + calibration/evaluation runs
  utils/llm_client.py    OpenAI-compatible client (Qwen3-4B-Instruct-2507) + offline stub
  api.py, pipeline.py, config.py, cli.py
frontend/                Streamlit app (app.py) + display helpers
tests/                   pytest suite (74 tests)
data/
  threat_intel/, baselines/, events/   small SYNTHETIC reference data (committed)
  eval/                  frozen evaluation/calibration subset ids (committed)
  raw/, splits/, processed/            official CSVs and generated files (gitignored)
docs/                    project documentation (PHASE1_IMPLEMENTATION.md = how Phase 1 works)
  architecture/, frontend/
runs/                    calibration and evaluation outputs (gitignored)
.github/  AGENTS.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md  README.md
requirements.txt  pyproject.toml
```

## Documentation

- [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) — problem, goals, phases, scope
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — conceptual system design and components
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md) — implementation-level architecture, tech stack, project structure
- [`docs/architecture/AGENT_SPECIFICATION.md`](docs/architecture/AGENT_SPECIFICATION.md) — per-agent role detail
- [`docs/AGENT_DESIGN.md`](docs/AGENT_DESIGN.md) — agent implementation design (base class, prompting, error handling)
- [`docs/architecture/TRUST_MODEL.md`](docs/architecture/TRUST_MODEL.md) — trust mechanism
- [`docs/architecture/DATA_FLOW.md`](docs/architecture/DATA_FLOW.md) — data flow through the system
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) — internal API/data model reference
- [`docs/DATASET.md`](docs/DATASET.md) — dataset candidates and licensing requirements
- [`docs/LLM_FINE_TUNING.md`](docs/LLM_FINE_TUNING.md) — Phase 2 fine-tuning approach
- [`docs/DEVELOPMENT_GUIDE.md`](docs/DEVELOPMENT_GUIDE.md) — local setup and development workflow
- [`docs/TESTING.md`](docs/TESTING.md) — testing strategy
- [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) — evaluation experiments and results tracking
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decision log
- [`docs/RESEARCH.md`](docs/RESEARCH.md) — research foundation
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — threats and mitigations
- [`AGENTS.md`](AGENTS.md) — instructions for AI coding agents working in this repo
- [`docs/PHASE1_IMPLEMENTATION.md`](docs/PHASE1_IMPLEMENTATION.md) — how the implemented Phase 1 baseline works (schemas, data, trust, metrics, commands)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and Git workflow guide
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — community standards
- [`SECURITY.md`](SECURITY.md) — security policy and reporting

## Project Status

🧪 **Phase 1 baseline implemented** (UNSW-NB15 · Qwen3-4B-Instruct-2507 · four agents · trust/verification · evaluation · Streamlit frontend). The pipeline and all four metrics are tested end to end; **real Qwen3-4B-Instruct-2507 baseline results have not been produced yet** (see `docs/PHASE1_IMPLEMENTATION.md` §14). Phase 2 (Detection fine-tuning) is not started. The project license (D-012) is still open.

### Quick start

```bash
pip install -r requirements.txt
# put UNSW_NB15_training-set.csv and UNSW_NB15_testing-set.csv in data/raw/unsw_nb15/
python -m src.cli prepare-data && python -m src.cli validate-data
vllm serve Qwen/Qwen3-4B-Instruct-2507          # or see PHASE1_IMPLEMENTATION.md §6 for Ollama
python -m src.cli calibrate && python -m src.cli evaluate
streamlit run frontend/app.py
pytest
```

Without a model server, add `--backend stub` (CLI) or set `LLM_BACKEND=stub` (Streamlit) to run the pipeline with a clearly labelled stub Detection model. Full details: [`docs/PHASE1_IMPLEMENTATION.md`](docs/PHASE1_IMPLEMENTATION.md).

## Team

Three students. See `docs/DECISIONS.md` (D-008) for the agreed task distribution.
