// Q3 — 10 most recent reviews for a specific hotel
// v1: $lookup + $sort + $facet (latest_reviews + recent_score_summary + hotel_info)
// v2: pre-embedded recent_reviews (Subset Pattern) → single document read on v2_hotels_guest

db.v2_hotels_guest.aggregate([
  {
    $match: {
      name: "Hotel Arena",
      city: "Amsterdam"
    }
  },
  {
    $project: {
      _id: 0,
      hotel: {
        hotel_id: "$_id",
        hotel_name: "$name",
        address: "$address",
        city: "$city",
        country: "$country",
        total_average_score: "$average_score",
        total_number_of_reviews: "$total_number_of_reviews"
      },
      recent_review_count: { $size: "$recent_reviews" },
      recent_average_score: 1,
      latest_reviews: "$recent_reviews"
    }
  }
])
