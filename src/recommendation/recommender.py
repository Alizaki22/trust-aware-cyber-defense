"""Trust-weighted final recommendation.

Aggregation: two-stage weighted vote. Each non-abstaining agent adds its
trust score (trust_weighted) or 1.0 (equal_weighted, the Experiment 2
control) to its verdict.
  Stage 1: threat (malicious + suspicious) vs benign; a tie -> "unknown".
  Stage 2: if threat wins, "malicious" if its weight >= "suspicious"'s
           weight, else "suspicious".
Abstentions ("unknown" or failed agents) do not vote.

confidence_value = winning side's share of the total trust-weighted vote
(0 if no winner); label: >=0.75 high, >=0.55 medium, >0 low, 0 none.

Routing (first rule that applies):
  no winner / tie               -> human_review
  confidence_value < threshold  -> human_review
  agents disagree AND winner is not benign -> human_review
  winner benign                 -> further_verification (no action proposed)
  otherwise                     -> simulated_action (never executed, D-011)
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.models import (AgentFinding, FinalRecommendation, SimulatedAction, TrustScore,
                        VerificationResult, WeightingOutcome)
from src.trust.trust_model import abstains, side


def weighted_vote(findings: list[AgentFinding], weights: dict[str, float], method: str) -> WeightingOutcome:
    tally: dict[str, float] = {}
    for finding in findings:
        if abstains(finding):
            continue
        tally[finding.verdict] = round(tally.get(finding.verdict, 0.0) + weights[finding.agent], 4)
    if not tally:
        return WeightingOutcome(method=method, verdict="unknown", verdict_weights={}, tie=False)
    threat = tally.get("malicious", 0.0) + tally.get("suspicious", 0.0)
    benign = tally.get("benign", 0.0)
    if abs(threat - benign) < 1e-9:
        return WeightingOutcome(method=method, verdict="unknown", verdict_weights=tally, tie=True)
    if benign > threat:
        verdict = "benign"
    else:
        verdict = "malicious" if tally.get("malicious", 0.0) >= tally.get("suspicious", 0.0) else "suspicious"
    return WeightingOutcome(method=method, verdict=verdict, verdict_weights=tally, tie=False)


def side_weight(outcome: WeightingOutcome) -> float:
    w = outcome.verdict_weights
    if outcome.verdict == "benign":
        return w.get("benign", 0.0)
    if outcome.verdict in ("malicious", "suspicious"):
        return w.get("malicious", 0.0) + w.get("suspicious", 0.0)
    return 0.0


def confidence_label(value: float) -> str:
    if value >= 0.75:
        return "high"
    if value >= 0.55:
        return "medium"
    return "low" if value > 0 else "none"


class RecommendationEngine:
    def __init__(self, confidence_threshold: float = 0.60):
        self.threshold = confidence_threshold

    def recommend(self, *, event_id: str, run_id: str, phase: int, agent_models: dict[str, str],
                  is_mock: bool, findings: list[AgentFinding], verification_results: list[VerificationResult],
                  trust_scores: list[TrustScore], action_target: str) -> FinalRecommendation:
        trust = {t.agent: t.total_score for t in trust_scores}
        trust_weighted = weighted_vote(findings, trust, "trust_weighted")
        equal_weighted = weighted_vote(findings, {f.agent: 1.0 for f in findings}, "equal_weighted")
        verdict = trust_weighted.verdict

        total = sum(trust_weighted.verdict_weights.values())
        value = round(side_weight(trust_weighted) / total, 4) if total else 0.0
        voted = {side(f.verdict) for f in findings if not abstains(f)}
        disagreement = len(voted) > 1

        if verdict == "unknown":
            routing, reason = "human_review", ("Weighted vote tied." if trust_weighted.tie else "No agent reached a conclusion.")
        elif value < self.threshold:
            routing, reason = "human_review", f"Winning share {value:.2f} is below the threshold {self.threshold:.2f}."
        elif disagreement and verdict != "benign":
            routing, reason = "human_review", "Agents disagree on a non-benign verdict."
        elif verdict == "benign":
            routing, reason = "further_verification", f"Benign verdict (share {value:.2f}); no action proposed."
        else:
            routing, reason = "simulated_action", f"Agents agree on '{verdict}' (share {value:.2f} >= {self.threshold:.2f})."

        supporters = sorted((f for f in findings if not abstains(f) and f.verdict == verdict),
                            key=lambda f: -trust.get(f.agent, 0.0))
        classification = supporters[0].classification if supporters else "undetermined"
        action = (SimulatedAction(description=f"Simulated — would contain traffic matching {action_target} "
                                              f"and open an incident ticket ({classification}).")
                  if routing == "simulated_action" else None)
        summary = "; ".join(f"{f.agent}: {f.verdict}" for f in findings) if disagreement else None
        changed = trust_weighted.verdict != equal_weighted.verdict
        reasoning = (f"Trust-weighted vote: {verdict}; equal-weighted vote: {equal_weighted.verdict}"
                     f"{' (trust changed the outcome)' if changed else ''}. {reason}")
        return FinalRecommendation(
            run_id=run_id, event_id=event_id, phase=phase,
            model="; ".join(f"{a}={m}" for a, m in agent_models.items()), agent_models=agent_models,
            created_at=datetime.now(timezone.utc), is_mock=is_mock, classification=classification,
            verdict=verdict, confidence=confidence_label(value), confidence_value=value, routing=routing,
            routing_reason=reason, simulated_action=action, agent_findings=findings,
            verification_results=verification_results, trust_scores=trust_scores,
            trust_weighted=trust_weighted, equal_weighted=equal_weighted, trust_changed_outcome=changed,
            disagreement_summary=summary, reasoning=reasoning)
