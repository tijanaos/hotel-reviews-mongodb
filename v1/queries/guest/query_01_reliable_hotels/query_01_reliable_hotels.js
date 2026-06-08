// Koji hoteli u izabranom gradu imaju visoku prosecnu ocenu i barem 100 recenzija.
// za reliability score koriscena formula Bayesian Average
// review_count / (review_count + 100) * hotel_average + 100 / (review_count + 100) * city_average

db.v1_reviews.aggregate(
[
  {
    $lookup: {
      from: "v1_hotels",
      localField: "hotel_id",
      foreignField: "_id",
      as: "hotel"
    }
  },
  {
    $unwind: "$hotel"
  },
  {
    $match: {
      "hotel.city": "Amsterdam"
    }
  },
  {
    $facet: {
      cityStats: [
        {
          $group: {
            _id: null,
            city_average_score: { $avg: "$reviewer_score" }
          }
        }
      ],
      hotelStats: [
        {
          $group: {
            _id: "$hotel._id",
            hotel_name: { $first: "$hotel.name" },
            address: { $first: "$hotel.address" },
            city: { $first: "$hotel.city" },
            country: { $first: "$hotel.country" },
            average_reviewer_score: { $avg: "$reviewer_score" },
            review_count: { $sum: 1 }
          }
        },
        {
          $match: {
            review_count: { $gte: 100 }
          }
        }
      ]
    }
  },
  {
    $unwind: "$cityStats"
  },
  {
    $unwind: "$hotelStats"
  },
  {
    $project: {
      _id: 0,
      hotel_id: "$hotelStats._id",
      hotel_name: "$hotelStats.hotel_name",
      address: "$hotelStats.address",
      city: "$hotelStats.city",
      country: "$hotelStats.country",
      average_reviewer_score: {
        $round: ["$hotelStats.average_reviewer_score", 2]
      },
      review_count: "$hotelStats.review_count",
      city_average_score: {
        $round: ["$cityStats.city_average_score", 2]
      },
      reliability_score: {
        $round: [
          {
            $add: [
              {
                $multiply: [
                  {
                    $divide: [
                      "$hotelStats.review_count",
                      { $add: ["$hotelStats.review_count", 100] }
                    ]
                  },
                  "$hotelStats.average_reviewer_score"
                ]
              },
              {
                $multiply: [
                  {
                    $divide: [
                      100,
                      { $add: ["$hotelStats.review_count", 100] }
                    ]
                  },
                  "$cityStats.city_average_score"
                ]
              }
            ]
          },
          4
        ]
      }
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
  }
]);