# Experiments

This document describes the experimental design for evaluating the project. It tracks planned experiments, their methodology, and results (to be filled in as experiments are conducted).

## Experiment Goals

1. **Demonstrate that the system works end-to-end** — agents analyze events, verification checks findings, trust weighs the decision, and a recommendation is produced.
2. **Demonstrate that trust weighting has a visible effect** — at least one scenario where trust changes the outcome compared to equal weighting.
3. **Compare Phase 1 (base LLM) vs. Phase 2 (fine-tuned LLM)** — on a defined set of measurable dimensions.
4. **Report results honestly** — including negative, inconclusive, or unexpected findings.

## Experimental Design

### Independent Variables

| Variable | Phase 1 | Phase 2 |
|---|---|---|
| LLM model | Base/normal LLM | Fine-tuned LLM (LoRA/QLoRA) |

Everything else (agent architecture, verification logic, trust model, test scenarios, prompts) remains constant between phases to isolate the effect of fine-tuning.

### Dependent Variables (Metrics)

Exact metrics are **TO BE DECIDED** by the team. Candidate metrics include:

| Metric | What It Measures | How to Measure |
|---|---|---|
| Classification accuracy | Correct event classification rate | Compare agent output against labeled test data |
| Evidence quality | Whether cited evidence actually supports the conclusion | Verification pass/fail rate |
| Hallucination rate | How often agents cite evidence not in the input | Manual review + verification checks |
| Trust differentiation | Whether trust scores meaningfully distinguish reliable from unreliable findings | Compare trust scores of correct vs. incorrect findings |
| Trust impact | Whether trust weighting changes the final recommendation | Compare trust-weighted vs. equal-weighted recommendations |
| Agent agreement | How often agents agree on classification | Cross-agent comparison |
| Confidence calibration | Whether stated confidence correlates with actual accuracy | Plot confidence vs. accuracy |

The team should select a small number of these (3–5) that are actually measurable with available data and time.

### Control Conditions

- **Equal weighting (no trust):** Run the same scenarios with all agents weighted equally to establish a baseline.
- **Phase 1 baseline:** Phase 1 results serve as the baseline for Phase 2 comparison.

## Planned Experiments

### Experiment 1: End-to-End Functionality

**Objective:** Verify the system works end-to-end on at least one realistic scenario.

**Method:**
1. Prepare a labeled security event (e.g., a clear DDoS attack from CIC-IDS2017).
2. Run through the full pipeline: Coordinator → Agents → Verification → Trust → Recommendation.
3. Verify each component produced valid output.
4. Check that the final recommendation is reasonable given the input.

**Expected outcome:** A valid `FinalRecommendation` with populated findings, trust scores, and routing.

**Status:** NOT YET RUN

---

### Experiment 2: Trust Weighting Demonstration

**Objective:** Show that trust weighting visibly affects the final decision.

**Method:**
1. Prepare a scenario where one agent produces a deliberately incorrect finding.
2. Run the pipeline with equal weighting — observe the recommendation.
3. Run the pipeline with trust weighting (where the incorrect agent has lower historical accuracy) — observe the recommendation.
4. Compare the two recommendations.

**Expected outcome:** Trust-weighted recommendation should be closer to the correct answer than the equal-weighted recommendation.

**Status:** NOT YET RUN

---

### Experiment 3: Agent Disagreement Handling

**Objective:** Verify the system handles conflicting agent findings appropriately.

**Method:**
1. Prepare a scenario where agents legitimately disagree (ambiguous event).
2. Run the pipeline.
3. Verify that disagreement is surfaced in the final recommendation.
4. Verify routing suggests human review.

**Expected outcome:** The recommendation should acknowledge disagreement and route to human review rather than forcing a confident answer.

**Status:** NOT YET RUN

---

### Experiment 4: Phase 1 vs. Phase 2 Comparison

**Objective:** Compare system performance with base LLM vs. fine-tuned LLM.

**Method:**
1. Select a test set of labeled security events (same set for both phases).
2. Run all events through Phase 1 configuration (base LLM).
3. Run all events through Phase 2 configuration (fine-tuned LLM).
4. Compare selected metrics (accuracy, evidence quality, hallucination rate, etc.).
5. Report differences honestly, including if Phase 2 performs worse on some dimensions.

**Expected outcome:** No outcome is assumed in advance. Results will be whatever they turn out to be.

**Status:** NOT YET RUN

---

### Experiment 5: Verification Effectiveness

**Objective:** Evaluate how well the Verification Agent catches incorrect or hallucinated findings.

**Method:**
1. Prepare a set of findings with known correct/incorrect evidence citations.
2. Run Verification on each finding.
3. Measure true positive rate (catching actual inconsistencies) and false positive rate (flagging correct findings).

**Expected outcome:** Verification should catch some, but not necessarily all, inconsistencies.

**Status:** NOT YET RUN

## Experiment Log Template

Use this template to record experiment runs:

```markdown
### Run: [Experiment Name] — [Date]

**Configuration:**
- Phase: [1 / 2]
- LLM model: [model name]
- Trust weights: [w1, w2, w3]
- Test set: [description]

**Results:**
- [Metric 1]: [value]
- [Metric 2]: [value]
- [Metric 3]: [value]

**Observations:**
- [What happened]
- [Anything unexpected]
- [Issues encountered]

**Conclusion:**
- [What was learned from this run]
```

## Results Reporting Guidelines

Per `docs/RESEARCH.md` and `AGENTS.md`:

- Report all results honestly, including negative or inconclusive findings.
- Do not fabricate results, metrics, or experimental outcomes.
- Clearly state the sample size and limitations of any evaluation.
- Distinguish between results that meet statistical significance thresholds and those that are merely indicative.
- Include raw data or detailed results in an appendix if needed.

## Experiment Results

Results will be added here as experiments are conducted. No results are assumed or fabricated in advance.

| Experiment | Status | Key Result |
|---|---|---|
| 1: End-to-End Functionality | NOT YET RUN | — |
| 2: Trust Weighting Demonstration | NOT YET RUN | — |
| 3: Agent Disagreement Handling | NOT YET RUN | — |
| 4: Phase 1 vs. Phase 2 Comparison | NOT YET RUN | — |
| 5: Verification Effectiveness | NOT YET RUN | — |

## Related Documentation

- `docs/RESEARCH.md` — Research questions and evaluation methodology
- `docs/TESTING.md` — Testing strategy and scenario-based tests
- `docs/DATASET.md` — Datasets used in experiments
- `docs/architecture/TRUST_MODEL.md` — Trust model being evaluated
- `docs/LLM_FINE_TUNING.md` — Fine-tuning approach being compared
