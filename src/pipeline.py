"""Wiring: build the Phase 1 (or Phase 2) pipeline from configuration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.agents.behavioral import BehavioralAgent
from src.agents.detection import DetectionAgent
from src.agents.intelligence import IntelligenceAgent
from src.agents.verification import VerificationAgent
from src.config import SystemConfig
from src.coordinator.coordinator import Coordinator
from src.recommendation.recommender import RecommendationEngine
from src.trust.trust_history import TrustHistory
from src.trust.trust_model import TrustEvaluator
from src.utils.llm_client import LLMClient, build_llm_client


def reference_paths(config: SystemConfig) -> dict:
    d = config.data_dir
    return {"ioc": d / "threat_intel" / "ioc_synthetic.json",
            "entities": d / "baselines" / "entities_synthetic.json",
            "profiles": d / "processed" / "behavioral_profiles.json",
            "signatures": d / "processed" / "intel_signatures.json"}


def build_specialists(config: SystemConfig, detection_llm: Optional[LLMClient] = None) -> dict:
    paths = reference_paths(config)
    return {"detection": DetectionAgent(detection_llm or build_llm_client(config, "detection")),
            "intelligence": IntelligenceAgent.from_file(paths["ioc"], paths["signatures"]),
            "behavioral": BehavioralAgent.from_files(paths["profiles"], paths["entities"])}


def build_coordinator(config: Optional[SystemConfig] = None, detection_llm: Optional[LLMClient] = None,
                      run_id: Optional[str] = None, history: Optional[TrustHistory] = None) -> Coordinator:
    config = config or SystemConfig.from_env()
    history = history or TrustHistory.load(config.calibration_path, config.initial_trust_score)
    trust = TrustEvaluator(history, config.trust_weight_historical, config.trust_weight_verification,
                           config.trust_weight_peer)
    run_id = run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    return Coordinator(build_specialists(config, detection_llm), VerificationAgent(), trust,
                       RecommendationEngine(config.confidence_threshold), run_id=run_id, phase=config.phase)
