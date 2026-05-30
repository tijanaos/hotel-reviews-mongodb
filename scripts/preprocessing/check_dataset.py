from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "Hotel_Reviews.csv"


def main():
    print("Checking dataset...")
    print(f"Expected dataset path: {DATASET_PATH}")

    if not DATASET_PATH.exists():
        print("\nERROR: Dataset file was not found.")
        print("Please place Hotel_Reviews.csv inside data/raw/")
        return

    print("\nDataset file found.")

    df = pd.read_csv(DATASET_PATH, nrows=1000)

    print("\nFirst 1000 rows loaded successfully.")

    print("\nColumns:")
    for column in df.columns:
        print(f"- {column}")

    print("\nShape of sample:")
    print(df.shape)

    print("\nData types:")
    print(df.dtypes)

    print("\nFirst 3 rows:")
    print(df.head(3))

    print("\nMissing values in first 1000 rows:")
    print(df.isna().sum())


if __name__ == "__main__":
    main()