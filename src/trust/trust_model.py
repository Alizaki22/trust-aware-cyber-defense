"""Trust evaluation: Trust_i = w1*HistoricalAccuracy_i + w2*Verification_i + w3*PeerAgreement_i.

- HistoricalAccuracy_i : calibration accuracy (TrustHistory), default 0.5.
- Verification_i       : verified_consistent 1.0, inconclusive 0.5, verified_inconsistent 0.0.
                         The verification result is used here and nowhere else.
- PeerAgreement_i      : 0.0 if agent i abstained; else the share of the other
                         non-abstaining agents' historical accuracy that is on the same
                         side (threat = malicious/suspicious, or benign) as agent i;
                         0.5 (neutral) if no other agent voted.
                         Historical accuracy (not trust) is used to avoid circularity.
"""
from __future__ import annotations

from src.models import AgentFinding, TrustScore, VerificationResult
from src.trust.trust_history import TrustHistory

VERIFICATION_SCORE = {"verified_consistent": 1.0, "inconclusive": 0.5, "verified_inconsistent": 0.0}
NEUTRAL_PEER_AGREEMENT = 0.5


THREAT_VERDICTS = {"malicious", "suspicious"}


def abstains(finding: AgentFinding) -> bool:
    return finding.error is not None or finding.verdict == "unknown"


def side(verdict: str) -> str:
    """'threat' for malicious/suspicious, 'benign' for benign."""
    return "threat" if verdict in THREAT_VERDICTS else verdict


class TrustEvaluator:
    def __init__(self, history: TrustHistory, w_hist: float = 0.40, w_ver: float = 0.35, w_peer: float = 0.25):
        if abs(w_hist + w_ver + w_peer - 1.0) > 1e-9:
            raise ValueError("trust weights must sum to 1")
        self.history, self.w = history, (w_hist, w_ver, w_peer)

    def peer_agreement(self, finding: AgentFinding, findings: list[AgentFinding]) -> float:
        if abstains(finding):
            return 0.0
        peers = [f for f in findings if f.agent != finding.agent and not abstains(f)]
        total = sum(self.history.get(p.agent) for p in peers)
        if not peers or total == 0:
            return NEUTRAL_PEER_AGREEMENT
        return sum(self.history.get(p.agent) for p in peers if side(p.verdict) == side(finding.verdict)) / total

    def evaluate(self, findings: list[AgentFinding], verification: list[VerificationResult]) -> list[TrustScore]:
        status = {v.agent: v.status for v in verification}
        scores = []
        for finding in findings:
            hist = self.history.get(finding.agent)
            ver = VERIFICATION_SCORE[status.get(finding.agent, "inconclusive")]
            peer = self.peer_agreement(finding, findings)
            total = self.w[0] * hist + self.w[1] * ver + self.w[2] * peer
            scores.append(TrustScore(agent=finding.agent, event_id=finding.event_id,
                                     historical_accuracy=round(hist, 4), verification_score=ver,
                                     peer_agreement=round(peer, 4), total_score=round(min(1.0, total), 4)))
        return scores
