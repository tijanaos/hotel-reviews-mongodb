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
              reviewer_score: { $gt: 8.5 },
              review_date: { $ne: null },
              tags: { $exists: true, $ne: [] }
            }
        },

        // Stage 4
        {
            $project: {
              year: { $year: "$review_date" },
              tags: 1
            }
        },

        // Stage 5
        {
            $unwind: {
              path: "$tags"
            }
        },

        // Stage 6
        {
            $group: {
              _id: {
                year: "$year",
                tag: "$tags"
              },
              count: { $sum: 1 }
            }
        },

        // Stage 7
        {
            $sort: {
              "_id.year": 1,
              count: -1
            }
        },

        // Stage 8
        {
            $group: {
              _id: "$_id.year",
              top_tags: {
                $push: {
                  tag: "$_id.tag",
                  count: "$count"
                }
              }
            }
        },

        // Stage 9
        {
            $project: {
              _id: 0,
              year: "$_id",
              top_10_tags: { $slice: ["$top_tags", 10] }
            }
        },

        // Stage 10
        {
            $sort: {
              year: 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);