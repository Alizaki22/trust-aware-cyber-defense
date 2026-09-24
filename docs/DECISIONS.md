# Decisions

## Purpose

This document records important decisions agreed upon by the team, and clearly marks decisions that are still pending team approval. No entry in this log represents a fabricated or assumed team agreement — anything not yet actually decided is marked **PROPOSED — REQUIRES TEAM APPROVAL** or **TO BE DECIDED**.

## Decision Log

| ID | Decision | Status |
|---|---|---|
| D-000 | Final project title | DECIDED BY TEAM AND AGREED BY MENTOR |
| D-001 | Two-phase development (Phase 1 baseline, Phase 2 fine-tuned) | DECIDED |
| D-002 | Four logical agent roles (Detection, Intelligence, Behavioral Analysis, Verification) | DECIDED |
| D-003 | Conceptual trust model (historical accuracy, verification, peer agreement) | DECIDED BY THE TEAM |
| D-004 | Fine-tuning scoped to Phase 2 only | DECIDED BY THE TEAM |
| D-005 | Phase 1 as literal baseline for Phase 2 comparison | DECIDED BY THE TEAM |
| D-006 | Student-friendly/simple architecture over enterprise infrastructure | DECIDED BY THE TEAM |
| D-007 | Technology stack (language, framework, base LLM, etc.) | DECIDED BY THE TEAM |
| D-008 | Three-student task distribution | DECIDED BY THE TEAM AND APPROVED BY THE MENTOR |
| D-009 | Git branching model (main / development / feature branches) | DECIDED BY THE TEAM |
| D-010 | Phase 2 fine-tuned-model agent assignment | TO BE DECIDED |
| D-011 | All system actions are simulated, never real | DECIDED BY THE TEAM |
| D-012 | Project license | NOT YET DECIDED |

---

### D-000 — Final Project Title

**Decision:** The official project title is **Fine-Tuned Multi-Agent AI for Cyber Defense**.

**Status:** DECIDED

---

### D-001 — Two-Phase Development

**Decision:** Build the project in two connected phases: Phase 1 (base/normal LLM) as a working baseline, and Phase 2 (fine-tuned LLM) as an extension of the same architecture.

**Context:** Allows the team to learn general multi-agent/LLM integration first, then isolate what changes when fine-tuning is introduced.

**Alternatives Considered:** Building the fine-tuned system directly without a baseline; building fine-tuning and multi-agent structure simultaneously.

**Consequences:** Phase 2 work depends on Phase 1 being functional first; the team cannot skip ahead to fine-tuning without a working baseline.

**Status:** DECIDED

---

### D-002 — Four Logical Agent Roles

**Decision:** Detection, Intelligence, Behavioral Analysis, and Verification, as logical responsibilities (not necessarily four separate models/services).

**Alternatives Considered:** More agents (e.g., separate Vulnerability/Incident agents); a single combined analysis agent.

**Consequences:** Keeps the system small enough for three students; may need revisiting if a role proves too broad to implement simply.

**Status:** DECIDED

---

### D-003 — Conceptual Trust Model

**Decision:** Trust based on historical accuracy, verification result, and peer agreement; no fixed weights/thresholds yet. Verification result feeds into the trust score once, not applied separately elsewhere.

**Alternatives Considered:** Self-reported agent confidence as trust (rejected — not independently checkable); a more complex adaptive trust algorithm (rejected for Phase 1 as unnecessarily complex).

**Consequences:** Trust values will need real tuning once the team has actual data to test against.

**Status:** DECIDED BY THE TEAM

---

### D-004 — Fine-Tuning Scoped to Phase 2

**Decision:** No fine-tuning occurs in Phase 1; it is introduced only in Phase 2.

**Alternatives Considered:** Fine-tuning from the start (rejected — would prevent a clean baseline comparison).

**Consequences:** Phase 1 must be fully functional using only prompting, since there is no fine-tuned model yet.

**Status:** DECIDED

---

### D-005 — Phase 1 as Literal Baseline

**Decision:** Phase 2 must reuse Phase 1's multi-agent structure, verification, and trust mechanism rather than being rebuilt separately, so that the only substantive change is the LLM used.

