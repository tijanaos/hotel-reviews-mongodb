from pathlib import Path
from collections import Counter
import ast
import json

import pandas as pd
from tqdm import tqdm

from preprocess_dataset import extract_city, extract_country, parse_tags


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "Hotel_Reviews.csv"
REPORT_PATH = PROJECT_ROOT / "docs" / "schema" / "dataset_profile.md"
JSON_REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "dataset_profile.json"


def safe_parse_tags(value: str) -> list[str]:
    try:
        tags = ast.literal_eval(value)
        return [tag.strip() for tag in tags]
    except (ValueError, SyntaxError):
        return []


def main():
    print("Profiling full dataset...")

    if not RAW_DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at: {RAW_DATASET_PATH}")
        return

    df = pd.read_csv(RAW_DATASET_PATH)

    print("Dataset loaded.")

    total_rows = len(df)
    total_columns = len(df.columns)
    unique_hotels = df["Hotel_Name"].nunique()

    df["parsed_review_date"] = pd.to_datetime(df["Review_Date"], format="%m/%d/%Y", errors="coerce")
    df["city"] = df["Hotel_Address"].apply(extract_city)
    df["country"] = df["Hotel_Address"].apply(extract_country)

    all_tags = []
    for value in tqdm(df["Tags"], desc="Parsing tags"):
        all_tags.extend(safe_parse_tags(value))

    tag_counts = Counter(all_tags)

    missing_values = df.isna().sum().to_dict()
    city_counts = df["city"].value_counts(dropna=False).to_dict()
    country_counts = df["country"].value_counts(dropna=False).to_dict()
    nationality_counts = df["Reviewer_Nationality"].str.strip().value_counts().head(20).to_dict()

    no_negative_count = (df["Negative_Review"].str.strip().str.lower() == "no negative").sum()
    no_positive_count = (df["Positive_Review"].str.strip().str.lower() == "no positive").sum()

    missing_coordinate_rows = df[["lat", "lng"]].isna().any(axis=1).sum()

    profile = {
        "total_rows": int(total_rows),
        "total_columns": int(total_columns),
        "unique_hotels": int(unique_hotels),
        "review_date_min": str(df["parsed_review_date"].min().date()),
        "review_date_max": str(df["parsed_review_date"].max().date()),
        "reviewer_score_min": float(df["Reviewer_Score"].min()),
        "reviewer_score_max": float(df["Reviewer_Score"].max()),
        "reviewer_score_avg": float(df["Reviewer_Score"].mean()),
        "average_score_avg": float(df["Average_Score"].mean()),
        "missing_coordinate_rows": int(missing_coordinate_rows),
        "no_negative_count": int(no_negative_count),
        "no_positive_count": int(no_positive_count),
        "city_counts": city_counts,
        "country_counts": country_counts,
        "top_20_reviewer_nationalities": nationality_counts,
        "top_30_tags": dict(tag_counts.most_common(30)),
        "missing_values": missing_values,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(JSON_REPORT_PATH, "w", encoding="utf-8") as json_file:
        json.dump(profile, json_file, indent=2, ensure_ascii=False)

    with open(REPORT_PATH, "w", encoding="utf-8") as report_file:
        report_file.write("# Dataset profile\n\n")

        report_file.write("## Basic information\n\n")
        report_file.write(f"- Total rows: {total_rows}\n")
        report_file.write(f"- Total columns: {total_columns}\n")
        report_file.write(f"- Unique hotels: {unique_hotels}\n")
        report_file.write(f"- Review date range: {profile['review_date_min']} - {profile['review_date_max']}\n")
        report_file.write(f"- Reviewer score range: {profile['reviewer_score_min']} - {profile['reviewer_score_max']}\n")
        report_file.write(f"- Average reviewer score: {profile['reviewer_score_avg']:.2f}\n")
        report_file.write(f"- Average hotel score: {profile['average_score_avg']:.2f}\n")
        report_file.write(f"- Rows with missing coordinates: {missing_coordinate_rows}\n")
        report_file.write(f"- Reviews without negative text: {no_negative_count}\n")
        report_file.write(f"- Reviews without positive text: {no_positive_count}\n")

        report_file.write("\n## Reviews by city\n\n")
        for city, count in city_counts.items():
            report_file.write(f"- {city}: {count}\n")

        report_file.write("\n## Reviews by country\n\n")
        for country, count in country_counts.items():
            report_file.write(f"- {country}: {count}\n")

        report_file.write("\n## Top 20 reviewer nationalities\n\n")
        for nationality, count in nationality_counts.items():
            report_file.write(f"- {nationality}: {count}\n")

        report_file.write("\n## Top 30 tags\n\n")
        for tag, count in tag_counts.most_common(30):
            report_file.write(f"- {tag}: {count}\n")

        report_file.write("\n## Missing values\n\n")
        for column, count in missing_values.items():
            report_file.write(f"- {column}: {count}\n")

    print(f"\nMarkdown report saved to: {REPORT_PATH}")
    print(f"JSON report saved to: {JSON_REPORT_PATH}")

    print("\nBasic profile:")
    print(json.dumps(profile, indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()