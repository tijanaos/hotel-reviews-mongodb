from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import ast
from datetime import datetime
import os
import re

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "Hotel_Reviews.csv"

COUNTRY_TO_CITY = {
    "Netherlands": "Amsterdam",
    "United Kingdom": "London",
    "France": "Paris",
    "Spain": "Barcelona",
    "Italy": "Milan",
    "Austria": "Vienna",
}

COUNTRIES = list(COUNTRY_TO_CITY.keys())

NEGATIVE_STOP_WORDS = {
    "the",
    "and",
    "for",
    "was",
    "were",
    "with",
    "that",
    "this",
    "from",
    "have",
    "had",
    "but",
    "not",
    "too",
    "very",
    "all",
    "our",
    "you",
    "your",
    "are",
    "just",
    "they",
    "them",
    "there",
    "then",
    "than",
    "into",
    "about",
    "after",
    "before",
    "because",
    "been",
    "being",
    "out",
    "off",
    "did",
    "didnt",
    "dont",
    "cant",
    "could",
    "would",
    "should",
    "again",
    "only",
    "more",
    "most",
    "some",
    "much",
    "many",
    "few",
    "lot",
    "lots",
    "one",
    "two",
    "three",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "what",
    "why",
    "how",
    "hotel",
    "room",
    "rooms",
    "also",
    "like",
    "even",
    "can",
    "little",
    "small",
    "around",
    "will",
    "didn",
    "bit",
    "nice",
}


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


def parse_tags(value: str) -> list[str]:
    try:
        tags = ast.literal_eval(value)
        return [tag.strip() for tag in tags if str(tag).strip()]
    except (ValueError, SyntaxError):
        return []


def extract_negative_keywords(negative_review: str) -> list[str]:
    if not isinstance(negative_review, str):
        return []

    normalized = negative_review.strip().lower()
    if not normalized or normalized == "no negative":
        return []

    tokens = re.findall(r"[a-zA-Z']+", normalized)

    keywords = []
    for token in tokens:
        cleaned = token.replace("'", "").strip()
        if len(cleaned) < 3:
            continue
        if cleaned in NEGATIVE_STOP_WORDS:
            continue
        keywords.append(cleaned)

    # Preserve order while removing duplicates inside a single review.
    return list(dict.fromkeys(keywords))


def create_v2_hotel_document(row) -> dict:
    country = extract_country(row["Hotel_Address"])
    city = extract_city(row["Hotel_Address"])

    lat = row["lat"]
    lng = row["lng"]

    location = None
    if pd.notna(lat) and pd.notna(lng):
        location = {
            "type": "Point",
            "coordinates": [float(lng), float(lat)],
        }

    return {
        "name": str(row["Hotel_Name"]).strip(),
        "address": str(row["Hotel_Address"]).strip(),
        "city": city,
        "country": country,
        "average_score": float(row["Average_Score"]),
        "total_number_of_reviews": int(row["Total_Number_of_Reviews"]),
        "additional_number_of_scoring": int(row["Additional_Number_of_Scoring"]),
        "location": location,
    }


def create_v2_review_document(row, hotel_id) -> dict:
    hotel_name = str(row["Hotel_Name"]).strip()
    review_date = parse_review_date(row["Review_Date"])
    negative_review = str(row["Negative_Review"]).strip()

    return {
        "hotel_id": hotel_id,
        "hotel_name": hotel_name,
        "review_date": review_date,
        "review_year": review_date.year if review_date else None,
        "review_month": review_date.month if review_date else None,
        "reviewer_score": float(row["Reviewer_Score"]),
        "reviewer_nationality": str(row["Reviewer_Nationality"]).strip(),
        "negative_review": negative_review,
        "negative_keywords": extract_negative_keywords(negative_review),
        "tags": parse_tags(row["Tags"]),
    }


