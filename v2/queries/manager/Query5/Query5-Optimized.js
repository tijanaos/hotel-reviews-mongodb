const hotel = db.v2_hotels.findOne(
  { name: "Hotel Arena" },
  { location: 1, _id: 0 }
);

db.v2_hotels.aggregate([
  {
    $geoNear: {
      near: hotel.location,
      distanceField: "distance_meters",
      spherical: true,
      query: {
        name: { $ne: "Hotel Arena" },
        location: { $ne: null }
      }
    }
  },
  {
    $limit: 10
  },
  {
    $lookup: {
      from: "v2_hotel_time_stats",
      localField: "_id",
      foreignField: "hotel_id",
      as: "time_stats"
    }
  },
  {
    $unwind: "$time_stats"
  },
  {
    $match: {
      "time_stats.period_type": "month"
    }
  },
  {
    $project: {
      hotel_name: "$name",
      distance_meters: 1,
      hotel_average_score: "$average_score",
      year: "$time_stats.year",
      month: "$time_stats.month",
      avg_score: "$time_stats.avg_score",
      review_count: "$time_stats.review_count"
    }
  },
  {
    $sort: {
      distance_meters: 1,
      year: 1,
      month: 1
    }
  }
])