// Koje su najnovije recenzije(poslednjih 10) izabranog hotela i kakvu prosečnu ocenu hotel ima u skorijem periodu?

db.v2_hotels_guest.aggregate([
  {
    $match: {
      name: "Hotel Arena",
      city: "Amsterdam"
    }
  },
  {
    $project: {
      _id: 0,
      hotel: {
        hotel_id: "$_id",
        hotel_name: "$name",
        address: "$address",
        city: "$city",
        country: "$country",
        total_average_score: "$average_score",
        total_number_of_reviews: "$total_number_of_reviews"
      },
      recent_review_count: { $size: "$recent_reviews" },
      recent_average_score: 1,
      latest_reviews: "$recent_reviews"
    }
  }
])
