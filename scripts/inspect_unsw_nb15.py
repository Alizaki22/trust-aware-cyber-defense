import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
UNSW_DIR = RAW_DIR / "unsw_nb15"
DEMO_FILE = RAW_DIR / "demo_dataset.csv"

TRAIN_FILE = UNSW_DIR / "UNSW_NB15_training-set.csv"
TEST_FILE = UNSW_DIR / "UNSW_NB15_testing-set.csv"


def resolve_dataset_paths(
    train_file: str | Path | None = None,
    test_file: str | Path | None = None,
):
    """Return the train/test files to inspect.

    If the UNSW-NB15 files are absent in this workspace, fall back to the
    repo's demo dataset so the script still runs and users can inspect a real
    CSV without a hard failure.
    """

    train_path = Path(train_file) if train_file else TRAIN_FILE
    test_path = Path(test_file) if test_file else TEST_FILE

    train_exists = train_path.exists() and train_path.stat().st_size > 0
    test_exists = test_path is not None and test_path.exists() and test_path.stat().st_size > 0

    if train_exists and test_exists:
        return train_path, test_path

    if train_file is None and test_file is None and DEMO_FILE.exists():
        print(
            "UNSW-NB15 files were not found or are empty. Falling back to the available demo dataset: "
            f"{DEMO_FILE}"
        )
        return DEMO_FILE, None

    if not train_exists:
        if DEMO_FILE.exists() and train_file is None and test_file is None:
            print(
                "UNSW-NB15 files were not found or are empty. Falling back to the available demo dataset: "
                f"{DEMO_FILE}"
            )
            return DEMO_FILE, None
        raise FileNotFoundError(f"Training dataset not found:\n{train_path}")

    if test_path is not None and not test_exists:
        if DEMO_FILE.exists() and train_file is None and test_file is None:
            print(
                "UNSW-NB15 files were not found or are empty. Falling back to the available demo dataset: "
                f"{DEMO_FILE}"
            )
            return DEMO_FILE, None
        raise FileNotFoundError(f"Testing dataset not found:\n{test_path}")

    if not train_path.exists():
        raise FileNotFoundError(f"Training dataset not found:\n{train_path}")

    if test_path is not None and not test_path.exists():
        raise FileNotFoundError(f"Testing dataset not found:\n{test_path}")

    return train_path, test_path


def inspect_file(path: Path):

    print("\n" + "=" * 70)
    print(f"FILE: {path.name}")
    print("=" * 70)

    df = pd.read_csv(path)

    print(f"\nRows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for column in df.columns:
        print(f"  - {column}")

    print("\nMissing values:")
    print(df.isnull().sum())

    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    print("\nLabel distribution:")

    if "label" in df.columns:
        print(df["label"].value_counts(dropna=False))

    if "attack_cat" in df.columns:
        print("\nAttack categories:")
        print(df["attack_cat"].value_counts(dropna=False))

    print("\nData types:")
    print(df.dtypes)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect a raw cybersecurity CSV dataset.",
    )
    parser.add_argument(
        "--train-file",
        type=str,
        default=None,
        help="Path to the training CSV. Defaults to the UNSW-NB15 training file if available.",
    )
    parser.add_argument(
        "--test-file",
        type=str,
        default=None,
        help="Path to the testing CSV. Defaults to the UNSW-NB15 testing file if available.",
    )
    args = parser.parse_args()

    train_file, test_file = resolve_dataset_paths(
        train_file=args.train_file,
        test_file=args.test_file,
    )

    inspect_file(train_file)

    if test_file is not None and test_file != train_file:
        inspect_file(test_file)


if __name__ == "__main__":
    main()
