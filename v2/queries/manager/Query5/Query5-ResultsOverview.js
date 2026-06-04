db.getCollection("v2_nearby_hotel_trends").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
                  anchor_hotel_name: "Hotel Arena"
            }
        },

        // Stage 2
        {
            $project: {
                  _id: 0,
                  anchor_hotel_name: 1,
                  nearby_hotel_name: 1,
                  distance_meters: 1,
                  hotel_average_score: 1,
                  year: 1,
                  month: 1,
                  avg_score: 1,
                  review_count: 1
            }
        },

        // Stage 3
        {
            $sort: {
              distance_meters: 1,
              year: 1,
              month: 1
            }
        }
    ],

    // Options
    {

    }

    // Created with Studio 3T, the IDE for MongoDB - https://studio3t.com/

);