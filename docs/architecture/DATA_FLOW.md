# Data Flow

Status: **PROPOSED** — reflects the current documented concept; exact data formats are TO BE DECIDED.

## Flow Overview

```
Security Information
        ↓
Input Processing
        ↓
Agent Analysis (Detection, Intelligence, Behavioral Analysis — run independently on the same event)
        ↓
Agent Outputs (structured findings: classification/assessment + evidence + confidence, per agent)
        ↓
Verification (each finding checked against its cited evidence — result: verified consistent / verified inconsistent / inconclusive)
        ↓
Trust Evaluation (verification result + historical accuracy + peer agreement → trust score, applied once per finding)
        ↓
Trust-Weighted Final Recommendation (classification + confidence + routing suggestion)
        ↓
Simulated Action / Further Verification / Human Review
```

## Stage Detail

**1. Security Information** — a raw security event: a log line, alert, or email, depending on which scenario the team selects (see `docs/RESEARCH.md`).

**2. Input Processing** — normalizes the raw event into whatever structured format the agents expect (exact schema **TO BE DECIDED**, likely a simple dictionary/JSON object with fields such as event type, raw content, timestamp, and relevant entity identifiers).

**3. Agent Analysis** — the Coordinator sends the processed event to Detection, Intelligence, and Behavioral Analysis agents. These run independently (not sequentially dependent on each other) so their findings are not biased by one another before Verification.

**4. Agent Outputs** — each agent returns a structured finding, e.g. (illustrative only, not final):

```
{
  "agent": "detection",
  "classification": "suspicious_login",
  "evidence": "login from new IP outside normal hours",
  "confidence": "medium"
}
```

**5. Verification** — checks each finding's evidence against the actual event content, returning a single result (verified consistent / verified inconsistent / inconclusive) per finding.

**6. Trust Evaluation** — combines each agent's current trust score inputs (historical accuracy, this event's verification result, peer agreement) to determine how much weight the finding gets in the final decision. The verification result is used exactly once here — it is not reapplied as a separate weight later in the flow.

**7. Trust-Weighted Final Recommendation** — the trust-weighted combination of findings, expressed as a final classification, an overall confidence, and a routing suggestion.

**8. Routing** — the recommendation routes to a **simulated** action, further verification, or human review. The system never performs a real action against live infrastructure (see `docs/THREAT_MODEL.md`).

## Example (Illustrative Only)

A suspicious login event: Detection reports "suspicious_login" with medium confidence; Intelligence reports "no known-bad indicator match"; Behavioral Analysis reports "significant deviation from baseline" with high confidence. Verification confirms all three findings are consistent with the event evidence. Trust Evaluation weights Behavioral Analysis's finding most heavily due to high historical accuracy and a "verified consistent" result. The Trust-Weighted Final Recommendation is "likely suspicious — recommend human review," since no single agent alone reached full confidence, and the resulting action is a simulated flag for review, not a real automated response.

This example is for illustration only and does not represent an actual tested result.
