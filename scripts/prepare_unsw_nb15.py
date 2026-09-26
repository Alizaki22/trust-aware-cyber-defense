from pathlib import Path
import json

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "unsw_nb15"
OUTPUT_DIR = PROJECT_ROOT / "data" / "splits"

TRAIN_FILE = RAW_DIR / "UNSW_NB15_training-set.csv"
TEST_FILE = RAW_DIR / "UNSW_NB15_testing-set.csv"


# Reproducibility
RANDOM_STATE = 42


# ============================================================
# EXPECTED DATASET STRUCTURE
# ============================================================

REQUIRED_COLUMNS = [
    "id",
    "dur",
    "proto",
    "service",
    "state",
    "spkts",
    "dpkts",
    "sbytes",
    "dbytes",
    "rate",
    "sttl",
    "dttl",
    "sload",
    "dload",
    "sloss",
    "dloss",
    "sinpkt",
    "dinpkt",
    "sjit",
    "djit",
    "swin",
    "stcpb",
    "dtcpb",
    "dwin",
    "tcprtt",
    "synack",
    "ackdat",
    "smean",
    "dmean",
    "trans_depth",
    "response_body_len",
    "ct_srv_src",
    "ct_state_ttl",
    "ct_dst_ltm",
    "ct_src_dport_ltm",
    "ct_dst_sport_ltm",
    "ct_dst_src_ltm",
    "is_ftp_login",
    "ct_ftp_cmd",
    "ct_flw_http_mthd",
    "ct_src_ltm",
    "ct_srv_dst",
    "is_sm_ips_ports",
    "attack_cat",
    "label",
]


# ============================================================
# LOAD
# ============================================================

def load_dataset(path: Path) -> pd.DataFrame:

    print(f"\nLoading: {path.name}")

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    if path.stat().st_size == 0:
        raise ValueError(
            f"Dataset is empty: {path}"
        )

    df = pd.read_csv(path)

    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    return df


# ============================================================
# SCHEMA VALIDATION
# ============================================================

def validate_schema(df: pd.DataFrame):

    print("\nValidating schema...")

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing_columns)
        )

    print("Schema validation: PASSED")


# ============================================================
# CLEANING
# ============================================================

def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:

    print("\nCleaning dataset...")

    initial_rows = len(df)

    # Normalize column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove duplicate records
    duplicates = df.duplicated().sum()

    if duplicates:
        print(f"Removing duplicates: {duplicates}")
        df = df.drop_duplicates()
    else:
        print("Duplicates: 0")

    # Normalize categorical strings
    for column in [
        "proto",
        "service",
        "state",
        "attack_cat",
    ]:

        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
        )

    # Normalize label
    df["label"] = pd.to_numeric(
        df["label"],
        errors="coerce"
    )

    # Remove records with invalid labels
    invalid_labels = df["label"].isna().sum()

    if invalid_labels:
        print(
            f"Removing invalid labels: "
            f"{invalid_labels}"
        )

        df = df.dropna(
            subset=["label"]
        )

    df["label"] = df["label"].astype(int)

    # Check allowed binary labels
    invalid_binary = ~df["label"].isin([0, 1])

    if invalid_binary.any():

        count = invalid_binary.sum()

        raise ValueError(
            f"Found {count} records with "
            "invalid binary labels."
        )

    print(
        f"Rows before cleaning: {initial_rows}"
    )

    print(
        f"Rows after cleaning:  {len(df)}"
    )

    return df


# ============================================================
# LABEL VALIDATION
# ============================================================

def validate_labels(df: pd.DataFrame):

    print("\nValidating labels...")

    print("\nBinary label distribution:")

    print(
        df["label"]
        .value_counts()
        .sort_index()
    )

    print("\nAttack category distribution:")

    print(
        df["attack_cat"]
        .value_counts()
    )

    # Check normal records
    normal_categories = df.loc[
        df["label"] == 0,
        "attack_cat"
    ].unique()

    print(
        "\nCategories found for label=0:"
    )

    print(normal_categories)

    print("\nLabel validation: PASSED")


# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================

