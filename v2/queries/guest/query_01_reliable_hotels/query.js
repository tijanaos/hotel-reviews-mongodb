// Koji hoteli u izabranom gradu imaju visoku prosecnu ocenu i barem 100 recenzija.

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
