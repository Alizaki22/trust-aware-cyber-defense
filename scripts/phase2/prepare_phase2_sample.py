"""Phase 2 class-capped sampling for the Detection Agent fine-tuning dataset.

Class imbalance in the full training split (76,621 examples):
  Normal:          37,207  (majority)
  Exploits:        17,096
  Fuzzers:         11,533
  Reconnaissance:   5,074
  DoS:              2,752
  Analysis:           748
  Shellcode:          744
  Backdoor:           722
  Generic:            640
  Worms:              105  (rarest — kept in full)

Strategy: class_capped
  - Each class is capped at max_per_class examples (default 2,000).
  - No class is reduced below min_per_class (default 100) — protects minorities.
  - Worms has only 105 examples, which is below max; all 105 are kept.
  - Examples within each class are selected deterministically (seed 42).
  - The ORIGINAL splits in data/splits/ are NOT touched.
  - Sampled files are written to data/phase2/:
      data/phase2/train_sampled.jsonl
      data/phase2/validation_sampled.jsonl
  - A manifest is written to data/phase2/sampling_manifest.json for
    reproducibility and auditing.

Why this approach:
  - A 354x imbalance (Normal vs Worms) would cause the model to learn to
    always predict Normal, collapsing Macro-F1 (the primary Phase 2 metric).
  - Class-capping is a simple, reproducible strategy that does not destroy
    or reweight the original dataset.
  - Quality over quantity: docs/LLM_FINE_TUNING.md recommends 2,000-5,000
    high-quality examples; capping at 2,000/class gives ~9,274 train examples.
  - The full validation split is also capped for evaluation consistency.
  - The test split is NOT touched — Phase 1 and Phase 2 share the same
    frozen eval subset (data/eval/phase1_eval_subset_ids.json).

Usage (run from the repository root):
    python scripts/phase2/prepare_phase2_sample.py [--max-per-class N]

This script DOES NOT load any model and DOES NOT start training.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths and defaults
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
SPLITS_DIR = ROOT / "data" / "splits"
PHASE2_DIR = ROOT / "data" / "phase2"

DEFAULT_MAX_PER_CLASS = 2000
DEFAULT_MIN_PER_CLASS = 100
DEFAULT_SEED = 42


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def sample_split(
    records: list[dict],
    max_per_class: int,
    min_per_class: int,
    seed: int,
) -> tuple[list[dict], dict]:
    """Apply class_capped sampling to a list of instruction records.

    Returns:
        sampled:  The selected records (order may differ from original).
        summary:  Per-class counts before and after sampling.
    """
    # Group by classification
    by_class: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        try:
            cls = json.loads(rec["output"])["classification"]
        except (KeyError, json.JSONDecodeError):
            cls = "__invalid__"
        by_class[cls].append(rec)

    rng = random.Random(seed)
    sampled: list[dict] = []
    summary: dict[str, dict] = {}

    for cls in sorted(by_class):
        group = by_class[cls]
        rng.shuffle(group)
        # Cap but never drop below min_per_class
        cap = max(min_per_class, min(max_per_class, len(group)))
        selected = group[:cap]
        sampled.extend(selected)
        summary[cls] = {"before": len(group), "after": len(selected)}

    rng.shuffle(sampled)  # mix classes together (consistent with seed)
    return sampled, summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare class-capped Phase 2 training samples."
    )
    parser.add_argument(
        "--max-per-class", type=int, default=DEFAULT_MAX_PER_CLASS,
        help=f"Maximum examples per class (default: {DEFAULT_MAX_PER_CLASS})"
    )
    parser.add_argument(
        "--min-per-class", type=int, default=DEFAULT_MIN_PER_CLASS,
        help=f"Minimum examples per class — protect minorities (default: {DEFAULT_MIN_PER_CLASS})"
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})"
    )
    args = parser.parse_args()

    PHASE2_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "strategy": "class_capped",
        "max_per_class": args.max_per_class,
        "min_per_class": args.min_per_class,
        "seed": args.seed,
        "source_splits_dir": str(SPLITS_DIR),
        "splits": {},
    }

    for split_name, out_name in [
        ("train", "train_sampled.jsonl"),
        ("validation", "validation_sampled.jsonl"),
    ]:
        src_path = SPLITS_DIR / f"{split_name}.jsonl"
        dst_path = PHASE2_DIR / out_name

        if not src_path.exists():
            print(f"[SKIP] {split_name}: {src_path} not found")
            continue

        print(f"\nLoading {split_name} ({src_path.name}) …")
        records = load_jsonl(src_path)
        print(f"  Total: {len(records)} examples")

        sampled, summary = sample_split(
            records,
            max_per_class=args.max_per_class,
            min_per_class=args.min_per_class,
            seed=args.seed,
        )

        write_jsonl(dst_path, sampled)
        print(f"  Sampled: {len(sampled)} examples -> {dst_path.relative_to(ROOT)}")

        print(f"  Per-class distribution (before -> after):")
        for cls, counts in sorted(summary.items(), key=lambda x: -x[1]["before"]):
            flag = " (kept all)" if counts["before"] == counts["after"] else ""
            print(f"    {cls:<20} {counts['before']:>6} -> {counts['after']}{flag}")

        manifest["splits"][split_name] = {
            "source": str(src_path.relative_to(ROOT)),
            "output": str(dst_path.relative_to(ROOT)),
            "n_before": len(records),
            "n_after": len(sampled),
            "per_class": summary,
        }

    manifest_path = PHASE2_DIR / "sampling_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written to {manifest_path.relative_to(ROOT)}")
    print("\nDone. Pass data/phase2/train_sampled.jsonl to the training script,")
    print("or set sampling.enabled=true in configs/phase2/detection_lora.json")
    print("(the training script handles this automatically).")


if __name__ == "__main__":
    main()
