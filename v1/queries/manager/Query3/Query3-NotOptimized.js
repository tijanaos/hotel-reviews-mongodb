// NEOPTIMIZOVANO: v1_reviews
// Potrebno jer v1_reviews nema hotel_name, review_year ni negative_keywords.

const hotelName = "Hotel Arena";

const stopWords = [
  "the", "and", "for", "was", "were", "with", "that", "this", "from", "have",
  "had", "but", "not", "too", "very", "all", "our", "you", "your", "are",
  "just", "they", "them", "there", "then", "than", "into", "about", "after",
  "before", "because", "been", "being", "out", "off", "did", "didnt", "dont",
  "cant", "could", "would", "should", "again", "only", "more", "most", "some",
  "much", "many", "few", "lot", "lots", "one", "two", "three", "when", "where",
  "which", "while", "who", "whom", "what", "why", "how", "hotel", "room", "rooms",
  "also", "like", "even", "can", "little", "small", "around", "will", "didn", "bit",
  "nice"
];

const latestYear = db.v1_reviews.aggregate([
  {
    $match: {
      review_date: { $type: "date" }
    }
  },
  {
    $group: {
      _id: null,
      latestYear: { $max: { $year: "$review_date" } }
    }
  }
]).toArray()[0].latestYear;

db.v1_reviews.aggregate([
  {
    $match: {
      review_date: { $type: "date" },
      negative_review: { $nin: ["No Negative", "", null] }
    }
  },
  {
    $addFields: {
      review_year: { $year: "$review_date" }
    }
  },
  {
    $match: {
      review_year: latestYear
    }
  },
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
      "hotel.name": hotelName
    }
  },
  {
    $project: {
      tokens: {
        $map: {
          input: {
            $regexFindAll: {
              input: { $toLower: "$negative_review" },
              regex: "[a-zA-Z']+"
            }
          },
          as: "m",
          in: "$$m.match"
        }
      }
    }
  },
  {
    $project: {
      tokens: {
        $filter: {
          input: "$tokens",
          as: "word",
          cond: {
            $and: [
              { $gte: [{ $strLenCP: "$$word" }, 3] },
              { $not: { $in: ["$$word", stopWords] } }
            ]
          }
        }
      }
    }
  },
  {
    $project: {
      // da se ponaša kao v2 import, gde se duplikati uklanjaju unutar jedne recenzije
      tokens: { $setUnion: ["$tokens", []] }
    }
  },
  { $unwind: "$tokens" },
  {
    $group: {
      _id: "$tokens",
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