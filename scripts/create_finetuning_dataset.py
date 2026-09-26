from pathlib import Path
import pandas as pd

RANDOM_STATE = 42
SAMPLES_PER_CLASS = 400

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "splits" / "train.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "fine_tuning"
OUTPUT_FILE = OUTPUT_DIR / "train_balanced.csv"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_FILE)

    sampled_parts = []

    for attack_class, group in df.groupby("attack_cat"):
        sample_size = min(SAMPLES_PER_CLASS, len(group))

        sampled = group.sample(
            n=sample_size,
            random_state=RANDOM_STATE
        )

        sampled_parts.append(sampled)

    balanced_df = pd.concat(
        sampled_parts,
        ignore_index=True
    )

    balanced_df = balanced_df.sample(
        frac=1,
        random_state=RANDOM_STATE
    ).reset_index(drop=True)

    balanced_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("=" * 60)
    print("BALANCED FINE-TUNING DATASET")
    print("=" * 60)
    print(f"Input rows:  {len(df):,}")
    print(f"Output rows: {len(balanced_df):,}")
    print()
    print("Class distribution:")
    print(balanced_df["attack_cat"].value_counts().sort_index())
    print()
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
