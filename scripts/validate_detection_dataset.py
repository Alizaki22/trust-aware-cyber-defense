"""
Validate the Detection Agent's train/validation/test JSONL files
produced by scripts/prepare_unsw_nb15.py.

Checks performed (see docs/ for the Day 2 requirements this covers):
  1. All three split files exist.
  2. Every record has instruction/input/output as strings, and
     output parses as JSON with classification + label.
  3. No label leakage: "label=" never appears in the input text.
  4. No attack_cat leakage: "attack_cat=" never appears in the input
     text.
  5. Detection input feature count matches the canonical feature
     list (~12-15), for every record.
  6. label is binary (0/1).
  7. No malformed / unparsable JSONL lines.
  8. No exact-duplicate records within a split.
  9. Class/label distribution is reported for each split.
"""

from pathlib import Path
import json
from collections import Counter

# Import the canonical feature list so the validator can never
# silently drift from the generator's schema.
from prepare_unsw_nb15 import DETECTION_FEATURES, TARGET_FIELDS  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "splits"


FILES = {
    "train": DATA_DIR / "train.jsonl",
    "validation": DATA_DIR / "validation.jsonl",
    "test": DATA_DIR / "test.jsonl",
}


REQUIRED_FIELDS = {"instruction", "input", "output"}
REQUIRED_OUTPUT_FIELDS = {"classification", "label"}

EXPECTED_FEATURE_COUNT = len(DETECTION_FEATURES)


def _leaks_target_fields(input_text: str) -> list[str]:
    """Return which target fields (if any) appear as `field=` in the
    Detection input text."""

    leaked = []

    for field in TARGET_FIELDS:
        if f"{field}=" in input_text:
            leaked.append(field)

    return leaked


def _feature_count(input_text: str) -> int:
    """Count how many `field=value` pairs are present in the input."""

    # Input format: "Analyze this network security event:\n" + "a=1, b=2, ..."
    body = input_text.split("\n", 1)[-1]
    if not body.strip():
        return 0
    return len(body.split(", "))


def validate_file(name, path):
    print("\n" + "=" * 70)
    print(f"VALIDATING: {name}")
    print("=" * 70)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    total = 0
    valid = 0
    invalid = 0
    leakage_violations = 0
    feature_count_violations = 0

    classifications = Counter()
    labels = Counter()
    seen_records = set()
    duplicate_count = 0

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            total += 1

            try:
                record = json.loads(line)

                missing = REQUIRED_FIELDS - set(record.keys())
                if missing:
                    print(f"Line {line_number}: missing {missing}")
                    invalid += 1
                    continue

                if not isinstance(record["instruction"], str):
                    invalid += 1
                    continue

                if not isinstance(record["input"], str):
                    invalid += 1
                    continue

                # Duplicate detection (exact record match)
                record_key = line.strip()
                if record_key in seen_records:
                    duplicate_count += 1
                else:
                    seen_records.add(record_key)

                # Leakage checks: label / attack_cat must never be in
                # the model input text.
                leaked_fields = _leaks_target_fields(record["input"])
                if leaked_fields:
                    print(
                        f"Line {line_number}: LEAKAGE of {leaked_fields} "
                        "into model input"
                    )
                    leakage_violations += 1
                    invalid += 1
                    continue

                # Feature count check
                found_features = _feature_count(record["input"])
                if found_features != EXPECTED_FEATURE_COUNT:
                    print(
                        f"Line {line_number}: expected "
                        f"{EXPECTED_FEATURE_COUNT} input features, "
                        f"found {found_features}"
                    )
                    feature_count_violations += 1
                    invalid += 1
                    continue

                # Parse output JSON
                output = json.loads(record["output"])

                if not isinstance(output, dict):
                    invalid += 1
                    continue

                missing_output = REQUIRED_OUTPUT_FIELDS - set(output.keys())
                if missing_output:
                    print(f"Line {line_number}: output missing {missing_output}")
                    invalid += 1
                    continue

                if output["label"] not in [0, 1]:
                    invalid += 1
                    continue

                classifications[output["classification"]] += 1
                labels[output["label"]] += 1

                valid += 1

            except json.JSONDecodeError:
                print(f"Line {line_number}: invalid JSON")
                invalid += 1

    print(f"\nTotal records : {total}")
    print(f"Valid records : {valid}")
    print(f"Invalid       : {invalid}")
    print(f"Leakage violations       : {leakage_violations}")
    print(f"Feature-count violations : {feature_count_violations}")
    print(f"Duplicate records         : {duplicate_count}")

    print("\nLabels:")
    for label, count in sorted(labels.items()):
        print(f"  {label}: {count}")

    print("\nClassifications:")
    for classification, count in classifications.most_common():
        print(f"  {classification}: {count}")

    passed = (
        invalid == 0
        and leakage_violations == 0
        and feature_count_violations == 0
        and duplicate_count == 0
    )

    if passed:
        print("\nSTATUS: PASSED")
    else:
        print("\nSTATUS: FAILED")

    return passed


def main():
    print("=" * 70)
    print("DETECTION DATASET VALIDATION")
    print("=" * 70)
    print(f"\nExpected Detection input features: {EXPECTED_FEATURE_COUNT}")
    print(f"Feature list: {', '.join(DETECTION_FEATURES)}")

    all_valid = True

    for name, path in FILES.items():
        try:
            result = validate_file(name, path)
        except FileNotFoundError as error:
            print(f"\n{error}")
            result = False

        if not result:
            all_valid = False

    print("\n" + "=" * 70)

    if all_valid:
        print("FINAL STATUS: ALL DATASETS VALID")
    else:
        print("FINAL STATUS: VALIDATION FAILED")

    print("=" * 70)


if __name__ == "__main__":
    main()
