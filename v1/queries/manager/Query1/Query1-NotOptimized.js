db.getCollection("v1_reviews").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $lookup: {
              from: "v1_hotels",
              localField: "hotel_id",
              foreignField: "_id",
              as: "hotel"
            }
        },

        // Stage 2
        {
            $unwind: {
              path: "$hotel"
            }
        },

        // Stage 3
        {
            $match: {
              "hotel.name": "Hotel Arena",
              review_date: { $ne: null }
            }
        },

        // Stage 4
        {
            $project: {
              year: { $year: "$review_date" },
              month: { $month: "$review_date" },
              reviewer_score: 1
            }
        },

        // Stage 5
        {
            $group: {
              _id: {
                year: "$year",
                month: "$month"
              },
              avg_score: { $avg: "$reviewer_score" },
              review_count: { $sum: 1 }
            }
        },

        // Stage 6
        {
            $sort: {
              "_id.year": 1,
              "_id.month": 1
            }
        },

        // Stage 7
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