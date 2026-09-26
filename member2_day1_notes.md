# Member 2 - Day 1 Notes

## Overview
- Project: Trust-Aware Cyber Defense
- Date: 2026-09-25
- Focus: Initial project review, documentation review, and planning tasks.

## Goals for Day 1
- Review repository structure and project scope.
- Understand the architecture and core design decisions.
- Identify the key deliverables and expected workflow.
- Capture notes for future implementation tasks.

## Key Observations
- The repository is a student learning project focused on defensive cybersecurity and trust-aware decision-making.
- Documentation appears to be the source of truth for architecture, scope, and decisions.
- The project includes a mix of architecture docs, research notes, dataset references, and experimental planning.

## Relevant Files Reviewed
- AGENTS.md
- README.md
- docs/PROJECT_SCOPE.md
- docs/ARCHITECTURE.md
- docs/DECISIONS.md
- docs/RESEARCH.md
- docs/THREAT_MODEL.md
- docs/EXPERIMENTS.md

## Notes
- Follow the documented scope and avoid expanding beyond the approved architecture.
- Keep implementation simple and educational rather than production-focused.
- Defensive-only, simulated environment; no live infrastructure actions.
- Tests should be added for important functionality and verified before completion.

## Open Questions
- Which specific module or feature should Member 2 focus on first?
- Are there any immediate implementation tasks or bug fixes assigned for the first sprint?
- Is there a preferred workflow for documenting experiments or deliverables?

## Next Steps
- Confirm task assignment and milestone expectations.
- Review the most relevant implementation area in the codebase.
- Document findings and begin the assigned work.

# Member 2 - Day 1 AI/ML Planning

## 1. Role

Member 2 - AI/ML & Model Development

Responsibilities:
- Dataset preparation
- Model development
- Fine-tuning
- Training
- Experimentation
- Model evaluation/testing

## 2. Project Agents

1. Detection Agent
2. Intelligence Agent
3. Behavioral Analysis Agent
4. Verification Agent

## 3. Dataset Requirements

Detection:
- Labeled security events

Intelligence:
- IOC lookup data

Behavioral Analysis:
- Historical behavioral baselines

Verification:
- Agent findings paired with original events

Fine-tuning:
- Instruction-formatted cybersecurity examples

Evaluation:
- Labeled test scenarios

## 4. Dataset Candidates

Primary Detection dataset:
- CIC-IDS2017
- UNSW-NB15

Current status:
TO BE DECIDED

## 5. Fine-Tuning

Method:
- PEFT
- LoRA / QLoRA

Training data:
- Instruction-tuning format

Target size:
- Minimum: 500-1,000 high-quality examples
- Recommended: 2,000-5,000 examples

## 6. Dataset Split

Training: 80%
Validation: 10%
Test: 10%

## 7. Model

Base model:
TO BE DECIDED

Fine-tuned agent:
TO BE DECIDED

## 8. Experiments

Experiment 1:
End-to-end functionality

Experiment 2:
Trust weighting demonstration

Experiment 3:
Agent disagreement handling

Experiment 4:
Phase 1 vs Phase 2

Experiment 5:
Verification effectiveness

## 9. Current Blockers / Decisions Needed

1. Primary Detection dataset
2. Base LLM
3. Which agent(s) receive fine-tuning
4. Final evaluation metrics
