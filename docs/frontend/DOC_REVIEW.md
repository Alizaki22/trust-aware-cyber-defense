# Frontend Documentation Review

Owner: Member 3 (Frontend & Product) · Day 1, Phase 1 of 3 · Status: **PROPOSED — for team review**

Reviewed against `development` @ `3e17d55`.

## 1. Purpose

This review reads every project document from the frontend's point of view. It records:

- what each document requires of the UI, as traceable requirements (§3)
- the gaps and inconsistencies that block or affect frontend work (§4)
- what M3 needs from M1 and M2, and when (§5)

It does not change any decision. Items that need a decision are listed as questions for the team.

## 2. Documents Reviewed

| Document | Relevance to frontend |
|---|---|
| `README.md`, `docs/PROJECT_SCOPE.md` | Success criteria the demo must show; academic, non-enterprise framing |
| `docs/ARCHITECTURE.md` | Pipeline stages to visualise; output layer "dashboard/report — TBD" |
| `docs/SYSTEM_ARCHITECTURE.md` | Runtime flow (synchronous), config values the UI may display, project structure |
| `docs/DECISIONS.md` | D-006 simplicity, D-007 stack (no frontend tech), D-008 M3 scope, D-011 simulated actions |
| `docs/architecture/AGENT_SPECIFICATION.md` | Per-agent output meaning and failure/uncertainty behaviour → card states |
| `docs/architecture/TRUST_MODEL.md` | Three trust factors to display; trust ≠ probability; surface disagreement |
| `docs/architecture/DATA_FLOW.md` | Stage order for the pipeline view; example scenario |
| `docs/AGENT_DESIGN.md` | Error handling → `confidence: "none"`; agents run in parallel via Coordinator |
| `docs/API_REFERENCE.md` | Current data contract (`SecurityEvent`, `FinalRecommendation`); optional REST endpoints |
| `docs/THREAT_MODEL.md` | Human over-reliance and prompt-injection threats → UI requirements |
| `SECURITY.md` | Untrusted input, no secrets in code, label synthetic data |
| `docs/DATASET.md` | Event input format; synthetic-data labelling |
| `docs/EXPERIMENTS.md`, `docs/RESEARCH.md` | Experiments 2–4 need UI views; metrics TBD; honest small-sample reporting |
| `docs/TESTING.md` | Scenario list reusable as demo scenarios; mock LLM approach |
| `docs/LLM_FINE_TUNING.md` | Phase 2 model identity needed for phase comparison |
| `docs/DEVELOPMENT_GUIDE.md`, `CONTRIBUTING.md`, `AGENTS.md` | Branch/PR workflow; no unapproved dependencies |

## 3. Derived Frontend Requirements

Each requirement cites its source. **Must** means the requirement comes from a decided item or a success criterion. **Should** means it comes from guidance or a proposed item.

### Safety and honesty

| ID | Requirement | Level | Source |
|---|---|---|---|
| R-01 | Every action is presented as simulated ("would …"), with a persistent SIMULATED label. The UI has no control that implies real execution. | Must | D-011, PROJECT_SCOPE, THREAT_MODEL (trust boundary) |
| R-02 | An Intelligence "no match" is displayed as neutral / "no known indicator", never as benign or safe. | Must | AGENT_SPECIFICATION (Intelligence) |
| R-03 | A missing behavioural baseline is displayed as "no baseline available", not as normal or anomalous. | Must | AGENT_SPECIFICATION (Behavioral) |
| R-04 | Trust scores are shown as a weighting heuristic, never as "% correct" or a probability. | Must | TRUST_MODEL, THREAT_MODEL (human over-reliance) |
| R-05 | Agent disagreement is shown explicitly on the result, never hidden. | Must | ARCHITECTURE, TRUST_MODEL |
| R-06 | Uncertain results are shown as uncertain. The UI must not restyle a low-confidence or human-review result as a confident one. | Must | ARCHITECTURE (error/uncertainty) |
| R-07 | Synthetic data and mock results are visibly labelled. | Must | SECURITY.md, DATASET.md |
| R-08 | Raw event content is rendered as plain text, never as HTML/Markdown. Event content (e.g. phishing email bodies) is untrusted and could otherwise inject script into the UI. | Must | SECURITY.md (input untrusted), THREAT_MODEL (prompt injection) |
| R-09 | No API keys or secrets in frontend code or config committed to the repo. | Must | SECURITY.md |
| R-10 | Evaluation views show sample size and a "small test set — indicative only" note. They never show invented numbers when data is missing. | Must | RESEARCH, EXPERIMENTS, AGENTS.md |

