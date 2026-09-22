# Agent Specification

Status: **PROPOSED — REQUIRES TEAM APPROVAL** for exact prompts/implementation; roles and responsibilities below reflect the current documented concept.

These are logical responsibilities. They do not require four independent models, databases, or services.

---

## Detection Agent

**Purpose:** Classify the security event (e.g., type of intrusion/alert, severity).

**Inputs:** Raw security event (log line, alert, or similar structured/semi-structured data).

**Outputs:** Classification label, severity, cited evidence from the input, confidence.

**Main responsibility:** First-pass classification of what the event appears to be.

**Interaction with other agents:** Sends findings to Verification; findings are visible to Intelligence and Behavioral Analysis agents for comparison.

**Evidence:** Must cite the specific part of the input event that supports its classification.

**Failure behavior:** If it cannot produce a valid classification, it must say so explicitly rather than guessing; this is treated as a low-confidence finding.

**Uncertainty behavior:** Must express confidence rather than a single unqualified answer when the event is ambiguous.

**What it should NOT do:** Should not fabricate evidence not present in the input event. Should not take or recommend a real action — its job is analysis only.

---

## Intelligence Agent

**Purpose:** Correlate the event against known threat-intelligence indicators (e.g., IP/domain/hash reputation).

**Inputs:** Indicators of compromise (IOCs) extracted from the event; a local/static threat-intelligence dataset (source **TO BE DECIDED**).

**Outputs:** Match/no-match result against known indicators, source of the match, confidence.

**Main responsibility:** Determine whether the event involves anything already known to be malicious.

**Interaction with other agents:** Sends findings to Verification; visible to Detection and Behavioral Analysis agents.

**Evidence:** Must cite which indicator matched and against which data source.

**Failure behavior:** If no indicator data is available for the event, must report "no match found," not "benign."

**Uncertainty behavior:** Absence of a known-bad match is not the same as a confirmed-benign result; this distinction must be preserved in the output.

**What it should NOT do:** Should not treat "no match" as proof of safety. Should not query live external services unless explicitly approved (see `docs/THREAT_MODEL.md`).

---

## Behavioral Analysis Agent

**Purpose:** Compare the current event against a historical baseline for the relevant user/host/entity.

**Inputs:** Current event; historical baseline data for the same entity (source and format **TO BE DECIDED**).

**Outputs:** Anomaly assessment, description of the deviation from baseline, confidence.

**Main responsibility:** Determine whether the event is unusual for this specific entity, independent of whether it matches a known threat signature.

**Interaction with other agents:** Sends findings to Verification; visible to Detection and Intelligence agents.

**Evidence:** Must describe which aspect of the current event deviates from the baseline and by how much (qualitatively or quantitatively).

**Failure behavior:** If no baseline exists for the entity, must report this explicitly rather than defaulting to "anomalous" or "normal."

**Uncertainty behavior:** Should express how confident it is that the deviation is meaningful versus noise.

**What it should NOT do:** Should not assume a baseline that was not actually provided. Should not make a final malicious/benign call on its own — anomaly is one input, not a verdict.

---

## Verification

**Purpose:** Check whether other agents' findings are actually supported by the evidence they cited.

**Inputs:** Findings + cited evidence from Detection, Intelligence, and Behavioral Analysis agents; the original event.

**Outputs:** A result per finding — verified consistent, verified inconsistent, or inconclusive — with a stated reason. This result is passed to Trust Evaluation as one input to the trust score (see `docs/architecture/TRUST_MODEL.md`); it is not applied anywhere else in the decision path.

**Main responsibility:** Catch findings whose stated conclusion is not actually backed by the evidence cited (inconsistency detection), not to re-solve the classification task itself.

**Interaction with other agents:** Receives findings from all three specialist agents; sends verification results to Trust Evaluation.

**Evidence:** Must state specifically why a finding passed, failed, or was inconclusive (e.g., "cited indicator does not appear in the input event").

**Failure behavior:** If it cannot determine consistency (e.g., ambiguous evidence), it must report this as inconclusive, not as a pass.

**Uncertainty behavior:** Should distinguish "verified consistent," "verified inconsistent," and "inconclusive" rather than forcing a binary result.

**What it should NOT do:** Should not independently re-classify the event as if it were another Detection Agent. Should not be treated as infallible — its own reliability is a known limitation (see `docs/architecture/TRUST_MODEL.md`). Its result must feed the trust score exactly once, never as a second, separate decision weight.

---

## Open Questions (TO BE DECIDED by the team)

- Exact prompt templates for each agent.
- Source and format of the threat-intelligence dataset (Intelligence Agent).
- Source and format of historical baseline data (Behavioral Analysis Agent).
- Whether any agent uses tools/function-calling in Phase 1, or only in Phase 2.
- Whether Verification's own reliability is trust-scored, or treated as a fixed, trusted component (recommended for simplicity, but not yet decided).
- Which agent(s) receive the fine-tuned model in Phase 2 (see `docs/DECISIONS.md`, D-010).
