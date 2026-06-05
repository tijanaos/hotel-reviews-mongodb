from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from tqdm import tqdm
import os
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MINIMUM_REVIEWS = 100

PROBLEM_PATTERNS = {
    "noise":           re.compile(r"noise|noisy|loud|soundproof", re.IGNORECASE),
    "small_room":      re.compile(r"small room|tiny room|room was small|rooms are small", re.IGNORECASE),
    "cleanliness":     re.compile(r"dirty|cleanliness|unclean|not clean|dust|smell", re.IGNORECASE),
    "bed":             re.compile(r"bed|mattress|pillow", re.IGNORECASE),
    "air_conditioning": re.compile(r"air conditioning|aircondition|air con|a/c| ac |heating|climate", re.IGNORECASE),
    "wifi":            re.compile(r"wifi|wi fi|wi-fi|internet", re.IGNORECASE),
}


def detect_problems(negative_review: str) -> list[str]:
    if not isinstance(negative_review, str) or negative_review.strip() == "No Negative":
        return []
    return [pt for pt, pattern in PROBLEM_PATTERNS.items() if pattern.search(negative_review)]


def compute_reliability_score(review_count: int, avg_score: float, city_avg: float) -> float:
    m = MINIMUM_REVIEWS
    return round(
        (review_count / (review_count + m)) * avg_score
        + (m / (review_count + m)) * city_avg,
        4,
    )


def main():
    print("Creating v2_hotels_guest collection...")

    load_dotenv(PROJECT_ROOT / ".env")

    username = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    database_name = os.getenv("MONGO_DATABASE", "hotel_reviews")

    client = MongoClient(f"mongodb://{username}:{password}@localhost:27017/?authSource=admin")
    db = client[database_name]

    db["v2_hotels_guest"].drop()

    # Ucitavanje hotela
    print("Loading hotels...")
    hotels = {}
    for hotel in db["v1_hotels"].find({}):
        if hotel.get("city") is not None:
            hotels[hotel["_id"]] = hotel

    print(f"  {len(hotels)} hotels with city loaded.")

    # Grupisanje po hotel_id i ucitavanje recenzija
    total_reviews = db["v1_reviews"].count_documents({})
    print(f"Loading {total_reviews} reviews...")

    hotel_reviews: dict = {hid: [] for hid in hotels}

    for review in tqdm(db["v1_reviews"].find({}), total=total_reviews):
        hid = review["hotel_id"]
        if hid in hotel_reviews:
            hotel_reviews[hid].append(review)

    # Racunanje prosecnog reviewer_score po gradu
    print("Computing city averages...")
    city_score_buckets: dict[str, list[float]] = {}
    for hid, reviews in hotel_reviews.items():
        city = hotels[hid]["city"]
        bucket = city_score_buckets.setdefault(city, [])
        for r in reviews:
            score = r.get("reviewer_score")
            if score is not None:
                bucket.append(score)

    city_avg: dict[str, float] = {
        city: round(sum(scores) / len(scores), 4)
        for city, scores in city_score_buckets.items()
        if scores
    }

    # Insertovanje
    print("Building hotel documents...")
    batch = []
    batch_size = 500

    for hid, hotel in tqdm(hotels.items()):
        reviews = hotel_reviews[hid]
        review_count = len(reviews)

        if review_count == 0:
            continue

        # Sablon sracunavanja - query 1
        scores = [r["reviewer_score"] for r in reviews if r.get("reviewer_score") is not None]
        avg_reviewer_score = round(sum(scores) / len(scores), 4) if scores else 0.0
        city = hotel["city"]
        city_average_score = city_avg.get(city, avg_reviewer_score)
        reliability_score = compute_reliability_score(review_count, avg_reviewer_score, city_average_score)

        # Sablon podskupa - query 3
        sorted_reviews = sorted(
            reviews,
            key=lambda r: r.get("review_date") or datetime.min,
            reverse=True,
        )[:10]

        recent_reviews = [
            {
                "review_id": r["_id"],
                "review_date": r.get("review_date"),
                "reviewer_nationality": r.get("reviewer_nationality"),
                "reviewer_score": r.get("reviewer_score"),
                "positive_review": r.get("positive_review"),
                "negative_review": r.get("negative_review"),
                "positive_word_count": r.get("positive_word_count"),
                "negative_word_count": r.get("negative_word_count"),
                "tags": r.get("tags", []),
            }
            for r in sorted_reviews
        ]

        recent_scores = [rv["reviewer_score"] for rv in recent_reviews if rv.get("reviewer_score") is not None]
        recent_average_score = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None

        # Sablon atributa - query 4, unapred sracunati problem stats
        problem_accumulator: dict[str, dict] = {}
        for r in reviews:
            neg = r.get("negative_review", "")
            rscore = r.get("reviewer_score")
            for pt in detect_problems(neg):
                bucket = problem_accumulator.setdefault(pt, {"count": 0, "score_sum": 0.0})
                bucket["count"] += 1
                if rscore is not None:
                    bucket["score_sum"] += rscore

        problem_stats = [
            {
                "problem_type": pt,
                "count": data["count"],
                "percentage": round(data["count"] / review_count * 100, 2),
                "avg_score": round(data["score_sum"] / data["count"], 2),
            }
            for pt, data in sorted(problem_accumulator.items(), key=lambda x: -x[1]["count"])
        ]

        doc = {
            "_id": hid,
            "name": hotel["name"],
            "address": hotel["address"],
            "city": city,
            "country": hotel.get("country"),
            "average_score": hotel.get("average_score"),
            "total_number_of_reviews": hotel.get("total_number_of_reviews"),
            "additional_number_of_scoring": hotel.get("additional_number_of_scoring"),
            "location": hotel.get("location"),
            # Sablon sracunavanja
            "review_count": review_count,
            "average_reviewer_score": avg_reviewer_score,
            "city_average_score": city_average_score,
            "reliability_score": reliability_score,
            # Sablon podskupa
            "recent_reviews": recent_reviews,
            "recent_average_score": recent_average_score,
            # Sablon atributa
            "problem_stats": problem_stats,
        }

        batch.append(doc)

        if len(batch) == batch_size:
            db["v2_hotels_guest"].insert_many(batch)
            batch.clear()

    if batch:
        db["v2_hotels_guest"].insert_many(batch)

    count = db["v2_hotels_guest"].count_documents({})
    print(f"Done. v2_hotels_guest: {count} documents.")
    client.close()


if __name__ == "__main__":
    main()
