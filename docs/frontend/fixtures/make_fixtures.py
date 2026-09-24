"""
MOCK DATA GENERATOR — frontend development only.

Defines the *proposed* input/output schema (docs/frontend/SCHEMA_PROPOSAL.md) and
generates three illustrative scenario fixtures so the frontend can be built
before the real pipeline exists.

Nothing here is a real result. Trust weights, verification scores, the peer
agreement formula and routing rules are PLACEHOLDERS (TO BE DECIDED by the team,
see docs/architecture/TRUST_MODEL.md). They only exist so the numbers in the
fixtures are internally consistent.

Run:  python docs/frontend/fixtures/make_fixtures.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, IPvAnyAddress

# ---------------------------------------------------------------- schema ----
AgentName = Literal["detection", "intelligence", "behavioral"]
Verdict = Literal["malicious", "suspicious", "benign", "unknown"]
Confidence = Literal["high", "medium", "low", "none"]
VerificationStatus = Literal["verified_consistent", "verified_inconsistent", "inconclusive"]
Routing = Literal["simulated_action", "further_verification", "human_review"]


class SecurityEvent(BaseModel):
    """Input event. Validation rules = SCHEMA_PROPOSAL.md Part A."""
    event_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime                                   # ISO 8601
    event_type: str = Field(min_length=1)
    source_ip: Optional[IPvAnyAddress] = None
    destination_ip: Optional[IPvAnyAddress] = None
    destination_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None
    raw_content: str = Field(min_length=1, max_length=10_000)  # max: PLACEHOLDER, confirm with M1
    entity: Optional[str] = None
    metadata: dict = {}


class AgentFinding(BaseModel):
    agent: AgentName
    event_id: str
    classification: str          # free label, e.g. "brute_force_login"
    verdict: Verdict             # PROPOSED: common scale so findings can be combined/compared
    evidence: str
    confidence: Confidence
    reasoning: str
    error: Optional[str] = None  # PROPOSED: set when the agent failed (LLM/parse error)


class VerificationResult(BaseModel):
    agent: AgentName
    event_id: str
    status: VerificationStatus
    reason: str


class TrustScore(BaseModel):
    agent: AgentName
    event_id: str
    historical_accuracy: float
    verification_score: float
    peer_agreement: float
    total_score: float


class WeightingOutcome(BaseModel):
    """PROPOSED: result of one aggregation method, so the UI can compare them."""
    method: Literal["trust_weighted", "equal_weighted"]
    verdict: Verdict                   # "unknown" when tied or no votes
    verdict_weights: dict[str, float]  # verdict -> summed weight
    tie: bool = False


class SimulatedAction(BaseModel):
    """PROPOSED: what the system *would* do. Never executed (D-011)."""
    description: str
    executed: Literal[False] = False


class FinalRecommendation(BaseModel):
    run_id: str                                   # PROPOSED
    event_id: str
    phase: Literal[1, 2]                          # PROPOSED
    model: str                                    # PROPOSED
    created_at: datetime                          # PROPOSED
    classification: str
    verdict: Verdict                              # PROPOSED
    confidence: Confidence
    confidence_value: float                       # PROPOSED: numeric value the threshold is applied to
    routing: Routing
    routing_reason: str                           # PROPOSED
    simulated_action: Optional[SimulatedAction] = None  # PROPOSED
    agent_findings: list[AgentFinding]
    verification_results: list[VerificationResult]     # PROPOSED (missing today)
    trust_scores: list[TrustScore]
    trust_weighted: WeightingOutcome              # PROPOSED
    equal_weighted: WeightingOutcome              # PROPOSED
    trust_changed_outcome: bool                   # PROPOSED
    disagreement_summary: Optional[str] = None
    reasoning: str
    is_mock: bool = True                          # PROPOSED: UI shows a MOCK badge


class AnalysisRun(BaseModel):
    """What the frontend loads: the input event + the system's output."""
    scenario: str
    event: SecurityEvent
    result: FinalRecommendation


# ------------------------------------------------- placeholder trust math ----
W_HIST, W_VER, W_PEER = 0.40, 0.35, 0.25          # PLACEHOLDER (TBD)
VER_SCORE = {"verified_consistent": 1.0, "inconclusive": 0.5, "verified_inconsistent": 0.0}
CONF_MAP = [(0.75, "high"), (0.55, "medium"), (0.0, "low")]  # PLACEHOLDER
THRESHOLD = 0.60                                   # PLACEHOLDER (API_REFERENCE default)


def peer_agreement(agent, findings, history):
    """Share of *other* agents' historical accuracy that agrees with this verdict.
    Uses historical accuracy (not trust) to avoid a circular definition."""
    me = next(f for f in findings if f.agent == agent)
    others = [f for f in findings if f.agent != agent and f.verdict != "unknown"]
    total = sum(history[f.agent] for f in others)
    if total == 0 or me.verdict == "unknown":
        return 0.0
    return sum(history[f.agent] for f in others if f.verdict == me.verdict) / total