def build_time_stats(df: pd.DataFrame) -> list[dict]:
    monthly_stats = (
        df.dropna(subset=["review_year", "review_month"])
        .groupby(["hotel_id", "hotel_name", "review_year", "review_month"], as_index=False)
        .agg(avg_score=("reviewer_score", "mean"), review_count=("reviewer_score", "size"))
    )

    yearly_stats = (
        df.dropna(subset=["review_year"])
        .groupby(["hotel_id", "hotel_name", "review_year"], as_index=False)
        .agg(avg_score=("reviewer_score", "mean"), review_count=("reviewer_score", "size"))
    )

    documents = []

    for row in monthly_stats.itertuples(index=False):
        documents.append(
            {
                "hotel_id": row.hotel_id,
                "hotel_name": row.hotel_name,
                "period_type": "month",
                "year": int(row.review_year),
                "month": int(row.review_month),
                "avg_score": round(float(row.avg_score), 4),
                "review_count": int(row.review_count),
            }
        )

    for row in yearly_stats.itertuples(index=False):
        documents.append(
            {
                "hotel_id": row.hotel_id,
                "hotel_name": row.hotel_name,
                "period_type": "year",
                "year": int(row.review_year),
                "month": None,
                "avg_score": round(float(row.avg_score), 4),
                "review_count": int(row.review_count),
            }
        )

    return documents


def build_top_tags_by_year(df: pd.DataFrame) -> list[dict]:
    high_score_df = df[
        (df["reviewer_score"] > 8.5)
        & (df["review_year"].notna())
        & (df["tags"].map(bool))
    ]

    tag_counts: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in high_score_df.itertuples(index=False):
        key = (row.hotel_id, row.hotel_name, int(row.review_year))
        for tag in row.tags:
            tag_counts[key][tag] += 1

    documents = []
    for (hotel_id, hotel_name, year), counts in tag_counts.items():
        sorted_tags = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        documents.append(
            {
                "hotel_id": hotel_id,
                "hotel_name": hotel_name,
                "year": year,
                "top_tags": [
                    {"tag": tag, "count": count}
                    for tag, count in sorted_tags[:10]
                ],
            }
        )

    return documents


def build_nationality_year_stats(df: pd.DataFrame) -> list[dict]:
    nationality_df = df[
        df["review_year"].notna()
        & df["reviewer_nationality"].notna()
        & (df["reviewer_nationality"] != "")
    ].copy()

    grouped = (
        nationality_df.groupby(
            ["hotel_id", "hotel_name", "review_year", "reviewer_nationality"],
            as_index=False,
        )
        .agg(
            avg_score=("reviewer_score", "mean"),
            review_count=("reviewer_score", "size"),
            high_score_count=("reviewer_score", lambda scores: int((scores > 8.5).sum())),
            low_score_count=("reviewer_score", lambda scores: int((scores < 5).sum())),
        )
    )

    documents = []
    for row in grouped.itertuples(index=False):
        documents.append(
            {
                "hotel_id": row.hotel_id,
                "hotel_name": row.hotel_name,
                "year": int(row.review_year),
                "nationality": row.reviewer_nationality,
                "avg_score": round(float(row.avg_score), 4),
                "review_count": int(row.review_count),
                "high_score_count": int(row.high_score_count),
                "low_score_count": int(row.low_score_count),
            }
        )

    return documents


