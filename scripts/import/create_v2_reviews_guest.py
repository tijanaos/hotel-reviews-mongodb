from pathlib import Path
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from tqdm import tqdm
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAG_TO_GUEST_TYPE = {
    "Couple": "couple",
    "Family with young children": "family",
    "Family with older children": "family",
    "Solo traveler": "solo",
    "Business trip": "business",
}


def classify_guest_types(tags: list[str]) -> list[str]:
    guest_types = set()
    for tag in tags:
        gt = TAG_TO_GUEST_TYPE.get(tag)
        if gt:
            guest_types.add(gt)
    return sorted(guest_types)


def main():
    print("Creating v2_reviews_guest collection...")

    load_dotenv(PROJECT_ROOT / ".env")

    username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    database_name = os.getenv("MONGO_DATABASE", "hotel_reviews")

    client = MongoClient(f"mongodb://{username}:{password}@localhost:27017/?authSource=admin")
    db = client[database_name]

    db["v2_reviews_guest"].drop()

    # (id -> {name, address, city, country})
    print("Loading hotels...")
    hotel_map = {}
    for hotel in db["v1_hotels"].find({}, {"name": 1, "address": 1, "city": 1, "country": 1}):
        hotel_map[hotel["_id"]] = {
            "name": hotel["name"],
            "address": hotel["address"],
            "city": hotel.get("city"),
            "country": hotel.get("country"),
        }

    total = db["v1_reviews"].count_documents({})
    print(f"Processing {total} reviews...")

    batch = []
    batch_size = 5000

    for review in tqdm(db["v1_reviews"].find({}), total=total):
        hotel_info = hotel_map.get(review["hotel_id"])
        if hotel_info is None or hotel_info.get("city") is None:
            continue

        tags = review.get("tags", [])
        guest_types = classify_guest_types(tags)

        doc = {
            "_id": review["_id"],
            "hotel_id": review["hotel_id"],
            "review_date": review.get("review_date"),
            "reviewer_nationality": review.get("reviewer_nationality"),
            "reviewer_score": review.get("reviewer_score"),
            "positive_review": review.get("positive_review"),
            "negative_review": review.get("negative_review"),
            "positive_word_count": review.get("positive_word_count"),
            "negative_word_count": review.get("negative_word_count"),
            "tags": tags,
            "hotel": hotel_info,
            "guest_types": guest_types,
        }

        batch.append(doc)

        if len(batch) == batch_size:
            db["v2_reviews_guest"].insert_many(batch)
            batch.clear()

    if batch:
        db["v2_reviews_guest"].insert_many(batch)

    count = db["v2_reviews_guest"].count_documents({})
    print(f"Done. v2_reviews_guest: {count} documents.")
    client.close()


if __name__ == "__main__":
    main()
