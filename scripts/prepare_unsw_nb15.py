from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
UNSW_DIR = RAW_DIR / "unsw_nb15"
DEMO_FILE = RAW_DIR / "demo_dataset.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "splits"

TRAIN_FILE = UNSW_DIR / "UNSW_NB15_training-set.csv"
TEST_FILE = UNSW_DIR / "UNSW_NB15_testing-set.csv"


RANDOM_STATE = 42


def load_dataset_inputs():
    """Load UNSW files when available, otherwise fall back to the repo demo data."""
    if TRAIN_FILE.exists() and TEST_FILE.exists():
        train_df = pd.read_csv(TRAIN_FILE)
        test_df = pd.read_csv(TEST_FILE)
        return train_df, test_df

    if DEMO_FILE.exists():
        print(
            "UNSW-NB15 raw files were not found. Falling back to the repository demo dataset: "
            f"{DEMO_FILE}"
        )
        demo_df = pd.read_csv(DEMO_FILE)
        return demo_df.copy(), demo_df.copy()

    raise FileNotFoundError(
        "Missing UNSW-NB15 files and no demo dataset was found. "
        f"Expected: {TRAIN_FILE} and {TEST_FILE}"
    )


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    print("Cleaning dataset...")

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Replace infinity values
    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Remove duplicate records
    df = df.drop_duplicates()

    return df


def clean_labels(df: pd.DataFrame) -> pd.DataFrame:

    if "label" not in df.columns:
        raise ValueError("Required column 'label' was not found.")

    label_mapping = {
        "normal": 0,
        "benign": 0,
        "safe": 0,
        "0": 0,
        "false": 0,
        "malicious": 1,
        "attack": 1,
        "anomaly": 1,
        "1": 1,
        "true": 1,
    }

    normalized_label = df["label"].astype(str).str.strip().str.lower()
    numeric_label = normalized_label.map(label_mapping)

    if numeric_label.isna().any():
        fallback_numeric = pd.to_numeric(df["label"], errors="coerce")
        numeric_label = numeric_label.fillna(fallback_numeric)

    df["label"] = numeric_label

    # Remove rows with invalid labels
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    if "attack_cat" not in df.columns:
        df["attack_cat"] = np.where(
            df["label"].astype(int) == 1,
            "Malicious",
            "Normal",
        )
    else:
        df["attack_cat"] = (
            df["attack_cat"]
            .fillna("Normal")
            .astype(str)
            .str.strip()
        )

    return df


def print_statistics(
    name: str,
    df: pd.DataFrame
):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(f"Rows: {len(df)}")

    print("\nBinary label:")
    print(
        df["label"]
        .value_counts()
        .sort_index()
    )

    if "attack_cat" in df.columns:
        print("\nAttack categories:")
        print(
            df["attack_cat"]
            .value_counts()
        )


def create_detection_input(
    row: pd.Series
) -> str:

    excluded = {
        "label",
        "attack_cat",
    }

    fields = []

    for column, value in row.items():

        if column in excluded:
            continue

        if pd.isna(value):
            value = "unknown"

        fields.append(
            f"{column}={value}"
        )

    return (
        "Analyze the following network "
        "security event:\n"
        + ", ".join(fields)
    )


def create_instruction_example(
    row: pd.Series
) -> dict:

    detection_input = create_detection_input(
        row
    )

    attack_category = (
        str(row["attack_cat"]) if "attack_cat" in row.index else "Normal"
    )

    label = int(row["label"])

    return {
        "instruction": (
            "You are the Detection Agent. "
            "Analyze the network security event "
            "and classify whether it is normal or "
            "malicious. If malicious, identify the "
            "attack category."
        ),

        "input": detection_input,

        "output": json.dumps(
            {
                "classification": attack_category,
                "label": label
            },
            ensure_ascii=False
        )
    }


def save_jsonl(
    df: pd.DataFrame,
    filename: str
):

    output_file = OUTPUT_DIR / filename

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        for _, row in df.iterrows():

            example = create_instruction_example(
                row
            )

            file.write(
                json.dumps(
                    example,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(
        f"Saved {len(df)} examples -> "
        f"{output_file}"
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("Loading dataset...")
    official_train, official_test = load_dataset_inputs()

    print_statistics(
        "RAW TRAINING DATA",
        official_train
    )

    print_statistics(
        "RAW TEST DATA",
        official_test
    )

    # Clean
    official_train = clean_dataframe(
        official_train
    )

    official_test = clean_dataframe(
        official_test
    )

    # Clean labels
    official_train = clean_labels(
        official_train
    )

    official_test = clean_labels(
        official_test
    )

    print_statistics(
        "CLEANED TRAINING DATA",
        official_train
    )

    print_statistics(
        "CLEANED TEST DATA",
        official_test
    )

    # -----------------------------------------------------
    # Create validation set from training data
    # -----------------------------------------------------

    train_df, validation_df = train_test_split(
        official_train,
        test_size=0.10,
        random_state=RANDOM_STATE,
        stratify=official_train["label"]
    )

    test_df = official_test.copy()

    print_statistics(
        "FINAL TRAIN",
        train_df
    )

    print_statistics(
        "FINAL VALIDATION",
        validation_df
    )

    print_statistics(
        "FINAL TEST",
        test_df
    )

    # -----------------------------------------------------
    # Save CSV files
    # -----------------------------------------------------

    train_df.to_csv(
        OUTPUT_DIR / "train.csv",
        index=False
    )

    validation_df.to_csv(
        OUTPUT_DIR / "validation.csv",
        index=False
    )

    test_df.to_csv(
        OUTPUT_DIR / "test.csv",
        index=False
    )

    # -----------------------------------------------------
    # Save JSONL instruction datasets
    # -----------------------------------------------------

    save_jsonl(
        train_df,
        "train.jsonl"
    )

    save_jsonl(
        validation_df,
        "validation.jsonl"
    )

    save_jsonl(
        test_df,
        "test.jsonl"
    )

    print("\nDataset preparation complete.")


if __name__ == "__main__":
    main()
