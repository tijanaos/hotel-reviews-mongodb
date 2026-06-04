db.getCollection("v2_nationality_year_stats").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                  "hotel_name": "Hotel Arena"
            }
        },

        // Stage 2
        {
            $project: {
                  "_id": 0,
                  "nationality": 1,
                  "avg_score": 1,
                  "review_count": 1,
                  "high_score_count": 1,
                  "low_score_count": 1,
                  "year":1
                }
        },

        // Stage 3
        {
            $sort: {
                  "review_count": -1,
                  "nationality": 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);