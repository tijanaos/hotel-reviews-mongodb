db.getCollection("v2_hotel_time_stats").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                  hotel_name: "Hotel Arena",
                  period_type: "month"
            }
        },

        // Stage 2
        {
            $sort: {
                  year: 1,
                  month: 1
            }
        },

        // Stage 3
        {
            $project: {
                  _id: 0,
                  year: 1,
                  month: 1,
                  avg_score: 1,
                  review_count: 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);