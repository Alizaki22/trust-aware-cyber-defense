#!/usr/bin/env python3
from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "splits"


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a raw cybersecurity dataframe."""

    print("\n[1/5] Cleaning data...")

    original_rows = len(df)

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Replace positive/negative infinity with NaN
    df = df.replace([np.inf, -np.inf], np.nan)

    # Strip whitespace from column names
    df.columns = [str(col).strip() for col in df.columns]

    removed = original_rows - len(df)

    print(f"Original rows : {original_rows}")
    print(f"Rows removed  : {removed}")
    print(f"Rows remaining: {len(df)}")

    return df


def find_label_column(df: pd.DataFrame) -> str | None:
    """Try to identify the dataset label column."""

    possible_labels = [
        "label",
        "Label",
        "LABEL",
        "attack",
        "Attack",
        "attack_cat",
        "Attack_cat",
        "class",
        "Class",
    ]

    for column in possible_labels:
        if column in df.columns:
            return column

    return None


def normalize_numeric_features(
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    test_df: pd.DataFrame,
    label_column: str | None,
):
    """
    Normalize numeric features.

    The scaler is fitted ONLY on the training data to prevent
    information leakage from validation/test sets.
    """

    print("\n[2/5] Normalizing numerical features...")

    excluded_columns = set()

    if label_column:
        excluded_columns.add(label_column)

    numeric_columns = train_df.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    numeric_columns = [
        column
        for column in numeric_columns
        if column not in excluded_columns
    ]

    if not numeric_columns:
        print("No numerical columns found.")
        return train_df, validation_df, test_df

    scaler = StandardScaler()

    train_df[numeric_columns] = scaler.fit_transform(
        train_df[numeric_columns]
    )

    validation_df[numeric_columns] = scaler.transform(
        validation_df[numeric_columns]
    )

    test_df[numeric_columns] = scaler.transform(
        test_df[numeric_columns]
    )

    print(f"Normalized {len(numeric_columns)} numerical features.")

    return train_df, validation_df, test_df


def convert_to_text(row: pd.Series, label_column: str | None) -> str:
    """
    Convert one tabular cybersecurity event into a textual
    representation suitable for an LLM.
    """

    fields = []

    for column, value in row.items():

        if column == label_column:
            continue

        fields.append(f"{column}={value}")

    return "Cybersecurity event: " + ", ".join(fields)


def create_instruction_example(
    row: pd.Series,
    label_column: str,
) -> dict:
    """Convert one dataframe row to instruction-tuning format."""

    label = str(row[label_column])

    input_text = convert_to_text(
        row,
        label_column,
    )

    return {
        "instruction": (
            "You are a Detection Agent. "
            "Classify the following security event."
        ),
        "input": input_text,
        "output": json.dumps(
            {
                "classification": label
            }
        ),
    }


def save_jsonl(
    df: pd.DataFrame,
    label_column: str,
    output_file: Path,
):
    """Save dataframe in instruction-tuning JSONL format."""

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        for _, row in df.iterrows():

            example = create_instruction_example(
                row,
                label_column,
            )

            file.write(
                json.dumps(
                    example,
                    ensure_ascii=False,
                )
                + "\n"
            )


# ---------------------------------------------------------
# Main preprocessing pipeline
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Prepare cybersecurity dataset."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to raw CSV dataset.",
    )

    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for processed splits.",
    )

    parser.add_argument(
        "--test-size",
        type=float,
        default=0.10,
        help="Test split percentage.",
    )

    parser.add_argument(
        "--validation-size",
        type=float,
        default=0.10,
        help="Validation split percentage.",
    )

    args = parser.parse_args()

    input_file = Path(args.input)
    output_dir = Path(args.output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("CYBERSECURITY DATASET PREPROCESSING")
    print("=" * 60)

    # -----------------------------------------------------
    # Load
    # -----------------------------------------------------

    print("\n[0/5] Loading dataset...")

    df = pd.read_csv(input_file)

    print(f"Dataset: {input_file}")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # -----------------------------------------------------
    # Clean
    # -----------------------------------------------------

    df = clean_dataframe(df)

    # -----------------------------------------------------
    # Find label
    # -----------------------------------------------------

    label_column = find_label_column(df)

    if label_column is None:

        raise ValueError(
            "Could not automatically find a label column. "
            "Please specify the correct label column."
        )

    print(f"\nDetected label column: {label_column}")

    print("\nClass distribution:")
    print(df[label_column].value_counts())

    # -----------------------------------------------------
    # Split
    # -----------------------------------------------------

    print("\n[3/5] Creating train/validation/test splits...")

    train_df, temp_df = train_test_split(
        df,
        test_size=args.test_size + args.validation_size,
        random_state=42,
        stratify=df[label_column],
    )

    validation_ratio = (
        args.validation_size
        / (args.test_size + args.validation_size)
    )

    validation_df, test_df = train_test_split(
        temp_df,
        test_size=1 - validation_ratio,
        random_state=42,
        stratify=temp_df[label_column],
    )

    print(f"Training   : {len(train_df)}")
    print(f"Validation : {len(validation_df)}")
    print(f"Test       : {len(test_df)}")

    # -----------------------------------------------------
    # Normalize
    # -----------------------------------------------------

    train_df, validation_df, test_df = normalize_numeric_features(
        train_df,
        validation_df,
        test_df,
        label_column,
    )

    # -----------------------------------------------------
    # Save CSV splits
    # -----------------------------------------------------

    print("\n[4/5] Saving CSV splits...")

    train_df.to_csv(
        output_dir / "train.csv",
        index=False,
    )

    validation_df.to_csv(
        output_dir / "validation.csv",
        index=False,
    )

    test_df.to_csv(
        output_dir / "test.csv",
        index=False,
    )

    # -----------------------------------------------------
    # Instruction format
    # -----------------------------------------------------

    print("\n[5/5] Creating instruction-tuning datasets...")

    save_jsonl(
        train_df,
        label_column,
        output_dir / "train.jsonl",
    )

    save_jsonl(
        validation_df,
        label_column,
        output_dir / "validation.jsonl",
    )

    save_jsonl(
        test_df,
        label_column,
        output_dir / "test.jsonl",
    )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)

    print(f"\nOutput directory:")
    print(output_dir)

    print("\nFiles created:")

    for file in sorted(output_dir.iterdir()):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()
