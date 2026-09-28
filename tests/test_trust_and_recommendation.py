import json

import pytest

from src.models import AgentFinding, VerificationResult
from src.recommendation.recommender import RecommendationEngine, confidence_label, weighted_vote
from src.trust.trust_history import TrustHistory, calibrate, verdict_is_correct
from src.trust.trust_model import TrustEvaluator


def f(agent, verdict, error=None):
    return AgentFinding(agent=agent, event_id="e", verdict=verdict, classification=f"{agent}-{verdict}",
                        evidence="proto=tcp" if verdict != "unknown" else "", confidence="high",
                        reasoning="r", error=error)


def v(agent, status):
    return VerificationResult(agent=agent, event_id="e", status=status, reason="r")


def test_trust_formula_exact_values():
    history = TrustHistory({"detection": 0.35, "intelligence": 0.45, "behavioral": 0.85})
    findings = [f("detection", "benign"), f("intelligence", "benign"), f("behavioral", "malicious")]
    ver = [v("detection", "verified_inconsistent"), v("intelligence", "inconclusive"),
           v("behavioral", "verified_consistent")]
    scores = {t.agent: t for t in TrustEvaluator(history).evaluate(findings, ver)}
    # detection: 0.4*0.35 + 0.35*0 + 0.25*(0.45/1.30)
    assert scores["detection"].total_score == pytest.approx(0.4 * 0.35 + 0.25 * 0.45 / 1.30, abs=1e-4)
    assert scores["behavioral"].peer_agreement == 0.0
    assert scores["intelligence"].verification_score == 0.5


def test_peer_agreement_edge_cases():
    history = TrustHistory()
    scores = {t.agent: t for t in TrustEvaluator(history).evaluate(
        [f("detection", "malicious"), f("intelligence", "unknown"), f("behavioral", "unknown")],
        [v("detection", "verified_consistent"), v("intelligence", "inconclusive"), v("behavioral", "inconclusive")])}
    assert scores["detection"].peer_agreement == 0.5    # nobody else voted -> neutral
    assert scores["intelligence"].peer_agreement == 0.0  # abstained


def test_suspicious_and_malicious_agree_as_threat():
    history = TrustHistory()
    t = {s.agent: s for s in TrustEvaluator(history).evaluate(
        [f("detection", "malicious"), f("intelligence", "unknown"), f("behavioral", "suspicious")],
        [v("detection", "verified_consistent"), v("intelligence", "inconclusive"), v("behavioral", "verified_consistent")])}
    assert t["detection"].peer_agreement == 1.0


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        TrustEvaluator(TrustHistory(), 0.5, 0.5, 0.5)


def test_two_stage_vote():
    findings = [f("detection", "benign"), f("intelligence", "malicious"), f("behavioral", "suspicious")]
    assert weighted_vote(findings, {"detection": 1, "intelligence": 1, "behavioral": 1}, "equal_weighted").verdict == "malicious"
    tie = weighted_vote([f("detection", "benign"), f("behavioral", "suspicious"), f("intelligence", "unknown")],
                        {"detection": 1, "intelligence": 1, "behavioral": 1}, "equal_weighted")
    assert tie.verdict == "unknown" and tie.tie


def _recommend(findings, ver, history):
    trust = TrustEvaluator(history).evaluate(findings, ver)
    return RecommendationEngine(0.6).recommend(
        event_id="e", run_id="r", phase=1, agent_models={"detection": "m"}, is_mock=False,
        findings=findings, verification_results=ver, trust_scores=trust, action_target="proto=tcp")


def test_trust_flips_equal_weighted_outcome():
    """Two low-trust agents say benign, one high-trust verified agent says malicious."""
    history = TrustHistory({"detection": 0.2, "intelligence": 0.2, "behavioral": 0.95})
    findings = [f("detection", "benign"), f("intelligence", "benign"), f("behavioral", "malicious")]
    ver = [v("detection", "verified_inconsistent"), v("intelligence", "verified_inconsistent"),
           v("behavioral", "verified_consistent")]
    rec = _recommend(findings, ver, history)
    assert rec.equal_weighted.verdict == "benign" and rec.trust_weighted.verdict == "malicious"
    assert rec.trust_changed_outcome and rec.routing == "human_review" and rec.disagreement_summary


