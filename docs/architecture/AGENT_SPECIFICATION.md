# Agent Specification

Status: **PROPOSED — REQUIRES TEAM APPROVAL** for exact prompts/implementation; roles and responsibilities below reflect the current documented concept.

These are logical responsibilities. They do not require four independent models, databases, or services.

---

## Detection Agent

**Purpose:** Classify the security event (e.g., type of intrusion/alert, severity).

**Inputs:** Raw security event (log line, alert, or similar structured/semi-structured data).

**Outputs:** Classification label, severity, cited evidence from the input, confidence.

**Main responsibility:** First-pass classification of what the event appears to be.

**Interaction with other agents:** Sends findings to Verification via the Coordinator. Does not see Intelligence's or Behavioral Analysis's findings before producing its own — all three specialist agents run independently on the same event so their conclusions aren't biased by each other (see `docs/AGENT_DESIGN.md`, `docs/architecture/DATA_FLOW.md`).

**Evidence:** Must cite the specific part of the input event that supports its classification.

**Failure behavior:** If it cannot produce a valid classification, it must say so explicitly rather than guessing; this is treated as a low-confidence finding.

**Uncertainty behavior:** Must express confidence rather than a single unqualified answer when the event is ambiguous.

**What it should NOT do:** Should not fabricate evidence not present in the input event. Should not take or recommend a real action — its job is analysis only.

**Phase 1 implementation:** the only LLM agent (Qwen3-4B-Instruct-2507 in Phase 1; the Phase 2 fine-tuning target). It returns `verdict` (malicious | suspicious | benign | unknown), `classification` (exactly one of the ten UNSW-NB15 labels in `DETECTION_CLASSES`, stated in the prompt and enforced by the output schema), `evidence` (`field=value` pairs copied from the event), `confidence` and `reasoning`. There is no separate "severity" field; `verdict` plus `confidence` carry that information. An answer that doesn't fit the schema is retried once and otherwise reported as a failed finding, never guessed. Details: `docs/PHASE1_IMPLEMENTATION.md` §3–§4.

---

## Intelligence Agent

**Purpose:** Correlate the event against known threat-intelligence indicators (e.g., IP/domain/hash reputation).

**Inputs:** Indicators of compromise (IOCs) extracted from the event; a local/static threat-intelligence dataset (Phase 1: synthetic IOC list + UNSW-NB15 train-split flow signatures, see below).

**Outputs:** Match/no-match result against known indicators, source of the match, confidence.

**Main responsibility:** Determine whether the event involves anything already known to be malicious.

**Interaction with other agents:** Sends findings to Verification via the Coordinator. Runs independently of Detection and Behavioral Analysis — see the note under Detection Agent above.

**Evidence:** Must cite which indicator matched and against which data source.

**Failure behavior:** If no indicator data is available for the event, must report "no match found," not "benign."

**Uncertainty behavior:** Absence of a known-bad match is not the same as a confirmed-benign result; this distinction must be preserved in the output.

**What it should NOT do:** Should not treat "no match" as proof of safety. Should not query live external services unless explicitly approved (see `docs/THREAT_MODEL.md`).

**Phase 1 implementation (team-approved, audit fix C2):** two local reference sources, checked in order. (1) IOC lookup of IPs/domains/hashes against a SYNTHETIC IOC file. (2) A flow-signature reputation: the `(proto, service, state, sttl, dttl)` tuple against signatures learned from the **UNSW-NB15 train split only** (support ≥ 20; attack share ≥ 0.95 → known malicious, ≤ 0.05 → known benign, like an allowlist entry). A known-benign signature is the only way this agent says `benign`; an unknown signature or no indicators remains "no match" / an abstention. Evidence cites the matched fields and the reference source. Details: `docs/PHASE1_IMPLEMENTATION.md` §4.

---

## Behavioral Analysis Agent

**Purpose:** Compare the current event against a historical baseline for the relevant user/host/entity.

**Inputs:** Current event; historical baseline data for the same entity (Phase 1: synthetic entity baselines + UNSW-NB15 train-split normal-traffic profiles, see below).

**Outputs:** Anomaly assessment, description of the deviation from baseline, confidence.

**Main responsibility:** Determine whether the event is unusual for this specific entity, independent of whether it matches a known threat signature.

**Interaction with other agents:** Sends findings to Verification via the Coordinator. Runs independently of Detection and Intelligence — see the note under Detection Agent above.

**Evidence:** Must describe which aspect of the current event deviates from the baseline and by how much (qualitatively or quantitatively).

**Failure behavior:** If no baseline exists for the entity, must report this explicitly rather than defaulting to "anomalous" or "normal."

**Uncertainty behavior:** Should express how confident it is that the deviation is meaningful versus noise.

**What it should NOT do:** Should not assume a baseline that was not actually provided. Should not make a final malicious/benign call on its own — anomaly is one input, not a verdict. Its output is one vote among several; the final call is made by the trust-weighted recommendation.

**Phase 1 implementation (team-approved amendment, audit fix C2):** the baseline is the entity baseline when one exists, otherwise a (proto, service) normal-traffic profile learned from **train-split Normal records only**; with neither, the agent abstains ("no baseline available"). ≥ 2 deviating features → `suspicious` (never `malicious`). Within baseline → **`benign` with confidence `low`**, meaning "consistent with the normal-traffic baseline", not "proven benign". This replaces the earlier abstention so that UNSW-NB15 events have more than two voters; the vote's weakness is measured on the validation calibration subset and applied through trust (historical accuracy) rather than hidden. Details: `docs/PHASE1_IMPLEMENTATION.md` §4.

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
- ~~Source and format of historical baseline data (Behavioral Analysis Agent).~~ Resolved for Phase 1 (see Behavioral Analysis Agent).
- Whether any agent uses tools/function-calling in Phase 1, or only in Phase 2.
- Whether Verification's own reliability is trust-scored, or treated as a fixed, trusted component (recommended for simplicity, but not yet decided).
- ~~Which agent(s) receive the fine-tuned model in Phase 2 (see `docs/DECISIONS.md`, D-010).~~ Decided by the team: the Detection agent only.