def aggregate(findings, weights, method):
    tally: dict[str, float] = {}
    for f in findings:
        if f.verdict == "unknown" or f.error:
            continue  # abstains
        tally[f.verdict] = round(tally.get(f.verdict, 0) + weights[f.agent], 4)
    if not tally:
        return WeightingOutcome(method=method, verdict="unknown", verdict_weights={})
    top = max(tally.values())
    leaders = [v for v, w in tally.items() if w == top]
    tie = len(leaders) > 1  # PLACEHOLDER tie rule: no winner -> "unknown"
    return WeightingOutcome(method=method, verdict="unknown" if tie else leaders[0],
                            verdict_weights=tally, tie=tie)


def build(scenario, event, findings, verifs, history, classification,
          action_text, run_n):
    v_by = {v.agent: v for v in verifs}
    trust = []
    for f in findings:
        h, vs = history[f.agent], VER_SCORE[v_by[f.agent].status]
        pa = peer_agreement(f.agent, findings, history)
        trust.append(TrustScore(agent=f.agent, event_id=event.event_id,
                                historical_accuracy=h, verification_score=vs,
                                peer_agreement=round(pa, 3),
                                total_score=round(W_HIST * h + W_VER * vs + W_PEER * pa, 3)))
    tw = aggregate(findings, {t.agent: t.total_score for t in trust}, "trust_weighted")
    ew = aggregate(findings, {f.agent: 1.0 for f in findings}, "equal_weighted")

    total_w = sum(tw.verdict_weights.values()) or 1
    cv = round(tw.verdict_weights.get(tw.verdict, 0) / total_w, 3)
    conf = next(label for cut, label in CONF_MAP if cv >= cut)
    verdicts = {f.verdict for f in findings if f.verdict != "unknown"}
    disagree = len(verdicts) > 1

    if cv < THRESHOLD or (disagree and tw.verdict != "benign"):
        routing, reason = "human_review", (
            f"Winning share {cv:.2f} below threshold {THRESHOLD}" if cv < THRESHOLD
            else "Agents disagreed on a non-benign verdict")
    elif tw.verdict == "benign":
        routing, reason = "further_verification", "Benign verdict — no action proposed"
    else:
        routing, reason = "simulated_action", f"Agreement share {cv:.2f} ≥ {THRESHOLD}"

    return AnalysisRun(scenario=scenario, event=event, result=FinalRecommendation(
        run_id=f"mock-run-{run_n:03d}", event_id=event.event_id, phase=1,
        model="base-llm (TBD)", created_at=datetime(2026, 9, 25, 10, run_n),
        classification=classification, verdict=tw.verdict, confidence=conf,
        confidence_value=cv, routing=routing, routing_reason=reason,
        simulated_action=SimulatedAction(description=action_text) if routing == "simulated_action" else None,
        agent_findings=findings, verification_results=verifs, trust_scores=trust,
        trust_weighted=tw, equal_weighted=ew,
        trust_changed_outcome=tw.verdict != ew.verdict,
        disagreement_summary=(
            "; ".join(f"{f.agent}: {f.verdict}" for f in findings) if disagree else None),
        reasoning=f"Trust-weighted verdict '{tw.verdict}' "
                  f"(equal-weighted: '{ew.verdict}'). {reason}.",
    ))


def F(agent, eid, cls, verdict, ev, conf, why):
    return AgentFinding(agent=agent, event_id=eid, classification=cls, verdict=verdict,
                        evidence=ev, confidence=conf, reasoning=why)


def V(agent, eid, status, reason):
    return VerificationResult(agent=agent, event_id=eid, status=status, reason=reason)


# --------------------------------------------------------------- scenarios --
def scenario_clear_attack():
    e = SecurityEvent(event_id="evt-001", timestamp="2026-09-20T02:14:07Z",
        event_type="log_entry", source_ip="203.0.113.45", destination_ip="10.0.0.12",
        destination_port=22, protocol="TCP", entity="srv-web-01",
        raw_content="sshd[4121]: Failed password for root from 203.0.113.45 port 51234 ssh2 "
                    "(x312 in 60s); Accepted password for root from 203.0.113.45",
        metadata={"source": "SYNTHETIC"})
    fs = [F("detection", e.event_id, "brute_force_login", "malicious",
            "312 failed root logins in 60s followed by an accepted login", "high",
            "Classic SSH brute force pattern ending in success"),
          F("intelligence", e.event_id, "known_bad_ip", "malicious",
            "203.0.113.45 present in local synthetic IOC list (ioc_ips.json)", "high",
            "Source IP matches a known-bad indicator"),
          F("behavioral", e.event_id, "anomalous_login", "malicious",
            "srv-web-01 baseline: 0 root logins/week, never from this /24", "high",
            "Root login from never-seen network at 02:14")]
    vs = [V("detection", e.event_id, "verified_consistent", "Failure count and accept line present in raw_content"),
          V("intelligence", e.event_id, "verified_consistent", "Cited IP appears in event source_ip"),
          V("behavioral", e.event_id, "verified_consistent", "Entity and time match event fields")]
    h = {"detection": 0.82, "intelligence": 0.78, "behavioral": 0.85}
    return build("Clear attack — all agents agree", e, fs, vs, h, "brute_force_login",
                 "Would block 203.0.113.45 at the perimeter firewall and disable root SSH on srv-web-01", 1)