def test_agreement_gives_simulated_action_never_executed():
    history = TrustHistory({"detection": 0.9, "intelligence": 0.9, "behavioral": 0.9})
    findings = [f("detection", "malicious"), f("intelligence", "malicious"), f("behavioral", "suspicious")]
    ver = [v(a, "verified_consistent") for a in ("detection", "intelligence", "behavioral")]
    rec = _recommend(findings, ver, history)
    assert rec.routing == "simulated_action" and rec.simulated_action.executed is False
    assert rec.simulated_action.description.startswith("Simulated")


def test_benign_routes_to_further_verification_and_failure_to_human_review():
    history = TrustHistory()
    benign = _recommend([f("detection", "benign"), f("intelligence", "unknown"), f("behavioral", "benign")],
                        [v(a, "verified_consistent") for a in ("detection", "intelligence", "behavioral")], history)
    assert benign.routing == "further_verification" and benign.simulated_action is None
    failed = _recommend([f("detection", "unknown", error="down"), f("intelligence", "unknown"), f("behavioral", "unknown")],
                        [v(a, "inconclusive") for a in ("detection", "intelligence", "behavioral")], history)
    assert failed.verdict == "unknown" and failed.routing == "human_review" and failed.confidence == "none"


def test_confidence_labels():
    assert [confidence_label(x) for x in (0.9, 0.6, 0.3, 0.0)] == ["high", "medium", "low", "none"]


def test_verdict_correctness_mapping():
    assert verdict_is_correct("suspicious", 1) and verdict_is_correct("benign", 0)
    assert verdict_is_correct("malicious", 0) is False and verdict_is_correct("unknown", 1) is None


def test_history_load_and_calibrate(tmp_path):
    class Fixed:
        def __init__(self, verdict):
            self.verdict = verdict
        def analyze(self, event):
            return f("detection", self.verdict)
    from src.models import SecurityEvent
    events = [SecurityEvent(event_id=str(i), timestamp="2026-01-01T00:00:00Z", event_type="x", raw_content="a=1",
                            metadata={"ground_truth": {"label": i % 2, "attack_cat": "x"}}) for i in range(10)]
    result = calibrate({"detection": Fixed("malicious"), "intelligence": Fixed("unknown")}, events, {})
    assert result["agents"]["detection"]["accuracy"] == 0.5
    assert result["agents"]["intelligence"]["accuracy"] is None
    path = tmp_path / "cal.json"
    path.write_text(json.dumps(result))
    history = TrustHistory.load(path, initial=0.5)
    assert history.get("detection") == 0.5 and history.get("intelligence") == 0.5
    assert TrustHistory.load(tmp_path / "missing.json", 0.3).get("behavioral") == 0.3


def test_single_uncorroborated_threat_vote_goes_to_human_review():
    from src.models import AgentFinding
    from src.recommendation.recommender import RecommendationEngine
    def f(agent, verdict):
        return AgentFinding(agent=agent, event_id="e", verdict=verdict, classification="x",
                            evidence="", confidence="high", reasoning="r")
    from src.models import TrustScore
    findings = [f("detection", "malicious"), f("intelligence", "unknown"), f("behavioral", "unknown")]
    trust = [TrustScore(agent=a, event_id="e", historical_accuracy=0.5, verification_score=0.5,
                        peer_agreement=0.5, total_score=0.5) for a in ("detection", "intelligence", "behavioral")]
    rec = RecommendationEngine(0.6).recommend(event_id="e", run_id="r", phase=1, agent_models={}, is_mock=True,
                                              findings=findings, verification_results=[], trust_scores=trust,
                                              action_target="t")
    assert rec.verdict == "malicious" and rec.routing == "human_review" and rec.simulated_action is None


def test_frontend_plain_escapes_markdown():
    from frontend.view import plain
    assert plain("[click](http://x) **b**") == "\\[click\\]\\(http://x\\) \\*\\*b\\*\\*"
