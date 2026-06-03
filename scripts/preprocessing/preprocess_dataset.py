from pathlib import Path
import ast
import json
from datetime import datetime

import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "Hotel_Reviews.csv"
PROCESSED_SAMPLE_PATH = PROJECT_ROOT / "data" / "processed" / "sample_processed_reviews.jsonl"


COUNTRY_TO_CITY = {
    "Netherlands": "Amsterdam",
    "United Kingdom": "London",
    "France": "Paris",
    "Spain": "Barcelona",
    "Italy": "Milan",
    "Austria": "Vienna",
}

COUNTRIES = list(COUNTRY_TO_CITY.keys())

def extract_country(address: str) -> str | None:
    if not isinstance(address, str):
        return None

    normalized_address = address.strip()

    for country in COUNTRIES:
        if normalized_address.endswith(country):
            return country

    return None


def extract_city(address: str) -> str | None:
    country = extract_country(address)

    if country is None:
        return None

    return COUNTRY_TO_CITY[country]


def parse_review_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return None


def parse_days_since_review(value: str) -> int | None:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if digits:
        return int(digits)
    return None


def parse_tags(value: str) -> list[str]:
    try:
        tags = ast.literal_eval(value)
        return [tag.strip() for tag in tags]
    except (ValueError, SyntaxError):
        return []


def transform_row(row: pd.Series) -> dict:
    city = extract_city(row["Hotel_Address"])
    country = extract_country(row["Hotel_Address"])

    lat = row["lat"]
    lng = row["lng"]

    location = None
    if pd.notna(lat) and pd.notna(lng):
        location = {
            "type": "Point",
            "coordinates": [float(lng), float(lat)]
        }

    review_date = parse_review_date(row["Review_Date"])
    tags = parse_tags(row["Tags"])

    return {
        "hotel": {
            "name": row["Hotel_Name"],
            "address": row["Hotel_Address"],
            "city": city,
            "country": country,
            "average_score": float(row["Average_Score"]),
            "total_number_of_reviews": int(row["Total_Number_of_Reviews"]),
            "additional_number_of_scoring": int(row["Additional_Number_of_Scoring"]),
            "location": location,
        },
        "review": {
            "review_date": review_date,
            "reviewer_nationality": row["Reviewer_Nationality"].strip(),
            "negative_review": row["Negative_Review"],
            "positive_review": row["Positive_Review"],
            "negative_word_count": int(row["Review_Total_Negative_Word_Counts"]),
            "positive_word_count": int(row["Review_Total_Positive_Word_Counts"]),
            "reviewer_score": float(row["Reviewer_Score"]),
            "reviewer_total_reviews": int(row["Total_Number_of_Reviews_Reviewer_Has_Given"]),
            "tags": tags,
            "days_since_review": parse_days_since_review(row["days_since_review"]),
        }
    }


def serialize_for_json(value):
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main():
    print("Preprocessing sample dataset...")

    if not RAW_DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at: {RAW_DATASET_PATH}")
        return

    df = pd.read_csv(RAW_DATASET_PATH, nrows=1000)

    PROCESSED_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(PROCESSED_SAMPLE_PATH, "w", encoding="utf-8") as output_file:
        for _, row in tqdm(df.iterrows(), total=len(df)):
            transformed = transform_row(row)
            output_file.write(
                json.dumps(transformed, ensure_ascii=False, default=serialize_for_json) + "\n"
            )

    print(f"\nProcessed sample saved to: {PROCESSED_SAMPLE_PATH}")

    first_transformed_row = transform_row(df.iloc[0])

    print("\nExample transformed document:")
    print(json.dumps(first_transformed_row, indent=2, ensure_ascii=False, default=serialize_for_json))


if __name__ == "__main__":
    main()
