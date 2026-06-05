// Q2 — Top hotels for a specific guest type in a city
// v1: $lookup + $match on tags (raw string) + $group
// v2: $match on embedded hotel.city + classified guest_types array on v2_reviews_guest

db.v2_reviews_guest.aggregate([
  {
    $match: {
      "hotel.city": "Amsterdam",
      guest_types: "couple"
    }
  },
  {
    $group: {
      _id: "$hotel_id",
      name: { $first: "$hotel.name" },
      address: { $first: "$hotel.address" },
      city: { $first: "$hotel.city" },
      country: { $first: "$hotel.country" },
      average_reviewer_score: { $avg: "$reviewer_score" },
      review_count: { $sum: 1 }
    }
  },
  {
    $match: {
      review_count: { $gte: 20 }
    }
  },
  {
    $sort: {
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
      guest_type: "couple",
      average_reviewer_score: { $round: ["$average_reviewer_score", 2] },
      review_count: 1
    }
  }
])
