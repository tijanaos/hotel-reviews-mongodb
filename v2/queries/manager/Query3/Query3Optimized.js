// OPTIMIZOVANO: v2_reviews
// Koristi hotel_name, review_year i negative_keywords koji su već pripremljeni pri importu.

const hotelName = "Hotel Arena";

const latestYear = db.v2_reviews.aggregate([
  {
    $match: {
      review_year: { $ne: null }
    }
  },
  {
    $group: {
      _id: null,
      latestYear: { $max: "$review_year" }
    }
  }
]).toArray()[0].latestYear;

db.v2_reviews.aggregate([
  {
    $match: {
      hotel_name: hotelName,
      review_year: latestYear,
      negative_keywords: { $exists: true, $ne: [] }
    }
  },
  {
    $unwind: "$negative_keywords"
  },
  {
    $group: {
      _id: "$negative_keywords",
      count: { $sum: 1 }
    }
  },
  {
    $sort: {
      count: -1,
      _id: 1
    }
  },
  {
    $limit: 20
  }
]);