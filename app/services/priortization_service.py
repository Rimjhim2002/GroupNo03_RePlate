from app.models.food_listing import FoodListing, ListingStatus
 
 
async def get_prioritized_listings(restaurant_id: str | None = None, limit: int = 50) -> list[FoodListing]:
    """
    Returns available listings sorted so items closest to expiry appear first.
    Used to drive the consumer home feed / search results ordering.
    """
    query = FoodListing.find(FoodListing.status == ListingStatus.AVAILABLE)
    if restaurant_id:
        query = query.find(FoodListing.restaurant_id == restaurant_id)
 
    listings = await query.sort(+FoodListing.expiry_time).limit(limit).to_list()
    return listings
 
 
async def get_urgent_listings(hours_threshold: float = 6) -> list[FoodListing]:
    """Listings expiring within `hours_threshold` hours — used for banners / expiry alerts."""
    listings = await get_prioritized_listings(limit=200)
    return [listing for listing in listings if listing.get_remaining_shelf_life_hours() <= hours_threshold]
 
 
def compute_priority_score(food_listing: FoodListing) -> float:
    """Lower remaining shelf life -> higher priority score (0-100 scale)."""
    remaining_hours = food_listing.get_remaining_shelf_life_hours()
    if remaining_hours <= 0:
        return 100.0
    score = max(0.0, 100.0 - remaining_hours)
    return round(min(score, 100.0), 2)