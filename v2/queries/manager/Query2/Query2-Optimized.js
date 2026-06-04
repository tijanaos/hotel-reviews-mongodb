db.getCollection("v2_reviews").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
              hotel_name: "Hotel Arena",
              review_year: { $ne: null },
              reviewer_nationality: { $ne: null, $ne: "" }
            }
        },

        // Stage 2
        {
            $group: {
              _id: {
                year: "$review_year",
                nationality: "$reviewer_nationality"
              },
              avg_score: { $avg: "$reviewer_score" },
              review_count: { $sum: 1 },
              high_score_count: {
                $sum: {
                  $cond: [{ $gt: ["$reviewer_score", 8.5] }, 1, 0]
                }
              },
              low_score_count: {
                $sum: {
                  $cond: [{ $lt: ["$reviewer_score", 5] }, 1, 0]
                }
              }
            }
        },

        // Stage 3
        {
            $sort: {
                 "_id.year": 1,
                 avg_score: -1
            }
        },

        // Stage 4
        {
            $project: {
                  _id: 0,
                  year: "$_id.year",
                  nationality: "$_id.nationality",
                  avg_score: { $round: ["$avg_score", 2] },
                  review_count: 1,
                  high_score_count: 1,
                  low_score_count: 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);