def create_splits(
    training_df: pd.DataFrame,
    testing_df: pd.DataFrame,
):

    print("\nCreating train/validation/test splits...")

    # The official UNSW-NB15 training set becomes:
    #
    # 90% -> train
    # 10% -> validation
    #
    # The official UNSW-NB15 testing set remains:
    #
    # 100% -> test

    train_df = training_df.sample(
        frac=0.90,
        random_state=RANDOM_STATE
    )

    validation_df = training_df.drop(
        train_df.index
    )

    test_df = testing_df.copy()

    print(
        f"Training:   {len(train_df)}"
    )

    print(
        f"Validation: {len(validation_df)}"
    )

    print(
        f"Test:       {len(test_df)}"
    )

    return (
        train_df.reset_index(drop=True),
        validation_df.reset_index(drop=True),
        test_df.reset_index(drop=True),
    )


# ============================================================
# DETECTION AGENT INPUT
# ============================================================

def create_detection_input(
    row: pd.Series
) -> str:

    # These are targets, not model input.
    excluded = {
        "label",
        "attack_cat",
    }

    fields = []

    for column, value in row.items():

        if column in excluded:
            continue

        fields.append(
            f"{column}={value}"
        )

    return (
        "Analyze this network security event:\n"
        + ", ".join(fields)
    )


# ============================================================
# DETECTION AGENT JSONL
# ============================================================

def create_instruction_example(
    row: pd.Series
) -> dict:

    detection_input = create_detection_input(
        row
    )

    # For the dataset ground truth:
    #
    # label = 0 -> Normal
    # label = 1 -> Attack
    #
    # attack_cat provides the attack category.

    if int(row["label"]) == 0:
        classification = "Normal"
    else:
        classification = str(
            row["attack_cat"]
        )

    return {
        "instruction": (
            "You are the Detection Agent. "
            "Analyze the network security event "
            "and determine whether it is normal "
            "or malicious. If malicious, identify "
            "the attack category."
        ),

        "input": detection_input,

        "output": json.dumps(
            {
                "classification": classification,
                "label": int(row["label"])
            },
            ensure_ascii=False
        ),
    }


# ============================================================
# SAVE JSONL
# ============================================================

def save_jsonl(
    df: pd.DataFrame,
    filename: str
):

    output_file = OUTPUT_DIR / filename

    print(
        f"\nCreating {filename}..."
    )

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
        f"Saved {len(df)} examples."
    )


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    df: pd.DataFrame,
    filename: str
):

    output_file = OUTPUT_DIR / filename

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"Saved {filename}: "
        f"{len(df)} rows"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("UNSW-NB15 DETECTION DATASET PREPARATION")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    training_df = load_dataset(
        TRAIN_FILE
    )

    testing_df = load_dataset(
        TEST_FILE
    )

    # --------------------------------------------------------
    # Validate schema
    # --------------------------------------------------------

    validate_schema(
        training_df
    )

    validate_schema(
        testing_df
    )

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    training_df = clean_dataset(
        training_df
    )

    testing_df = clean_dataset(
        testing_df
    )

    # --------------------------------------------------------
    # Validate labels
    # --------------------------------------------------------

    validate_labels(
        training_df
    )

    validate_labels(
        testing_df
    )

    # --------------------------------------------------------
    # Create splits
    # --------------------------------------------------------

    (
        train_df,
        validation_df,
        test_df,
    ) = create_splits(
        training_df,
        testing_df
    )

    # --------------------------------------------------------
    # Save CSV datasets
    # --------------------------------------------------------

    print("\nSaving processed CSV files...")

    save_csv(
        train_df,
        "train.csv"
    )

    save_csv(
        validation_df,
        "validation.csv"
    )

    save_csv(
        test_df,
        "test.csv"
    )

    # --------------------------------------------------------
    # Save Detection Agent JSONL
    # --------------------------------------------------------

    print("\nCreating Detection Agent datasets...")

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

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DAY 2 DATASET PREPARATION COMPLETE")
    print("=" * 70)

    print("\nOutput files:")

    for file in sorted(
        OUTPUT_DIR.iterdir()
    ):

        print(
            f"  {file.name} "
            f"({file.stat().st_size:,} bytes)"
        )


if __name__ == "__main__":
    main()