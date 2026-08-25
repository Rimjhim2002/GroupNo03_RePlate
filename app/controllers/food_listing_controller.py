from fastapi import HTTPException,status
from app.models.enums import ListingStatus
from app.models.user import VerificationStatus
from app.models.food_listing import FoodListing
from app.models.user import User
from app.schemas.food_listing_schema import FoodListingCreate, FoodListingRead


def _to_food_listing_read(listing: FoodListing, restaurant_id: str) -> FoodListingRead:
    discounted_price = listing.original_price * (1 - listing.discount_percentage / 100)
    return FoodListingRead(
        id=str(listing.id),
        restaurant_id=restaurant_id,
        food_name=listing.food_name,
        description=listing.description,
        category=listing.category,
        listing_type=listing.listing_type,
        quantity=listing.quantity,
        available_quantity=listing.available_quantity,
        unit=listing.unit,
        original_price=listing.original_price,
        discount_percentage=listing.discount_percentage,
        discounted_price=round(discounted_price, 2),
        expiry_date=listing.expiry_date,
        pickup_location=listing.pickup_location,
        status=listing.status,
        created_at=listing.created_at,
    )


async def create_listing(data: FoodListingCreate, restaurant: User) -> FoodListingRead:
    if restaurant.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your restaurant account must be verified before creating listings.",
        )

    listing = FoodListing(
        restaurant=restaurant,
        food_name=data.food_name,
        description=data.description,
        category=data.category,
        listing_type=data.listing_type,
        quantity=data.quantity,
        available_quantity=data.quantity,
        unit=data.unit,
        original_price=data.original_price,
        discount_percentage=data.discount_percentage,
        expiry_date=data.expiry_date,
        pickup_location=data.pickup_location,
        latitude=data.latitude,
        longitude=data.longitude,
        status=ListingStatus.AVAILABLE,
    )
    await listing.insert()

    return _to_food_listing_read(listing, str(restaurant.id))
async def list_my_listings(restaurant: User) -> list[FoodListingRead]:
    listings = await FoodListing.find(FoodListing.restaurant.id == restaurant.id).to_list()
    return [_to_food_listing_read(listing, str(restaurant.id)) for listing in listings]