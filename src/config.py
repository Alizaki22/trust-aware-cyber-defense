"""System configuration (env-var driven; no secrets in code).

Environment variables (all optional):
  PHASE              1 (default) or 2
  LLM_BACKEND        "openai" (default; any OpenAI-compatible server) or "stub"
  LLM_BASE_URL       default http://localhost:8000/v1 (vLLM default)
  LLM_MODEL          default Qwen/Qwen3-4B-Instruct-2507 (locked decision #2)
  LLM_API_KEY        default "EMPTY" (local servers ignore it)
  DETECTION_MODEL    Phase 2 only: model id served for the fine-tuned Detection agent
  DATA_DIR / RUNS_DIR
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"


class SystemConfig(BaseModel):
    phase: Literal[1, 2] = 1
    llm_backend: Literal["openai", "stub"] = "openai"
    llm_base_url: str = "http://localhost:8000/v1"
    llm_model: str = BASE_MODEL_ID
    llm_api_key: str = "EMPTY"
    # Per-agent model override. Phase 1: empty (every LLM agent uses llm_model).
    # Phase 2: {"detection": "<fine-tuned model id>"} -- nothing else changes.
    agent_models: Dict[str, str] = Field(default_factory=dict)
    llm_temperature: float = 0.0
    llm_max_tokens: int = 512
    llm_timeout_s: float = 120.0
    llm_seed: Optional[int] = 42

    # Trust model (docs/PHASE1_IMPLEMENTATION.md §7)
    trust_weight_historical: float = 0.40
    trust_weight_verification: float = 0.35
    trust_weight_peer: float = 0.25
    confidence_threshold: float = 0.60
    initial_trust_score: float = 0.50

    data_dir: Path = PROJECT_ROOT / "data"
    runs_dir: Path = PROJECT_ROOT / "runs"

    def model_for(self, agent: str) -> str:
        return self.agent_models.get(agent, self.llm_model)

    @property
    def calibration_path(self) -> Path:
        model = "stub" if self.llm_backend == "stub" else self.model_for("detection")
        slug = model.replace("/", "__").replace(":", "_")
        return self.runs_dir / "calibration" / f"phase{self.phase}__{self.llm_backend}__{slug}.json"

    @classmethod
    def from_env(cls, **overrides) -> "SystemConfig":
        env = os.environ
        values: dict = {}
        if "PHASE" in env:
            values["phase"] = int(env["PHASE"])
        for key, field in [("LLM_BACKEND", "llm_backend"), ("LLM_BASE_URL", "llm_base_url"),
                           ("LLM_MODEL", "llm_model"), ("LLM_API_KEY", "llm_api_key")]:
            if env.get(key):
                values[field] = env[key]
        if env.get("DETECTION_MODEL"):
            values["agent_models"] = {"detection": env["DETECTION_MODEL"]}
        if env.get("DATA_DIR"):
            values["data_dir"] = Path(env["DATA_DIR"])
        if env.get("RUNS_DIR"):
            values["runs_dir"] = Path(env["RUNS_DIR"])
        values.update(overrides)
        return cls(**values)
