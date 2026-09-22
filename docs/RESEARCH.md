# Research

## Research Problem

Multi-agent AI systems used for cybersecurity analysis can produce unreliable results when individual agent outputs are incorrect, conflicting, or misleading, and are trusted equally regardless of actual reliability.

## Research Questions

1. Can a simple, trust-aware weighting mechanism improve the reliability of a multi-agent cybersecurity analysis system compared to treating all agent outputs equally?
2. What, if anything, changes in agent output quality and system reliability when a base LLM is replaced with a fine-tuned, cybersecurity-oriented LLM?
3. Can a small set of understandable, checkable signals (historical accuracy, verification result, peer agreement) meaningfully distinguish reliable from unreliable agent outputs in this context?

## Objectives

- Build a working Phase 1 (base LLM) multi-agent baseline.
- Build a working Phase 2 (fine-tuned LLM) extension of the same system.
- Compare the two phases on a small number of measurable dimensions.
- Document what was actually learned, including negative or inconclusive results.

## Background

**Multi-agent AI:** [RESEARCH NEEDED] — the team should review foundational and recent material on multi-agent LLM systems and agent orchestration before implementation.

**Cybersecurity AI:** [RESEARCH NEEDED] — background on ML/LLM-based intrusion detection, phishing detection, and log analysis should be reviewed.

**LLMs and fine-tuning:** [RESEARCH NEEDED] — background on parameter-efficient fine-tuning (LoRA/QLoRA) should be reviewed before Phase 2 begins.

**Trust-aware AI / verification / uncertainty:** [RESEARCH NEEDED] — the team should review existing approaches to trust modeling in multi-agent systems and to LLM output verification/uncertainty estimation.

## Related Work

[RESEARCH NEEDED] — no specific papers, tools, or prior systems are cited here. The team must conduct and document this review before or during implementation; do not fabricate citations.

## Literature

| Source | Key Finding | Relevance |
|---|---|---|
| [RESEARCH NEEDED] | [RESEARCH NEEDED] | [RESEARCH NEEDED] |

## Dataset Considerations

No dataset has been finalized. Candidates to evaluate (not commitments): public network-intrusion datasets, publicly available phishing/email datasets, and locally constructed synthetic IOC and behavioral-baseline data for the Intelligence and Behavioral Analysis agents. Any dataset used must be appropriately licensed for academic use, and any synthetic data must be clearly labeled as synthetic in the final report.

## Phase 1 Methodology

Build the four logical agents using a base/normal LLM with role-specific prompting. Implement verification and trust as plain code. Test on a small, chosen scenario set. Record baseline behavior and any issues encountered.

## Phase 2 Methodology

Fine-tune an open-source LLM (approach: LoRA/QLoRA, to be investigated) on cybersecurity-related data. **Which agent(s) receive the fine-tuned model is not yet decided** (see `docs/DECISIONS.md`, D-010) — the choice depends on dataset availability, hardware, training feasibility, time, student skill level, experimental design, and educational value. Integrate the fine-tuned model into the same architecture used in Phase 1, changing only the model, not the surrounding system.

## Evaluation Methodology

Compare Phase 1 and Phase 2 using a small number of concrete, measurable dimensions selected by the team (e.g., accuracy on a labeled test set, handling of a deliberately conflicting/misleading test case, whether trust-weighting changed the final outcome). Exact metrics are **TO BE DECIDED** — this document intentionally does not pre-select final metrics or claim expected results.

## Limitations

- Small team, limited time, and limited compute constrain both the fine-tuning scope and the size/rigor of any evaluation.
- Any accuracy or reliability figures produced will be based on a small, non-industrial-scale test set and should be reported as such.

## Research Gaps

- No literature review has been conducted yet at the time of writing this document — see [RESEARCH NEEDED] markers above.
- No dataset has been selected.
- No baseline experiments have been run.
- Which agent(s) will be fine-tuned in Phase 2 is unresolved.

## References

None yet. To be added as research progresses. Do not add placeholder or invented references.
