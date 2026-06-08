// Koji hoteli imaju najčešće negativne komentare o problemima kao što su buka, mala soba, 
// loša čistoća, neudoban krevet, klima ili Wi-Fi?   

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
        "hotel.city": "Amsterdam",
        negative_review: {
          $ne: "No Negative"
        }
      }
    },
    {
      $addFields: {
        negative_review_lower: {
          $toLower: "$negative_review"
        }
      }
    },
    {
      $addFields: {
        problem_types: {
          $setUnion: [
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "noise|noisy|loud|soundproof"
                  }
                },
                ["noise"],
                []
              ]
            },
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "small room|tiny room|room was small|rooms are small"
                  }
                },
                ["small_room"],
                []
              ]
            },
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "dirty|cleanliness|unclean|not clean|dust|smell"
                  }
                },
                ["cleanliness"],
                []
              ]
            },
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "bed|mattress|pillow"
                  }
                },
                ["bed"],
                []
              ]
            },
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "air conditioning|aircondition|air con|a/c| ac |heating|climate"
                  }
                },
                ["air_conditioning"],
                []
              ]
            },
            {
              $cond: [
                {
                  $regexMatch: {
                    input: "$negative_review_lower",
                    regex: "wifi|wi fi|wi-fi|internet"
                  }
                },
                ["wifi"],
                []
              ]
            }
          ]
        }
      }
    },
    {
      $match: {
        $expr: {
          $gt: [
            {
              $size: "$problem_types"
            },
            0
          ]
        }
      }
    },
    {
      $unwind: "$problem_types"
    },
    {
      $group: {
        _id: {
          hotel_id: "$hotel._id",
          problem_type: "$problem_types"
        },
        hotel_name: { $first: "$hotel.name"},
        address: { $first: "$hotel.address"},
        city: { $first: "$hotel.city"},
        country: { $first: "$hotel.country"},
        total_hotel_reviews: { $first: "$hotel.total_number_of_reviews"},
        problem_review_count: { $sum: 1},
        average_problem_reviewer_score: { $avg: "$reviewer_score"}
      }
    },
    {
      $addFields: {
        problem_review_percentage: {
          $multiply: [
            {
              $divide: [
                "$problem_review_count",
                "$total_hotel_reviews"
              ]
            },
            100
          ]
        }
      }
    },
    {
      $match: {
        problem_review_count: {
          $gte: 10
        }
      }
    },
    {
      $sort: {
        problem_review_percentage: -1,
        problem_review_count: -1,
        average_problem_reviewer_score: 1
      }
    },
    {
      $limit: 20
    },
    {
      $project: {
        _id: 0,
        hotel_id: "$_id.hotel_id",
        hotel_name: 1,
        address: 1,
        city: 1,
        country: 1,
        problem_type: "$_id.problem_type",
        total_hotel_reviews: 1,
        problem_review_count: 1,
        problem_review_percentage: {
          $round: [
            "$problem_review_percentage",
            2
          ]
        },
        average_problem_reviewer_score: {
          $round: [
            "$average_problem_reviewer_score",
            2
          ]
        }
      }
    }
  ],
  {
    allowDiskUse: true
  }
);