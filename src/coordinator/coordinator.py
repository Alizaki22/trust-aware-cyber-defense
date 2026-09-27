"""Coordinator: runs the Phase 1 pipeline for one event.

Detection -> Intelligence -> Behavioral Analysis run in that order but
independently (no agent sees another's finding), then Verification checks
every finding against the event, Trust scores each agent, and the
RecommendationEngine produces the FinalRecommendation.
"""
from __future__ import annotations

from src.agents.base import event_fields
from src.agents.verification import VerificationAgent
from src.models import AgentFinding, FinalRecommendation, SecurityEvent
from src.recommendation.recommender import RecommendationEngine
from src.trust.trust_model import TrustEvaluator

SPECIALIST_ORDER = ("detection", "intelligence", "behavioral")


class Coordinator:
    def __init__(self, agents: dict, verifier: VerificationAgent, trust: TrustEvaluator,
                 recommender: RecommendationEngine, run_id: str, phase: int = 1):
        missing = [name for name in SPECIALIST_ORDER if name not in agents]
        if missing:
            raise ValueError(f"missing agents: {missing}")
        self.agents, self.verifier, self.trust, self.recommender = agents, verifier, trust, recommender
        self.run_id, self.phase = run_id, phase

    @property
    def agent_models(self) -> dict[str, str]:
        models = {name: self.agents[name].model_id for name in SPECIALIST_ORDER}
        models["verification"] = self.verifier.model_id
        return models

    def dispatch_to_agents(self, event: SecurityEvent) -> list[AgentFinding]:
        findings = []
        for name in SPECIALIST_ORDER:
            agent = self.agents[name]
            try:
                findings.append(agent.analyze(event))
            except Exception as error:  # an agent bug must not take down the pipeline
                findings.append(agent.error_finding(event, f"{type(error).__name__}: {error}"))
        return findings

    def process_event(self, event: SecurityEvent | dict) -> FinalRecommendation:
        if not isinstance(event, SecurityEvent):
            event = SecurityEvent.model_validate(event)
        findings = self.dispatch_to_agents(event)
        verification = self.verifier.verify_findings(findings, event)
        trust_scores = self.trust.evaluate(findings, verification)
        fields = event_fields(event)
        target = (f"source_ip={event.source_ip}" if event.source_ip else
                  ", ".join(f"{k}={fields[k]}" for k in ("proto", "service", "state") if k in fields) or event.event_id)
        is_mock = any(m.startswith("stub:") for m in self.agent_models.values())
        return self.recommender.recommend(
            event_id=event.event_id, run_id=self.run_id, phase=self.phase, agent_models=self.agent_models,
            is_mock=is_mock, findings=findings, verification_results=verification,
            trust_scores=trust_scores, action_target=target)
