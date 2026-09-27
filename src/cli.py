"""Phase 1 command line.  Usage:  python -m src.cli <command> [--backend stub]

  prepare-data   build splits, baselines and frozen subsets from data/raw/unsw_nb15/
  validate-data  gate: validate data/splits/*.jsonl (exit 1 on any failure)
  check-llm      one request to the configured model server
  calibrate      measure per-agent historical accuracy on the calibration subset
  evaluate       run the pipeline on the frozen eval subset and compute the 4 metrics
  analyze        run one event (JSON file, or --demo N) and print the FinalRecommendation
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import SystemConfig


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.cli")
    parser.add_argument("--backend", choices=["openai", "stub"], help="override LLM_BACKEND")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare-data")
    sub.add_parser("validate-data")
    sub.add_parser("check-llm")
    for name in ("calibrate", "evaluate"):
        p = sub.add_parser(name)
        p.add_argument("--limit", type=int, help="only the first N events (smoke runs)")
        if name == "evaluate":
            p.add_argument("--run-id")
    p = sub.add_parser("analyze")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--event", type=Path)
    group.add_argument("--demo", type=int, help="index into data/events/demo_events.json")
    args = parser.parse_args(argv)

    config = SystemConfig.from_env(**({"llm_backend": args.backend} if args.backend else {}))

    if args.command == "prepare-data":
        from src.data.unsw_nb15 import prepare
        prepare(config.data_dir)
        return 0
    if args.command == "validate-data":
        from src.data.unsw_nb15 import validate_split_files
        ok = validate_split_files(config.data_dir / "splits")
        print("ALL DATASETS VALID" if ok else "VALIDATION FAILED")
        return 0 if ok else 1
    if args.command == "check-llm":
        from src.utils.llm_client import LLMError, build_llm_client
        client = build_llm_client(config)
        try:
            print(f"{client.model_id} @ {config.llm_base_url}: {client.generate('Reply with OK.', 'ping')[:80]!r}")
        except LLMError as error:
            print(f"LLM check failed: {error}")
            return 1
        return 0
    if args.command == "calibrate":
        from src.evaluation.runner import run_calibration
        run_calibration(config, limit=args.limit)
        return 0
    if args.command == "evaluate":
        from src.evaluation.runner import run_evaluation
        run_evaluation(config, limit=args.limit, run_id=args.run_id)
        return 0
    if args.command == "analyze":
        from src.api import analyze_event
        from src.pipeline import build_coordinator
        event = (json.loads(args.event.read_text()) if args.event else
                 json.loads((config.data_dir / "events" / "demo_events.json").read_text())[args.demo])
        print(analyze_event(event, build_coordinator(config)).model_dump_json(indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