### Explainability (what the demo must show)

| ID | Requirement | Level | Source |
|---|---|---|---|
| R-11 | Show the pipeline stages in order: input → 3 agents (parallel) → verification → trust → recommendation → routing. | Must | ARCHITECTURE, DATA_FLOW |
| R-12 | For each agent: classification, cited evidence, confidence, reasoning. | Must | AGENT_SPECIFICATION, API_REFERENCE |
| R-13 | For each agent: its verification status (consistent / inconsistent / inconclusive) and the stated reason. | Must | AGENT_SPECIFICATION (Verification) |
| R-14 | For each agent: its trust score and the three factors (historical accuracy, verification, peer agreement). | Must | TRUST_MODEL |
| R-15 | Show the final classification, confidence, routing and reasoning. | Must | API_REFERENCE (`FinalRecommendation`) |
| R-16 | Show trust-weighted vs equal-weighted outcomes side by side, and highlight when trust changed the result. | Must | PROJECT_SCOPE success criterion; EXPERIMENTS Exp. 2 |
| R-17 | Show which phase/model produced a result, and compare Phase 1 vs Phase 2 on the metrics M2 reports. | Must | PROJECT_SCOPE; EXPERIMENTS Exp. 4 |
| R-18 | Show a failed agent distinctly from an unsure agent, and let the result still render with the remaining agents. | Should | AGENT_DESIGN, API_REFERENCE (error responses), TESTING (agent failure) |
| R-19 | Show the trust weights and threshold actually used for a run, since they are TBD and may change. | Should | TRUST_MODEL, SYSTEM_ARCHITECTURE (config) |

### Input and operation

| ID | Requirement | Level | Source |
|---|---|---|---|
| R-20 | Accept a `SecurityEvent` (pick a sample, paste JSON, or upload a file) and validate required fields before running. | Must | API_REFERENCE, DATASET.md |
| R-21 | Provide prepared demo scenarios covering: clear attack, ambiguous event, deliberately wrong agent, missing data, agent failure, trust demonstration. | Should | TESTING (scenario table), EXPERIMENTS 1–3 |
| R-22 | Show clear loading and error states. LLM/API failures are reported, not swallowed. The pipeline is synchronous, so the loading state is indeterminate for MVP. | Should | SYSTEM_ARCHITECTURE (runtime flow, error handling) |
| R-23 | Work from mock data before the backend exists, and keep that mode as a demo fallback. | Should | 10-day plan (Days 2–4 need schema only) |
| R-24 | Readable on a projector: colour is never the only signal (icon + text too). | Should | Demo context (D-008 M3 scope) |

## 4. Gaps and Inconsistencies Found

Severity scale: **Blocker** = M3 can't proceed past a given day without it; **High** = rework risk if not fixed before Day 3; **Medium** = affects a specific view; **Low** = tidy-up.

