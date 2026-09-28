"""Reproducible calibration and evaluation runs (writes to runs/<run_id>/)."""
from __future__ import annotations

import dataclasses
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from src.config import SystemConfig
from src.data.unsw_nb15 import load_events
from src.evaluation.metrics import compute_metrics
from src.models import SecurityEvent
from src.pipeline import build_coordinator, build_specialists
from src.trust.trust_history import calibrate


def _config_summary(config: SystemConfig, agent_models: dict) -> dict:
    data = config.model_dump(mode="json", exclude={"llm_api_key"})
    data["agent_models_effective"] = agent_models
    data["python"] = platform.python_version()
    return data


def run_calibration(config: SystemConfig, detection_llm=None, limit=None, log=print) -> Path:
    events = [SecurityEvent.model_validate(e)
              for e in load_events(config.data_dir / "processed" / "calibration_events.jsonl", limit)]
    agents = build_specialists(config, detection_llm)
    models = {name: agent.model_id for name, agent in agents.items()}
    log(f"calibrating {list(agents)} on {len(events)} validation events ...")
    result = calibrate(agents, events, _config_summary(config, models))
    path = config.calibration_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1))
    for name, info in result["agents"].items():
        log(f"  {name}: accuracy={info['accuracy']} (counted {info['counted']}, abstained {info['abstained']}, errors {info['errors']})")
    log(f"wrote {path}")
    return path


class CalibrationMissingError(RuntimeError):
    """A real (non-stub) evaluation needs measured historical accuracy."""


def run_evaluation(config: SystemConfig, detection_llm=None, limit=None, run_id=None, log=print,
                   allow_uncalibrated: bool = False) -> Path:
    real_model = detection_llm is None and config.llm_backend != "stub"
    if real_model and not allow_uncalibrated and not config.calibration_path.exists():
        raise CalibrationMissingError(
            f"No calibration file for this configuration: {config.calibration_path}\n"
            "Run `python -m src.cli calibrate` with the same model first, or pass "
            "--allow-uncalibrated to use the default trust score (not valid for reported results).")
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime(f"phase{config.phase}-%Y%m%dT%H%M%SZ")
        if detection_llm is None and config.llm_backend == "stub":
            run_id += "-STUB"
    coordinator = build_coordinator(config, detection_llm, run_id=run_id)
    run_dir = config.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    events = load_events(config.data_dir / "processed" / "eval_events.jsonl", limit)
    (run_dir / "config.json").write_text(json.dumps({
        **_config_summary(config, coordinator.agent_models),
        "trust_history_source": coordinator.trust.history.source,
        "trust_history": {a: coordinator.trust.history.get(a) for a in ("detection", "intelligence", "behavioral")},
        "eval_subset": "data/eval/phase1_eval_subset_ids.json", "n_events": len(events)}, indent=1))

    records = []
    with (run_dir / "results.jsonl").open("w", encoding="utf-8") as out:
        for index, raw in enumerate(events, 1):
            event = SecurityEvent.model_validate(raw)
            recommendation = coordinator.process_event(event)
            trace = dataclasses.asdict(coordinator.agents["detection"].last_trace)
            record = {"event_id": event.event_id, "ground_truth": event.metadata["ground_truth"],
                      "recommendation": recommendation.model_dump(mode="json"), "detection_trace": trace}
            out.write(json.dumps(record) + "\n")
            records.append(record)
            if index % 50 == 0 or index == len(events):
                log(f"  {index}/{len(events)} events")

    metrics = compute_metrics(records)
    metrics["run_id"] = run_id
    metrics["is_mock"] = any(m.startswith("stub:") for m in coordinator.agent_models.values())
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=1))
    log(format_summary(metrics))
    log(f"wrote {run_dir}")
    return run_dir


def format_summary(m: dict) -> str:
    warn = "  [STUB MODEL - NOT A QWEN RESULT]" if m.get("is_mock") else ""
    s = m["schema_valid_rate"]
    return "\n".join([
        f"run {m.get('run_id')}  n={m['n_events']}{warn}",
        f"  Macro-F1 (Detection, {len(m['macro_f1_detection']['classes'])} classes): {m['macro_f1_detection']['value']}",
        f"  Schema-valid rate: first attempt {s['first_attempt']['value']} ({s['first_attempt']['numerator']}/{s['first_attempt']['denominator']}), after retry {s['after_retry']['value']}",
        f"  Detection outcomes: " + ", ".join(f"{k} {v}" for k, v in s['outcomes'].items()),
        f"  Evidence grounding rate: {m['evidence_grounding_rate']['value']} ({m['evidence_grounding_rate']['numerator']}/{m['evidence_grounding_rate']['denominator']})",
        f"  Trust impact rate: {m['trust_impact_rate']['value']} ({m['trust_impact_rate']['numerator']}/{m['trust_impact_rate']['denominator']}); when changed: trust right {m['trust_impact_rate']['when_changed']['trust_weighted_correct']}, equal right {m['trust_impact_rate']['when_changed']['equal_weighted_correct']}",
        f"  System binary macro-F1 (secondary): {m['secondary']['system_binary_macro_f1']}",
    ])