def scenario_trust_flip():
    e = SecurityEvent(event_id="evt-002", timestamp="2026-09-21T14:03:55Z",
        event_type="network_flow", source_ip="10.0.4.77", destination_ip="198.51.100.20",
        destination_port=443, protocol="TCP", entity="laptop-fin-07",
        raw_content="flow 10.0.4.77:50122 -> 198.51.100.20:443 bytes_out=1.8GB duration=41m",
        metadata={"source": "SYNTHETIC"})
    fs = [F("detection", e.event_id, "normal_https", "benign",
            "Destination is a known software update server", "high",
            "HTTPS to update infrastructure"),  # hallucinated: nothing in the event says this
          F("intelligence", e.event_id, "allowlisted_cdn", "benign",
            "198.51.100.0/24 appears in synthetic CDN allowlist", "low",
            "Destination range is allowlisted, but allowlist is coarse"),
          F("behavioral", e.event_id, "exfil_volume_anomaly", "malicious",
            "laptop-fin-07 baseline upload ≈ 40MB/day; this flow sent 1.8GB in 41 min", "high",
            "Upload volume ~45x baseline — possible data exfiltration")]
    vs = [V("detection", e.event_id, "verified_inconsistent", "Cited 'update server' is not present anywhere in the event"),
          V("intelligence", e.event_id, "inconclusive", "Allowlist match is on a /24, not the exact host"),
          V("behavioral", e.event_id, "verified_consistent", "bytes_out and entity match the event")]
    h = {"detection": 0.35, "intelligence": 0.45, "behavioral": 0.85}
    return build("Trust flips the outcome — misleading Detection agent", e, fs, vs, h,
                 "exfil_volume_anomaly", "Would isolate laptop-fin-07 from the network", 2)


def scenario_ambiguous():
    e = SecurityEvent(event_id="evt-003", timestamp="2026-09-22T23:48:10Z",
        event_type="log_entry", source_ip="192.0.2.88", entity="user:asha.m",
        raw_content="VPN login user=asha.m from 192.0.2.88 (new device, country=SG) MFA=passed",
        metadata={"source": "SYNTHETIC"})
    fs = [F("detection", e.event_id, "suspicious_login", "suspicious",
            "New device and new country", "medium", "Unusual login context"),
          F("intelligence", e.event_id, "no_match", "unknown",
            "192.0.2.88 not found in IOC list", "none",
            "No match found — this is NOT the same as benign"),
          F("behavioral", e.event_id, "travel_consistent", "benign",
            "asha.m baseline includes monthly logins from SG; MFA passed", "medium",
            "Within historical travel pattern")]
    vs = [V("detection", e.event_id, "verified_consistent", "New device and country present in raw_content"),
          V("intelligence", e.event_id, "verified_consistent", "No-match correctly reported"),
          V("behavioral", e.event_id, "inconclusive", "Baseline claim cannot be checked against the event alone")]
    h = {"detection": 0.70, "intelligence": 0.78, "behavioral": 0.72}
    return build("Ambiguous — agents disagree", e, fs, vs, h, "suspicious_login", "", 3)


def check_invalid_example(out: Path) -> None:
    """The invalid fixture must be rejected (used to build the P1 error state)."""
    from pydantic import ValidationError
    bad = json.loads((out / "invalid_event.json").read_text())
    try:
        SecurityEvent.model_validate(bad)
    except ValidationError as err:
        fields = sorted({".".join(map(str, e["loc"])) for e in err.errors()})
        print(f"invalid_event.json: rejected as expected on {fields}")
        return
    raise SystemExit("invalid_event.json was ACCEPTED — validation rules are broken")


if __name__ == "__main__":
    out = Path(__file__).parent
    check_invalid_example(out)
    for i, fn in enumerate([scenario_clear_attack, scenario_trust_flip, scenario_ambiguous], 1):
        run = fn()
        AnalysisRun.model_validate(run.model_dump())  # round-trip validation
        path = out / f"scenario_{i:02d}.json"
        path.write_text(run.model_dump_json(indent=2))
        r = run.result
        print(f"{path.name}: verdict={r.verdict} equal={r.equal_weighted.verdict} "
              f"flip={r.trust_changed_outcome} conf={r.confidence}({r.confidence_value}) "
              f"routing={r.routing}")