| # | Finding | Where | Severity | Suggested owner |
|---|---|---|---|---|
| G-01 | No frontend technology decided. D-007 lists no UI stack, and the output layer is "TBD". This blocks the Day 2 scaffold. | DECISIONS D-007, ARCHITECTURE | **Blocker (Day 2)** | Team → new D-013 |
| G-02 | Integration interface undecided: FastAPI is "only if required", but the 10-day plan (Day 5) assumes an "API or agreed interface". The choice depends on G-01. | D-007, API_REFERENCE | **Blocker (Day 5)** | M1 |
| G-03 | `FinalRecommendation` doesn't return `VerificationResult`s, so R-13 can't be met. | API_REFERENCE | **High** | M1 |
| G-04 | No equal-weighted outcome in the output, so R-16 (the headline success criterion) can't be shown. | API_REFERENCE, EXPERIMENTS Exp. 2 | **High** | M1 |
| G-05 | No run/phase/model identity in the output, so R-17 can't be met. | API_REFERENCE | **High** | M1 |
| G-06 | `confidence` is a string ("high/medium/low/none") but `confidence_threshold` is a float (0.6). There is no defined mapping, so routing can't be computed or explained. | API_REFERENCE (`SystemConfig`) | **High** | M1 |
| G-07 | Agents produce different kinds of answers (a classification, an IOC match, an anomaly). There is no shared verdict scale to combine them, compute peer agreement, or show them comparably. | AGENT_SPECIFICATION, TRUST_MODEL | **High** | M1 + M2 |
| G-08 | `agent_findings` and `trust_scores` are untyped `list`; `agent`, `routing` and `status` are free strings. The frontend can't rely on fixed values. | API_REFERENCE | **High** | M1 |
| G-09 | No field distinguishes "agent failed" from "agent unsure" (both become `confidence: "none"`), so R-18 can't be met. | AGENT_DESIGN, API_REFERENCE | Medium | M1 |
| G-10 | Two definitions of `AgentFinding`: AGENT_DESIGN's has no `event_id` and takes `event: dict`, while API_REFERENCE's has `event_id` and takes `SecurityEvent`. | AGENT_DESIGN vs API_REFERENCE | Medium | M1 |
| G-11 | Do agents see each other's findings? AGENT_SPECIFICATION says they are visible to peers; AGENT_DESIGN and DATA_FLOW say agents run independently. This affects how the pipeline view is drawn. | AGENT_SPECIFICATION vs AGENT_DESIGN/DATA_FLOW | Medium | M1 |
| G-12 | Is Verification LLM-based or rule-based? ARCHITECTURE says plain code, THREAT_MODEL assumes an LLM, and AGENT_DESIGN lists it as open. This affects what the "verification reason" text looks like. | ARCHITECTURE vs THREAT_MODEL vs AGENT_DESIGN | Low | M1 |
| G-13 | Aggregation method, tie handling and routing rules are all TBD. The UI can display them but can't define them. | TRUST_MODEL, ARCHITECTURE | Medium | M1 + M2 |
| G-14 | Trust history persistence across runs isn't specified. It is needed for any "trust over time" view. | TRUST_MODEL, SYSTEM_ARCHITECTURE | Low (stretch) | M1 |
| G-15 | "Reports" is in M3's scope in D-008 but absent from M3's tasks in the 10-day plan. Is this the final project report, or M2's evaluation report? | D-008 vs 10-day plan | Medium | Team |
| G-16 | SYSTEM_ARCHITECTURE's tree lists `docs/TRUST_MODEL.md`, which doesn't exist; the file is at `docs/architecture/TRUST_MODEL.md`. | SYSTEM_ARCHITECTURE | Low | M1 |
| G-17 | DEVELOPMENT_GUIDE has a placeholder `<org>` clone URL, references `requirements-dev.txt` (not in the structure), and hardcodes `gpt-3.5-turbo` although the model is TBD. | DEVELOPMENT_GUIDE | Low | M1 |
| G-18 | The official title ("Fine-Tuned Multi-Agent AI for Cyber Defense") differs from the repo name ("trust-aware-cyber-defense"). The demo, slides and UI header need one name. | README, D-000 | Low | Team |

## 5. M3 Dependencies (from the 10-day plan)

| Day | M3 needs | From | Covered by |
|---|---|---|---|
| 1–2 | Agent roles, output fields, UI stack decision | M1 / team | G-01, §3 |
| 3 | Agreed output schema | M1 | G-03 – G-10 |
| 4 | Sample structured outputs | M1 | Mock fixtures (Phase 3) until real ones exist |
| 5 | API or integration interface, plus real baseline outputs | M1, M2 | G-02 |
| 6 | Trust/verification output schema | M1 | G-03, G-04, G-06 |
| 8–9 | Phase 1 vs Phase 2 evaluation results | M2 | G-05, R-17 |

## 6. Next Steps

- **Phase 2 (M3):** define pages, user flow and result states against R-01 – R-24 → `FRONTEND_SPEC.md`.
- **Phase 3 (M3):** turn G-01 – G-09 into a concrete schema proposal and a draft D-013, and add mock fixtures → `SCHEMA_PROPOSAL.md`, `fixtures/`.
- **Team:** decide G-01 before Day 2 starts.
