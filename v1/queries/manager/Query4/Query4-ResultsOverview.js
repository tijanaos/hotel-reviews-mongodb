db.getCollection("v2_top_tags_by_year").aggregate(

    // Pipeline
    [
        // Stage 1
        {
            $match: {
              hotel_name: "Hotel Arena"
            }
        },

        // Stage 2
        {
            $project: {
                  _id: 0,
                  year: 1,
                  top_tags: 1
            }
        },

        // Stage 3
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