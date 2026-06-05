// Q1 — Top 10 most reliable hotels in a city
// v1: $lookup + $facet + runtime Bayesian formula
// v2: pre-computed reliability_score → simple $match + $sort on v2_hotels_guest

db.v2_hotels_guest.aggregate([
  {
    $match: {
      city: "Amsterdam",
      review_count: { $gte: 100 }
    }
  },
  {
    $sort: {
      reliability_score: -1,
      average_reviewer_score: -1,
      review_count: -1
    }
  },
  {
    $limit: 10
  },
  {
    $project: {
      _id: 0,
      hotel_id: "$_id",
      name: 1,
      address: 1,
      city: 1,
      country: 1,
      average_reviewer_score: 1,
      review_count: 1,
      city_average_score: 1,
      reliability_score: 1
    }
  }
])
