# Trust Model

Status: **CONCEPTUAL — weights, thresholds, and update frequency are TO BE DECIDED by the team.**

## Why Trust Is Needed

When multiple agents analyze the same event, they will sometimes disagree, and one or more may be wrong, incomplete, or misled. Treating every agent's output as equally reliable risks letting an incorrect finding drive the final decision just as much as a correct one. Trust gives the system a way to weigh findings by how reliable the source has actually been, rather than by how confident it sounds.

## What Trust Means In This Project

Trust is a **per-agent, evolving estimate of how much weight to give that agent's finding**, based on observable, checkable signals — not on the agent's own stated confidence. Trust is not a proof or guarantee of correctness; it is a heuristic for weighting.

## Conceptual Flow

Verification and trust are connected, but verification result is used **exactly once** — as one input into the trust score — not applied a second time anywhere else in the decision path:

```
Agent Findings
      ↓
Verification (verified consistent / verified inconsistent / inconclusive)
      ↓
Trust Evaluation
      ↓
Trust Score
      ↓
Trust-Weighted Final Recommendation
```

## The Three Factors

**1. Historical Accuracy** — how often this agent's past findings turned out to be correct, where correctness can be checked (e.g., against a labeled dataset, or against a later-confirmed outcome).

**2. Verification Result** — the single result Verification produced for this specific finding (verified consistent / verified inconsistent / inconclusive) — i.e., whether the evidence cited actually supports the conclusion.

**3. Agreement With Trusted Peers** — whether this agent's finding agrees with the findings of other agents that currently have high trust.

## Conceptual Formula

```
Trust_i = w1 × HistoricalAccuracy_i + w2 × Verification_i + w3 × PeerAgreement_i
```

This is a **conceptual model only**. The values of `w1`, `w2`, `w3`, the scale of each factor, update frequency, and any thresholds (e.g., for quarantining a low-trust agent) are **not decided** and must not be treated as final until the team agrees on them and records the decision in `docs/DECISIONS.md`.

## How Trust May Affect Decisions

A higher-trust agent's finding should count for more in the Final Recommendation than a lower-trust agent's finding on the same event. The exact aggregation method (e.g., weighted average, weighted vote, threshold-based exclusion) is **TO BE DECIDED**.

## Agent Disagreement

When agents disagree, the system should not silently pick one side. The Final Recommendation should be able to reflect that disagreement occurred and how it was resolved (e.g., by trust weighting), so the outcome is explainable rather than opaque.

## Low-Trust Situations

If an agent's trust drops significantly, the system should reduce that agent's influence on the decision. Whether this means simple down-weighting, temporary exclusion ("quarantine"), or another mechanism is **TO BE DECIDED**. Any such mechanism must be simple enough for the team to implement, test, and explain.

## Limitations

- With a small number of agents and a limited number of demo events, historical accuracy will be based on a small sample and should not be presented as statistically rigorous.
- Verification's own correctness is not guaranteed; if Verification is wrong, trust updates driven by it will be wrong too. This is a known, documented limitation, not something this project claims to solve.
- Trust scores are a decision-support heuristic, not a certified measure of an agent's true reliability.