def haversine_distance_meters(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> float:
    from math import asin, cos, radians, sin, sqrt

    earth_radius_m = 6371000

    lon1_rad = radians(lon1)
    lat1_rad = radians(lat1)
    lon2_rad = radians(lon2)
    lat2_rad = radians(lat2)

    delta_lon = lon2_rad - lon1_rad
    delta_lat = lat2_rad - lat1_rad

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c


def build_nearby_hotel_trends(
    hotels_df: pd.DataFrame, time_stats_df: pd.DataFrame, top_n: int = 10
) -> list[dict]:
    monthly_stats_df = time_stats_df[time_stats_df["period_type"] == "month"].copy()
    monthly_stats_by_hotel: dict = defaultdict(list)

    for row in monthly_stats_df.itertuples(index=False):
        monthly_stats_by_hotel[row.hotel_id].append(
            {
                "year": int(row.year),
                "month": int(row.month),
                "avg_score": float(row.avg_score),
                "review_count": int(row.review_count),
            }
        )

    hotels_with_location = []
    for row in hotels_df.to_dict("records"):
        location = row["location"]
        if not location or "coordinates" not in location:
            continue
        coordinates = location["coordinates"]
        if not coordinates or len(coordinates) != 2:
            continue

        hotels_with_location.append(
            {
                "hotel_id": row["_id"],
                "hotel_name": row["name"],
                "average_score": float(row["average_score"]),
                "coordinates": coordinates,
            }
        )

    documents = []

    for anchor_hotel in hotels_with_location:
        anchor_lon, anchor_lat = anchor_hotel["coordinates"]
        distances = []

        for nearby_hotel in hotels_with_location:
            if nearby_hotel["hotel_id"] == anchor_hotel["hotel_id"]:
                continue

            nearby_lon, nearby_lat = nearby_hotel["coordinates"]
            distance_meters = haversine_distance_meters(
                anchor_lon, anchor_lat, nearby_lon, nearby_lat
            )
            distances.append((distance_meters, nearby_hotel))

        distances.sort(key=lambda item: item[0])

        for distance_meters, nearby_hotel in distances[:top_n]:
            for monthly_stat in monthly_stats_by_hotel.get(nearby_hotel["hotel_id"], []):
                documents.append(
                    {
                        "anchor_hotel_id": anchor_hotel["hotel_id"],
                        "anchor_hotel_name": anchor_hotel["hotel_name"],
                        "nearby_hotel_id": nearby_hotel["hotel_id"],
                        "nearby_hotel_name": nearby_hotel["hotel_name"],
                        "distance_meters": round(distance_meters, 2),
                        "hotel_average_score": nearby_hotel["average_score"],
                        "year": monthly_stat["year"],
                        "month": monthly_stat["month"],
                        "avg_score": round(monthly_stat["avg_score"], 4),
                        "review_count": monthly_stat["review_count"],
                    }
                )

    return documents


def main():
    print("Importing v2 data...")

    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at: {DATASET_PATH}")
        return

    load_dotenv(PROJECT_ROOT / ".env")

    username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    database_name = os.getenv("MONGO_DATABASE", "hotel_reviews")

    connection_string = f"mongodb://{username}:{password}@localhost:27017/?authSource=admin"

    client = MongoClient(connection_string)
    db = client[database_name]

    v2_hotels = db["v2_hotels"]
    v2_reviews = db["v2_reviews"]
    v2_hotel_time_stats = db["v2_hotel_time_stats"]
    v2_top_tags_by_year = db["v2_top_tags_by_year"]
    v2_nationality_year_stats = db["v2_nationality_year_stats"]
    v2_nearby_hotel_trends = db["v2_nearby_hotel_trends"]

    v2_hotels.drop()
    v2_reviews.drop()
    v2_hotel_time_stats.drop()
    v2_top_tags_by_year.drop()
    v2_nationality_year_stats.drop()
    v2_nearby_hotel_trends.drop()

    df = pd.read_csv(DATASET_PATH)

    hotel_ids_by_key = {}
    seen_hotel_keys = set()
    hotels_to_insert = []

    print("Preparing v2_hotels...")

    for _, row in tqdm(df.iterrows(), total=len(df)):
        hotel_key = (
            str(row["Hotel_Name"]).strip(),
            str(row["Hotel_Address"]).strip(),
        )
        if hotel_key in seen_hotel_keys:
            continue

        seen_hotel_keys.add(hotel_key)
        hotels_to_insert.append((hotel_key, create_v2_hotel_document(row)))

    inserted_hotels = v2_hotels.insert_many([hotel for _, hotel in hotels_to_insert])

    for index, inserted_id in enumerate(inserted_hotels.inserted_ids):
        hotel_ids_by_key[hotels_to_insert[index][0]] = inserted_id

    hotel_documents_for_aggregates = []
    for index, inserted_id in enumerate(inserted_hotels.inserted_ids):
        hotel_document = dict(hotels_to_insert[index][1])
        hotel_document["_id"] = inserted_id
        hotel_documents_for_aggregates.append(hotel_document)

    print("Preparing v2_reviews...")

    review_batch = []
    review_batch_size = 5000
    review_rows_for_aggregates = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        hotel_key = (
            str(row["Hotel_Name"]).strip(),
            str(row["Hotel_Address"]).strip(),
        )
        hotel_id = hotel_ids_by_key[hotel_key]

        review_document = create_v2_review_document(row, hotel_id)
        review_batch.append(review_document)
        review_rows_for_aggregates.append(review_document)

        if len(review_batch) == review_batch_size:
            v2_reviews.insert_many(review_batch)
            review_batch.clear()

    if review_batch:
        v2_reviews.insert_many(review_batch)

    aggregates_df = pd.DataFrame(review_rows_for_aggregates)

    print("Preparing v2_hotel_time_stats...")
    time_stat_documents = build_time_stats(aggregates_df)
    if time_stat_documents:
        v2_hotel_time_stats.insert_many(time_stat_documents)

    print("Preparing v2_top_tags_by_year...")
    top_tag_documents = build_top_tags_by_year(aggregates_df)
    if top_tag_documents:
        v2_top_tags_by_year.insert_many(top_tag_documents)

    print("Preparing v2_nationality_year_stats...")
    nationality_year_documents = build_nationality_year_stats(aggregates_df)
    if nationality_year_documents:
        v2_nationality_year_stats.insert_many(nationality_year_documents)

    print("Preparing v2_nearby_hotel_trends...")
    nearby_trend_documents = build_nearby_hotel_trends(
        pd.DataFrame(hotel_documents_for_aggregates),
        pd.DataFrame(time_stat_documents),
        top_n=10,
    )
    if nearby_trend_documents:
        v2_nearby_hotel_trends.insert_many(nearby_trend_documents)

    print("Creating indexes...")
    v2_reviews.create_index([("hotel_name", 1), ("review_year", 1), ("review_month", 1)])
    v2_reviews.create_index([("hotel_name", 1), ("reviewer_nationality", 1), ("review_year", 1)])
    v2_reviews.create_index([("hotel_name", 1), ("reviewer_score", 1), ("review_year", 1)])
    v2_hotels.create_index([("location", "2dsphere")])
    v2_hotel_time_stats.create_index([("hotel_name", 1), ("period_type", 1), ("year", 1), ("month", 1)])
    v2_top_tags_by_year.create_index([("hotel_name", 1), ("year", 1)])
    v2_nationality_year_stats.create_index([("hotel_name", 1), ("year", 1), ("nationality", 1)])
    v2_nearby_hotel_trends.create_index([("anchor_hotel_name", 1), ("distance_meters", 1)])
    v2_nearby_hotel_trends.create_index([("anchor_hotel_name", 1), ("year", 1), ("month", 1)])
    v2_nearby_hotel_trends.create_index([("nearby_hotel_name", 1), ("year", 1), ("month", 1)])

    print("v2 import finished.")
    print(f"v2_hotels count: {v2_hotels.count_documents({})}")
    print(f"v2_reviews count: {v2_reviews.count_documents({})}")
    print(f"v2_hotel_time_stats count: {v2_hotel_time_stats.count_documents({})}")
    print(f"v2_top_tags_by_year count: {v2_top_tags_by_year.count_documents({})}")
    print(f"v2_nationality_year_stats count: {v2_nationality_year_stats.count_documents({})}")
    print(f"v2_nearby_hotel_trends count: {v2_nearby_hotel_trends.count_documents({})}")

    client.close()


if __name__ == "__main__":
    main()
