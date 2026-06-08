// Koje su najnovije recenzije(poslednjih 10) izabranog hotela i kakvu prosečnu ocenu hotel ima u skorijem periodu?

db.v1_reviews.aggregate([
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
      "hotel.name": "Hotel Arena",
      "hotel.city": "Amsterdam"
    }
  },
  {
    $sort: {
      review_date: -1
    }
  },
  {
    $facet: {
      latest_reviews: [
        {
          $limit: 10
        },
        {
          $project: {
            _id: 0,
            review_date: 1,
            reviewer_nationality: 1,
            reviewer_score: 1,
            positive_review: 1,
            negative_review: 1,
            positive_word_count: 1,
            negative_word_count: 1,
            tags: 1
          }
        }
      ],
      recent_score_summary: [
        {
          $limit: 10
        },
        {
          $group: {
            _id: null,
            recent_review_count: {
              $sum: 1
            },
            recent_average_score: {
              $avg: "$reviewer_score"
            }
          }
        }
      ],
      hotel_info: [
        {
          $limit: 1
        },
        {
          $project: {
            _id: 0,
            hotel_id: "$hotel._id",
            hotel_name: "$hotel.name",
            address: "$hotel.address",
            city: "$hotel.city",
            country: "$hotel.country",
            total_average_score: "$hotel.average_score",
            total_number_of_reviews: "$hotel.total_number_of_reviews"
          }
        }
      ]
    }
  },
  {
    $project: {
      hotel: {
        $arrayElemAt: [
          "$hotel_info",
          0
        ]
      },
      recent_review_count: {
        $arrayElemAt: [
          "$recent_score_summary.recent_review_count",
          0
        ]
      },
      recent_average_score: {
        $round: [
          {
            $arrayElemAt: [
              "$recent_score_summary.recent_average_score",
              0
            ]
          },
          2
        ]
      },
      latest_reviews: 1
    }
  }
]);