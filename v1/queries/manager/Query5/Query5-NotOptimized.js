db.getCollection("v1_hotels").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                  location: { $ne: null },
                  name: { $ne: "Hotel Arena" }
            }
        },

        // Stage 2
        {
            $project: {
              name: 1,
              average_score: 1,
              location: 1,
              distance_score: {
                $sqrt: {
                  $add: [
                    {
                      $pow: [
                        { $subtract: [{ $arrayElemAt: ["$location.coordinates", 0] }, 4.9149] },
                        2
                      ]
                    },
                    {
                      $pow: [
                        { $subtract: [{ $arrayElemAt: ["$location.coordinates", 1] }, 52.3606] },
                        2
                      ]
                    }
                  ]
                }
              }
            }
        },

        // Stage 3
        {
            $sort: {
                  distance_score: 1
            }
        },

        // Stage 4
        {
            $limit: // positive integer
            10
        },

        // Stage 5
        {
            $lookup: {
                  from: "v1_reviews",
                  localField: "_id",
                  foreignField: "hotel_id",
                  as: "reviews"
            }
        },

        // Stage 6
        {
            $unwind: "$reviews"
        },

        // Stage 7
        {
            $match: {
                  "reviews.review_date": { $ne: null }
            }
        },

        // Stage 8
        {
            $project: {
                  hotel_name: "$name",
                  distance_score: 1,
                  average_score: 1,
                  year: { $year: "$reviews.review_date" },
                  month: { $month: "$reviews.review_date" },
                  reviewer_score: "$reviews.reviewer_score"
            }
        },

        // Stage 9
        {
            $group: {
                  _id: {
                    hotel_name: "$hotel_name",
                    distance_score: "$distance_score",
                    average_score: "$average_score",
                    year: "$year",
                    month: "$month"
                  },
                  avg_score: { $avg: "$reviewer_score" },
                  review_count: { $sum: 1 }
            }
        },

        // Stage 10
        {
            $sort: {
                 "_id.distance_score": 1,
                 "_id.year": 1,
                 "_id.month": 1
            }
        },

        // Stage 11
        {
            $project: {
                  _id: 0,
                  hotel_name: "$_id.hotel_name",
                  distance_score: "$_id.distance_score",
                  hotel_average_score: "$_id.average_score",
                  year: "$_id.year",
                  month: "$_id.month",
                  avg_score: { $round: ["$avg_score", 2] },
                  review_count: 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);