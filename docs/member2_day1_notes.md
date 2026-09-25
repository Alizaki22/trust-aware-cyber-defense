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
