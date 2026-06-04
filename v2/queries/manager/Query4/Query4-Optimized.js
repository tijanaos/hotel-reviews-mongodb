db.getCollection("v2_reviews").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                 hotel_name: "Hotel Arena",
                 reviewer_score: { $gt: 8.5 },
                 review_year: { $ne: null },
                 tags: { $exists: true, $ne: [] }
            }
        },

        // Stage 2
        {
            $project: {
                 year: "$review_year",
                 tags: 1
            }
        },

        // Stage 3
        {
            $unwind: "$tags"
        },

        // Stage 4
        {
            $group: {
                  _id: {
                    year: "$year",
                    tag: "$tags"
                  },
                  count: { $sum: 1 }
            }
        },

        // Stage 5
        {
            $sort: {
                  "_id.year": 1,
                  count: -1
            }
        },

        // Stage 6
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

        // Stage 7
        {
            $project: {
              _id: 0,
              year: "$_id",
              top_10_tags: { $slice: ["$top_tags", 10] }
            }
        },

        // Stage 8
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