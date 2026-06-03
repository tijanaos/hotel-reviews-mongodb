from pathlib import Path
import ast
from datetime import datetime

import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from tqdm import tqdm
import os


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


def create_hotel_document(row) -> dict:
    country = extract_country(row["Hotel_Address"])
    city = extract_city(row["Hotel_Address"])

    lat = row["lat"]
    lng = row["lng"]

    location = None
    if pd.notna(lat) and pd.notna(lng):
        location = {
            "type": "Point",
            "coordinates": [float(lng), float(lat)]
        }

    return {
        "name": row["Hotel_Name"],
        "address": row["Hotel_Address"],
        "city": city,
        "country": country,
        "average_score": float(row["Average_Score"]),
        "total_number_of_reviews": int(row["Total_Number_of_Reviews"]),
        "additional_number_of_scoring": int(row["Additional_Number_of_Scoring"]),
        "location": location,
    }


def create_review_document(row, hotel_id) -> dict:
    return {
        "hotel_id": hotel_id,
        "review_date": parse_review_date(row["Review_Date"]),
        "reviewer_nationality": row["Reviewer_Nationality"].strip(),
        "negative_review": row["Negative_Review"],
        "positive_review": row["Positive_Review"],
        "negative_word_count": int(row["Review_Total_Negative_Word_Counts"]),
        "positive_word_count": int(row["Review_Total_Positive_Word_Counts"]),
        "reviewer_score": float(row["Reviewer_Score"]),
        "reviewer_total_reviews": int(row["Total_Number_of_Reviews_Reviewer_Has_Given"]),
        "tags": parse_tags(row["Tags"]),
        "days_since_review": parse_days_since_review(row["days_since_review"]),
    }


def main():
    print("Importing v1 data...")

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

    hotels_collection = db["v1_hotels"]
    reviews_collection = db["v1_reviews"]

    hotels_collection.drop()
    reviews_collection.drop()

    df = pd.read_csv(DATASET_PATH)

    hotel_ids_by_name_and_address = {}
    seen_hotel_keys = set()
    hotels_to_insert = []

    print("Preparing hotels...")

    for _, row in tqdm(df.iterrows(), total=len(df)):
        hotel_key = (
            str(row["Hotel_Name"]).strip(),
            str(row["Hotel_Address"]).strip()
        )
        if hotel_key not in seen_hotel_keys:
            seen_hotel_keys.add(hotel_key)

            hotel_document = create_hotel_document(row)
            hotels_to_insert.append((hotel_key, hotel_document))

    inserted_hotels = hotels_collection.insert_many(
        [hotel_document for _, hotel_document in hotels_to_insert]
    )

    for index, inserted_id in enumerate(inserted_hotels.inserted_ids):
        hotel_key = hotels_to_insert[index][0]
        hotel_ids_by_name_and_address[hotel_key] = inserted_id

    print("Preparing reviews...")

    batch = []
    batch_size = 5000

    for _, row in tqdm(df.iterrows(), total=len(df)):
        hotel_key = (
            str(row["Hotel_Name"]).strip(),
            str(row["Hotel_Address"]).strip()
        )

        hotel_id = hotel_ids_by_name_and_address[hotel_key]

        review_document = create_review_document(row, hotel_id)
        batch.append(review_document)

        if len(batch) == batch_size:
            reviews_collection.insert_many(batch)
            batch.clear()

    if batch:
        reviews_collection.insert_many(batch)

    print("Import finished.")
    print(f"Hotels count: {hotels_collection.count_documents({})}")
    print(f"Reviews count: {reviews_collection.count_documents({})}")

    client.close()


if __name__ == "__main__":
    main()