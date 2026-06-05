// Q5 — Hotels within 100km of user location, min score 8.0, sorted by distance
// v1: manual Haversine formula in $addFields on v1_hotels
// v2: $geoNear with 2dsphere index on v2_hotels_guest → native geospatial query, no manual math

// Coordinates: Milan [lng, lat] = [9.1900, 45.4642]
db.v2_hotels_guest.aggregate([
  {
    $geoNear: {
      near: {
        type: "Point",
        coordinates: [9.1900, 45.4642]
      },
      distanceField: "distance_m",
      maxDistance: 100000,
      query: {
        total_number_of_reviews: { $gte: 100 },
        average_reviewer_score: { $gte: 8.0 }
      },
      spherical: true
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
      total_number_of_reviews: 1,
      distance_km: { $round: [{ $divide: ["$distance_m", 1000] }, 2] },
      location: 1
    }
  }
])
