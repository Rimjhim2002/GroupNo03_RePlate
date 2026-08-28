from models.food_listing import FoodListing, ListingStatus
from models.food_recommendation import FoodRecommendation, RecommendationType

URGENT_DONATE_THRESHOLD_HOURS = 3
DONATE_THRESHOLD_HOURS = 8
DISCOUNT_THRESHOLD_HOURS = 24
 
 
async def generate_recommendation(food_listing: FoodListing) -> FoodRecommendation:
    """
    Core of the Smart Food Lifecycle Recommendation feature.
    Looks at how much shelf life a listing has left and decides whether the
    restaurant should discount-and-sell it or donate it, with a confidence score.
    """
    remaining_hours = food_listing.get_remaining_shelf_life_hours()
 
    if remaining_hours <= URGENT_DONATE_THRESHOLD_HOURS:
        rec_type = RecommendationType.URGENT_DONATE
        suggested_discount = 100.0
        priority_score = 100.0
        confidence_score = 0.95
        reason = f"Only {remaining_hours:.1f}h left before expiry — donate immediately to avoid waste."
    elif remaining_hours <= DONATE_THRESHOLD_HOURS:
        rec_type = RecommendationType.DONATE
        suggested_discount = 75.0
        priority_score = 80.0
        confidence_score = 0.85
        reason = f"{remaining_hours:.1f}h left — unlikely to sell in time, recommend donation."
    elif remaining_hours <= DISCOUNT_THRESHOLD_HOURS:
        rec_type = RecommendationType.DISCOUNT_SALE
        suggested_discount = min(50.0, round((DISCOUNT_THRESHOLD_HOURS - remaining_hours) * 2, 1))
        priority_score = 50.0
        confidence_score = 0.75
        reason = f"{remaining_hours:.1f}h left — apply a discount to move stock before it expires."
    else:
        rec_type = RecommendationType.DISCOUNT_SALE
        suggested_discount = 10.0
        priority_score = 20.0
        confidence_score = 0.6
        reason = "Plenty of shelf life left — a small discount is enough to attract buyers."
 
    recommendation = FoodRecommendation(
        food_listing_id=str(food_listing.id),
        recommendation_type=rec_type,
        suggested_discount=suggested_discount,
        priority_score=priority_score,
        confidence_score=confidence_score,
        reason=reason,
    )
    await recommendation.insert()
    return recommendation
 
 
async def generate_recommendations_for_all_active_listings() -> list[FoodRecommendation]:
    """Meant to be triggered periodically (cron / scheduled task) to refresh every active listing."""
    active_listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE
    ).to_list()
 
    recommendations = []
    for listing in active_listings:
        recommendation = await generate_recommendation(listing)
        recommendations.append(recommendation)
    return recommendations
 
 
async def get_latest_recommendation(food_listing_id: str) -> FoodRecommendation | None:
    return await FoodRecommendation.find(
        FoodRecommendation.food_listing_id == food_listing_id
    ).sort(-FoodRecommendation.generated_at).first_or_none()