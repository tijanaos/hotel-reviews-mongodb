from pathlib import Path
import ast
import json
import re
from datetime import datetime

import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "Hotel_Reviews.csv"
PROCESSED_SAMPLE_PATH = PROJECT_ROOT / "data" / "processed" / "sample_processed_reviews.jsonl"


CITIES = ["Amsterdam", "Barcelona", "London", "Milan", "Paris", "Vienna"]

COUNTRIES = [
    "Netherlands",
    "United Kingdom",
    "France",
    "Spain",
    "Italy",
    "Austria",
]

STOP_WORDS = {
    "the", "and", "was", "were", "for", "with", "that", "this", "but", "not",
    "you", "are", "had", "have", "has", "very", "all", "from", "they", "our",
    "there", "their", "would", "could", "should", "about", "just", "too",
    "into", "out", "what", "when", "where", "which", "then", "than", "been",
    "more", "some", "only", "also", "because", "your", "them", "did", "didn",
    "don", "does", "doesn", "isn", "wasn", "weren", "hotel", "room", "stay",
    "stayed", "night", "nights", "one", "two", "get", "got", "even"
}

PROBLEM_KEYWORDS = {
    "noise": [
        "noise", "noisy", "loud", "street noise", "traffic noise",
        "sound", "soundproof", "disturbing sound"
    ],
    "small_room": [
        "small room", "tiny room", "cramped", "room size",
        "smaller room", "small"
    ],
    "cleanliness": [
        "dirty", "dust", "unclean", "cleanliness", "smell", "smelly",
        "mold", "stain", "stained"
    ],
    "uncomfortable_bed": [
        "uncomfortable bed", "uncomfortable mattress", "hard bed",
        "bad bed", "mattress", "pillow"
    ],
    "wifi": [
        "wifi", "wi-fi", "internet", "connection"
    ],
    "air_conditioning": [
        "air conditioning", "air conditioner", "ac", "heating",
        "temperature", "too hot", "too cold"
    ],
    "breakfast": [
        "breakfast", "food", "coffee"
    ],
    "staff": [
        "staff", "reception", "service", "rude", "unfriendly"
    ],
}


def extract_city(address: str) -> str | None:
    for city in CITIES:
        if city.lower() in address.lower():
            return city
    return None


def extract_country(address: str) -> str | None:
    for country in COUNTRIES:
        if address.endswith(country):
            return country
    return None


def parse_review_date(value: str) -> str | None:
    try:
        parsed_date = datetime.strptime(value, "%m/%d/%Y")
        return parsed_date.date().isoformat()
    except ValueError:
        return None


def parse_days_since_review(value: str) -> int | None:
    match = re.search(r"\d+", str(value))
    if match:
        return int(match.group())
    return None


def parse_tags(value: str) -> list[str]:
    try:
        tags = ast.literal_eval(value)
        return [tag.strip() for tag in tags]
    except (ValueError, SyntaxError):
        return []


def extract_keywords(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    if text.strip().lower() == "no negative":
        return []

    words = re.findall(r"[a-zA-Z]+", text.lower())

    keywords = [
        word
        for word in words
        if len(word) > 2 and word not in STOP_WORDS
    ]

    return keywords

def contains_keyword(text: str, keyword: str) -> bool:
    pattern = r"\b" + re.escape(keyword).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None

def detect_problem_categories(negative_review: str) -> list[str]:
    if not isinstance(negative_review, str):
        return []

    if negative_review.strip().lower() == "no negative":
        return []

    text = negative_review.lower()
    detected_categories = []

    for category, keywords in PROBLEM_KEYWORDS.items():
        if any(contains_keyword(text, keyword) for keyword in keywords):
            detected_categories.append(category)

    return detected_categories


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
    negative_keywords = extract_keywords(row["Negative_Review"])
    problem_categories = detect_problem_categories(row["Negative_Review"])

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
            "negative_keywords": negative_keywords,
            "problem_categories": problem_categories,
        }
    }


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
            output_file.write(json.dumps(transformed, ensure_ascii=False) + "\n")

    print(f"\nProcessed sample saved to: {PROCESSED_SAMPLE_PATH}")

    first_transformed_row = transform_row(df.iloc[0])

    print("\nExample transformed document:")
    print(json.dumps(first_transformed_row, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()