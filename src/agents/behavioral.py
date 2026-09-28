"""Behavioral Analysis Agent (deterministic baseline comparison).

Baseline lookup order:
  1. entity baseline (metadata-free events with ``entity``; SYNTHETIC demo file)
  2. traffic-profile baseline keyed by (proto, service), learned from
     TRAIN-split Normal records only (data/processed/behavioral_profiles.json)
  3. otherwise abstain: verdict "unknown", "no baseline available".

A feature deviates if a numeric value is outside the baseline's
[1st, 99th] percentile range, or a categorical value (state/sttl/dttl) was
never seen in the baseline.
  >=2 deviations -> "suspicious" (medium; >=4 -> high). Never "malicious":
                    an anomaly is one input, not a final verdict.
  0-1 deviations -> "benign", confidence "low", classification
                    "within_baseline": the behavioural signal says the flow
                    looks like the normal profile.
Reporting "within baseline" as a low-confidence vote (instead of abstaining)
lets the trust mechanism decide how much this weak signal counts: its
historical accuracy is measured on the calibration subset like every other
agent's. Abstaining here left UNSW-NB15 events with at most two voters, so
every disagreement was a 1-vs-1 tie and trust could only break ties.
No baseline -> abstain ("no baseline available" is not "normal").
"""
from __future__ import annotations

import json
from pathlib import Path

from src.agents.base import BaseAgent, event_fields
from src.models import AgentFinding, SecurityEvent

SUSPICIOUS_MIN_DEVIATIONS = 2
HIGH_CONFIDENCE_DEVIATIONS = 4


def _as_float(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BehavioralAgent(BaseAgent):
    name = "behavioral"
    model_id = "rules:baseline-deviation-v1"

    def __init__(self, profiles: dict, entity_baselines: dict | None = None):
        self.profiles = profiles.get("profiles", {})
        self.entities = (entity_baselines or {}).get("entities", {})

    @classmethod
    def from_files(cls, profiles_path: Path, entities_path: Path) -> "BehavioralAgent":
        load = lambda p: json.loads(Path(p).read_text()) if Path(p).exists() else {}
        return cls(load(profiles_path), load(entities_path))

    def _baseline(self, event: SecurityEvent, fields: dict):
        if event.entity and event.entity in self.entities:
            return f"entity baseline for {event.entity}", self.entities[event.entity]
        key = f"{fields.get('proto')}|{fields.get('service')}"
        if "proto" in fields and key in self.profiles:
            return f"normal-traffic profile proto={fields['proto']}, service={fields.get('service')}", self.profiles[key]
        return None, None

    def analyze(self, event: SecurityEvent) -> AgentFinding:
        fields = event_fields(event)
        label, baseline = self._baseline(event, fields)
        if baseline is None:
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="unknown", classification="no_baseline", evidence="",
                                confidence="none",
                                reasoning="No baseline is available for this entity or traffic profile; "
                                          "no anomaly judgement is made.")
        checked, deviations = [], []
        for feature, (low, high) in baseline.get("numeric", {}).items():
            value = _as_float(fields.get(feature))
            if value is None:
                continue
            checked.append(feature)
            if value < low or value > high:
                deviations.append(feature)
        for feature, allowed in baseline.get("sets", {}).items():
            if feature not in fields:
                continue
            checked.append(feature)
            value = fields[feature]
            number = _as_float(value)
            allowed_norm = {str(_as_float(a)) if _as_float(a) is not None else a for a in allowed}
            if (str(number) if number is not None else value) not in allowed_norm:
                deviations.append(feature)
        if not checked:
            return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                                verdict="unknown", classification="no_comparable_fields", evidence="",
                                confidence="none", reasoning=f"The event has no fields covered by the {label}.")
        n = len(deviations)
        if n >= SUSPICIOUS_MIN_DEVIATIONS:
            verdict, classification = "suspicious", "baseline_deviation"
            confidence = "high" if n >= HIGH_CONFIDENCE_DEVIATIONS else "medium"
            evidence = ", ".join(f"{f}={fields[f]}" for f in deviations)
            reasoning = f"{n} of {len(checked)} checked features fall outside the {label}: {', '.join(deviations)}."
        else:
            verdict, classification, confidence = "benign", "within_baseline", "low"
            cited = [f for f in ("proto", "service", "state") if f in fields] or checked[:3]
            evidence = ", ".join(f"{f}={fields[f]}" for f in cited)
            reasoning = (f"{n} of {len(checked)} checked features fall outside the {label}. "
                         "The flow is consistent with the normal-traffic baseline; this is a weak "
                         "behavioural signal, not proof that the event is benign.")
        return AgentFinding(agent=self.name, event_id=event.event_id, model=self.model_id,
                            verdict=verdict, classification=classification, evidence=evidence,
                            confidence=confidence, reasoning=reasoning)