**Consequences:** Any architecture change made in Phase 2 must also be considered for backporting to Phase 1, to keep the comparison fair.

**Status:** DECIDED BY THE TEAM

---

### D-006 — Student-Friendly, Simple Architecture

**Decision:** Prefer simple Python modules, simple APIs, and small numbers of agents over distributed/enterprise infrastructure, unless a specific educational reason is documented.

**Status:** DECIDED BY THE TEAM

---

### D-007 — Technology Stack

**Decision:** The team will use the following initial technology stack:

- Python 3.11
- Pydantic
- pytest
- OpenAI SDK for initial LLM integration
- FastAPI, only if an API layer is required
- Hugging Face Transformers
- PEFT
- LoRA/QLoRA for Phase 2 fine-tuning
- JSON/JSONL for initial data storage

**Architecture approach:**
- Plain Python modules for the multi-agent system.
- No agent framework initially.
- No database initially.
- No RAG/vector database initially.
- Additional technologies require team approval.

**Reason:** This stack is lightweight, Python-based, suitable for LLM/fine-tuning work, and realistic for three students working under a 10-day development schedule.

**Action item (not a decision change):** Using the OpenAI SDK for Phase 1 requires a funded API key with real per-call cost. The team should confirm who provides/pays for this key (or decide to point the same client at a free/local OpenAI-compatible endpoint instead) before Phase 1 implementation begins — this blocks the very first agent-integration task.

**Status:** DECIDED

---

### D-008 — Three-Student Task Distribution

**Decision:** The project responsibilities are divided into three primary workstreams:

| Team Member | Primary Responsibilities |
|---|---|
| **Student 1 — Team Lead / Architecture & Repository** | Project documentation (`.md` files), system architecture, Git/GitHub repository management, project coordination, dataset coordination, and integration oversight |
| **Student 2 — AI/ML & Model Development** | Dataset preparation, model development, fine-tuning, training, experimentation, and model evaluation/testing |
| **Student 3 — Frontend & Product** | Frontend development, UI/UX, results visualization, system testing support, reports, and presentation/demo preparation |

This division creates three complementary workstreams:

1. **Project, Architecture & Repository**
   - Project documentation
   - System architecture
   - Dataset coordination
   - Git/GitHub repository management
   - Team coordination and integration

2. **AI/ML & Model Development**
   - Dataset preparation
   - Model development
   - Fine-tuning
   - Training and experimentation
   - Model evaluation and testing

3. **Frontend & Product**
   - Frontend development
   - UI/UX
   - Results visualization
   - Testing support
   - Reports and presentation/demo preparation

The responsibilities may be adjusted when necessary based on project requirements, workload, or technical dependencies. Any significant change to the agreed task distribution should be communicated to the team and recorded when appropriate.

**Status:** DECIDED BY THE TEAM AND APPROVED BY THE MENTOR

---

### D-009 — Git Branching Model

**Decision:** `main` = stable branch, `development` = integration branch, feature/docs/research/fix/experiment branches feed into `development` via PR, then `development` feeds `main` via PR. No direct pushes or merges to `main`.

**Status:** DECIDED BY THE TEAM

---

### D-010 — Phase 2 Fine-Tuned-Model Agent Assignment

**Decision:** Not yet made. Phase 2 will integrate a fine-tuned open-source LLM into the existing Phase 1 architecture, but which agent(s) (Detection, Intelligence, Behavioral Analysis, and/or Verification) will actually use the fine-tuned model has not been decided.

**Context:** The final choice depends on dataset availability, hardware, training feasibility, time, student skill level, experimental design, and educational value. No document should assume a specific agent is fine-tuned by default.

**Status:** TO BE DECIDED

---

### D-011 — All System Actions Are Simulated

**Decision:** The system never executes real cybersecurity actions against live infrastructure. Every action the system produces is a simulated action, presented alongside further-verification and human-review routing options.

**Context:** This is a defensive, academic project; real automated response capability is out of scope and a safety/liability risk for a student project.

**Status:** DECIDED

---

### D-012 — Project License

**Decision:** Not yet made. No license has been chosen or added to the repository, though it is public.

**Status:** NOT YET DECIDED
