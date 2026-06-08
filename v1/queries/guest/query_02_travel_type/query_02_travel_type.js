// Koji hoteli su najbolje ocenjeni od strane gostiju koji putuju kao parovi? 
// Hoteli se racunaju ako imaju barem 20 recenzija ljudi koji su putovali kao parovi.

db.v1_reviews.aggregate(
[
  {
    $lookup: {
      from: "v1_hotels",
      localField: "hotel_id",
      foreignField: "_id",
      as: "hotel"
    }
  },
  {
    $unwind: "$hotel"
  },
  {
    $match: {
      "hotel.city": "Amsterdam",
      tags: "Couple"
    }
  },
  {
    $group: {
      _id: "$hotel._id",
      hotel_name: { $first: "$hotel.name" },
      address: { $first: "$hotel.address" },
      city: { $first: "$hotel.city" },
      country: { $first: "$hotel.country" },
      average_reviewer_score: { $avg: "$reviewer_score" },
      review_count: { $sum: 1 }
    }
  },
  {
    $match: {
      review_count: { $gte: 20 }
    }
  },
  {
    $sort: {
      average_reviewer_score: -1,
      review_count: -1
    }
  },
  {
    $limit: 10
  },
  {
    $project: {
      _id: 0,
      hotel_id: "$_id",
      hotel_name: 1,
      address: 1,
      city: 1,
      country: 1,
      guest_type: "Couple",
      average_reviewer_score: {
        $round: ["$average_reviewer_score", 2]
      },
      review_count: 1
    }
  }
]);