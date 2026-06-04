db.getCollection("v2_reviews").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                  hotel_name: "Hotel Arena",
                  review_year: { $ne: null },
                  review_month: { $ne: null }
            }
        },

        // Stage 2
        {
            $group: {
                  _id: {
                    year: "$review_year",
                    month: "$review_month"
                  },
                  avg_score: { $avg: "$reviewer_score" },
                  review_count: { $sum: 1 }
            }
        },

        // Stage 3
        {
            $sort: {
                  "_id.year": 1,
                  "_id.month": 1
            }
        },

        // Stage 4
        {
            $project: {
                  _id: 0,
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