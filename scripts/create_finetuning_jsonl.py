from pathlib import Path
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "data" / "fine_tuning"


def create_detection_input(row: pd.Series) -> str:
    excluded = {"label", "attack_cat"}

    fields = []

    for column, value in row.items():
        if column in excluded:
            continue

        fields.append(f"{column}={value}")

    return (
        "Analyze this network security event:\n"
        + ", ".join(fields)
    )


def create_instruction_example(row: pd.Series) -> dict:
    detection_input = create_detection_input(row)

    if int(row["label"]) == 0:
        classification = "Normal"
    else:
        classification = str(row["attack_cat"])

    return {
        "instruction": (
            "You are the Detection Agent. "
            "Analyze the network security event and determine "
            "whether it is normal or malicious. "
            "If malicious, identify the attack category."
        ),
        "input": detection_input,
        "output": json.dumps(
            {
                "classification": classification,
                "label": int(row["label"])
            },
            ensure_ascii=False
        )
    }


def save_jsonl(input_filename: str, output_filename: str):
    input_file = INPUT_DIR / input_filename
    output_file = INPUT_DIR / output_filename

    df = pd.read_csv(input_file)

    with output_file.open("w", encoding="utf-8") as file:
        for _, row in df.iterrows():
            example = create_instruction_example(row)

            file.write(
                json.dumps(
                    example,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(f"Created: {output_file}")
    print(f"Examples: {len(df):,}")


def main():
    save_jsonl("train.csv", "train.jsonl")
    save_jsonl("validation.csv", "validation.jsonl")


if __name__ == "__main__":
    main()
