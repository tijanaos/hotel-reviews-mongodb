db.v1_hotels.aggregate([
  {
    $match: {
      location: { $ne: null },
      "location.coordinates.0": { $ne: null },
      "location.coordinates.1": { $ne: null },
      total_number_of_reviews: { $gte: 100 }
    }
  },
  {
    $addFields: {
      user_longitude: 9.1900,
      user_latitude: 45.4642,
      hotel_longitude: { $arrayElemAt: ["$location.coordinates", 0] },
      hotel_latitude: { $arrayElemAt: ["$location.coordinates", 1] }
    }
  },
  {
    $addFields: {
      distance_km: {
        $let: {
          vars: {
            earth_radius_km: 6371,
            lat1_rad: {
              $degreesToRadians: "$user_latitude"
            },
            lat2_rad: {
              $degreesToRadians: "$hotel_latitude"
            },
            delta_lat_rad: {
              $degreesToRadians: {
                $subtract: [
                  "$hotel_latitude",
                  "$user_latitude"
                ]
              }
            },
            delta_lng_rad: {
              $degreesToRadians: {
                $subtract: [
                  "$hotel_longitude",
                  "$user_longitude"
                ]
              }
            }
          },
          in: {
            $multiply: [
              "$$earth_radius_km",
              2,
              {
                $asin: {
                  $sqrt: {
                    $add: [
                      {
                        $pow: [
                          {
                            $sin: {
                              $divide: [
                                "$$delta_lat_rad",
                                2
                              ]
                            }
                          },
                          2
                        ]
                      },
                      {
                        $multiply: [
                          {
                            $cos: "$$lat1_rad"
                          },
                          {
                            $cos: "$$lat2_rad"
                          },
                          {
                            $pow: [
                              {
                                $sin: {
                                  $divide: [
                                    "$$delta_lng_rad",
                                    2
                                  ]
                                }
                              },
                              2
                            ]
                          }
                        ]
                      }
                    ]
                  }
                }
              }
            ]
          }
        }
      }
    }
  },
  {
    $match: {
      distance_km: { $lte: 100 }
    }
  },
  {
    $lookup: {
      from: "v1_reviews",
      localField: "_id",
      foreignField: "hotel_id",
      as: "reviews"
    }
  },
  {
    $addFields: {
      average_reviewer_score: { $avg: "$reviews.reviewer_score" }
    }
  },
  {
    $match: {
      average_reviewer_score: { $gte: 8.0 }
    }
  },
  {
    $sort: {
      distance_km: 1,
      average_reviewer_score: -1,
      total_number_of_reviews: -1
    }
  },
  {
    $limit: 10
  },
  {
    $project: {
      _id: 0,
      hotel_id: "$_id",
      hotel_name: "$name",
      address: 1,
      city: 1,
      country: 1,
      average_reviewer_score: { $round: ["$average_reviewer_score", 2] },
      total_number_of_reviews: 1,
      distance_km: {
        $round: [
          "$distance_km",
          2
        ]
      },
      location: 1
    }
  }
]);