// Koji hoteli imaju najčešće negativne komentare o problemima kao što su buka, mala soba, 
// loša čistoća, neudoban krevet, klima ili Wi-Fi?   

db.v2_hotels_guest.aggregate([
  {
    $match: {
      city: "Amsterdam"
    }
  },
  {
    $unwind: "$problem_stats"
  },
  {
    $match: {
      "problem_stats.count": { $gte: 10 }
    }
  },
  {
    $sort: {
      "problem_stats.percentage": -1,
      "problem_stats.count": -1,
      "problem_stats.avg_score": 1
    }
  },
  {
    $limit: 20
  },
  {
    $project: {
      _id: 0,
      hotel_id: "$_id",
      name: 1,
      address: 1,
      city: 1,
      country: 1,
      review_count: 1,
      problem_type: "$problem_stats.problem_type",
      problem_review_count: "$problem_stats.count",
      problem_review_percentage: "$problem_stats.percentage",
      average_problem_reviewer_score: "$problem_stats.avg_score"
    }
  }
])
