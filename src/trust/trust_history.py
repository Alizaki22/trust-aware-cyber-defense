"""Historical accuracy (trust factor 1).

Measured, not assumed: each agent is run on the frozen calibration subset
(validation split, never the test split) and its binary correctness is
recorded: malicious/suspicious -> attack, benign -> normal; "unknown" and
failed findings are abstentions and are not counted. Agents with no
non-abstaining calibration findings keep the configured initial score.
The file is per phase + detection model, so Phase 2 re-calibrates.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ATTACK_VERDICTS = {"malicious", "suspicious"}


def verdict_is_correct(verdict: str, label: int) -> Optional[bool]:
    """None = abstention (unknown)."""
    if verdict in ATTACK_VERDICTS:
        return label == 1
    if verdict == "benign":
        return label == 0
    return None


class TrustHistory:
    def __init__(self, accuracy: dict[str, float] | None = None, initial: float = 0.5, source: str = "default"):
        self.accuracy = dict(accuracy or {})
        self.initial = initial
        self.source = source

    def get(self, agent: str) -> float:
        return self.accuracy.get(agent, self.initial)

    @classmethod
    def load(cls, path: Path, initial: float = 0.5) -> "TrustHistory":
        if not Path(path).exists():
            return cls(initial=initial, source=f"initial_trust_score={initial} (no calibration file)")
        data = json.loads(Path(path).read_text())
        accuracy = {agent: info["accuracy"] for agent, info in data["agents"].items() if info["accuracy"] is not None}
        return cls(accuracy, initial, source=str(path))


def calibrate(agents: dict, events: list, config_summary: dict) -> dict:
    """Run each specialist agent on the calibration events and measure accuracy."""
    stats = {name: {"correct": 0, "counted": 0, "abstained": 0, "errors": 0} for name in agents}
    for event in events:
        label = event.metadata["ground_truth"]["label"]
        for name, agent in agents.items():
            finding = agent.analyze(event)
            if finding.error:
                stats[name]["errors"] += 1
            outcome = None if finding.error else verdict_is_correct(finding.verdict, label)
            if outcome is None:
                stats[name]["abstained"] += 1
                continue
            stats[name]["counted"] += 1
            stats[name]["correct"] += int(outcome)
    agents_out = {}
    for name, s in stats.items():
        accuracy = round(s["correct"] / s["counted"], 4) if s["counted"] else None
        agents_out[name] = {"accuracy": accuracy, **s}
    return {"created_at": datetime.now(timezone.utc).isoformat(), "n_events": len(events),
            "definition": "binary accuracy over non-abstaining findings on the calibration subset",
            "config": config_summary, "agents": agents_out}
