from pathlib import Path
import json
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "splits"


FILES = {
    "train": DATA_DIR / "train.jsonl",
    "validation": DATA_DIR / "validation.jsonl",
    "test": DATA_DIR / "test.jsonl",
}


REQUIRED_FIELDS = {
    "instruction",
    "input",
    "output",
}


def validate_file(name, path):

    print("\n" + "=" * 70)
    print(f"VALIDATING: {name}")
    print("=" * 70)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    total = 0
    valid = 0
    invalid = 0

    classifications = Counter()
    labels = Counter()

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1
        ):

            total += 1

            try:
                record = json.loads(line)

                # Check top-level fields
                missing = (
                    REQUIRED_FIELDS
                    - set(record.keys())
                )

                if missing:
                    print(
                        f"Line {line_number}: "
                        f"missing {missing}"
                    )
                    invalid += 1
                    continue

                # Check text fields
                if not isinstance(
                    record["instruction"],
                    str
                ):
                    invalid += 1
                    continue

                if not isinstance(
                    record["input"],
                    str
                ):
                    invalid += 1
                    continue

                # Parse output JSON
                output = json.loads(
                    record["output"]
                )

                if not isinstance(
                    output,
                    dict
                ):
                    invalid += 1
                    continue

                # Required output fields
                if "classification" not in output:
                    invalid += 1
                    continue

                if "label" not in output:
                    invalid += 1
                    continue

                # Validate label
                if output["label"] not in [0, 1]:
                    invalid += 1
                    continue

                classifications[
                    output["classification"]
                ] += 1

                labels[
                    output["label"]
                ] += 1

                valid += 1

            except json.JSONDecodeError:
                print(
                    f"Line {line_number}: "
                    "invalid JSON"
                )
                invalid += 1

    print(f"\nTotal records : {total}")
    print(f"Valid records : {valid}")
    print(f"Invalid       : {invalid}")

    print("\nLabels:")

    for label, count in sorted(
        labels.items()
    ):
        print(
            f"  {label}: {count}"
        )

    print("\nClassifications:")

    for classification, count in (
        classifications.most_common()
    ):
        print(
            f"  {classification}: {count}"
        )

    if invalid == 0:
        print("\nSTATUS: PASSED")
    else:
        print("\nSTATUS: FAILED")

    return invalid == 0


def main():

    print("=" * 70)
    print("DETECTION DATASET VALIDATION")
    print("=" * 70)

    all_valid = True

    for name, path in FILES.items():

        result = validate_file(
            name,
            path
        )

        if not result:
            all_valid = False

    print("\n" + "=" * 70)

    if all_valid:
        print(
            "FINAL STATUS: ALL DATASETS VALID"
        )
    else:
        print(
            "FINAL STATUS: VALIDATION FAILED"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()
