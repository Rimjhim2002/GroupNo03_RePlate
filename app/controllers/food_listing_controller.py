from datetime import datetime, timezone

from beanie.operators import Or
from fastapi import HTTPException,status
from app.models.enums import ListingApprovalStatus, ListingStatus, ListingType, NotificationType
from app.models.food_listing import FoodListing
from app.models.notification import Notification
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User, UserRole, VerificationStatus
from app.schemas.food_listing_schema import (
    FoodListingCreate,
    FoodListingDiscountUpdate,
    FoodListingRead,
    FoodListingStatusUpdate,
)

from app.controllers.notification_controller import notify_nearby_users_of_new_listing
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
        approval_status=listing.approval_status,
        created_at=listing.created_at,
    )


async def create_listing(data: FoodListingCreate, restaurant: User) -> FoodListingRead:
    if restaurant.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your restaurant account must be verified before creating listings.",
        )

    listing_latitude = data.latitude if data.latitude is not None else restaurant.latitude
    listing_longitude = data.longitude if data.longitude is not None else restaurant.longitude

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
        latitude=listing_latitude,
        longitude=listing_longitude,
        status=ListingStatus.AVAILABLE,
    )
    await listing.insert()

    await notify_nearby_users_of_new_listing(listing, restaurant)

    return _to_food_listing_read(listing, str(restaurant.id))
async def list_my_listings(restaurant: User) -> list[FoodListingRead]:
    listings = await FoodListing.find(FoodListing.restaurant.id == restaurant.id).to_list()
    await expire_listings(listings)
    return [_to_food_listing_read(listing, str(restaurant.id)) for listing in listings]


async def list_available_listings() -> list[FoodListingRead]:
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
        FoodListing.approval_status == ListingApprovalStatus.APPROVED,
    ).to_list()
    await expire_listings(listings)
    for listing in listings:
        if listing.status != ListingStatus.AVAILABLE:
            continue
        suggested = suggested_discount_percentage(listing)
        if suggested > listing.discount_percentage:
            listing.discount_percentage = suggested
            listing.updated_at = datetime.now(timezone.utc)
            await listing.save()
    return [
        _to_food_listing_read(listing, str(listing.restaurant.ref.id))
        for listing in listings
        if listing.status == ListingStatus.AVAILABLE
    ]


async def list_pending_listings() -> list[FoodListingRead]:
    listings = await FoodListing.find(
        FoodListing.approval_status == ListingApprovalStatus.PENDING
    ).to_list()
    return [_to_food_listing_read(listing, str(listing.restaurant.ref.id)) for listing in listings]


async def review_listing(listing_id: str, approved: bool) -> FoodListingRead:
    listing = await FoodListing.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    listing.approval_status = (
        ListingApprovalStatus.APPROVED if approved else ListingApprovalStatus.REJECTED
    )
    listing.updated_at = datetime.now(timezone.utc)
    await listing.save()
    return _to_food_listing_read(listing, str(listing.restaurant.ref.id))


def suggested_discount_percentage(listing: FoodListing) -> float:
    hours = listing.get_remaining_shelf_life_hours()
    if hours <= 0:
        return 100.0
    if hours <= 6:
        return 50.0
    if hours <= 24:
        return 30.0
    if hours <= 48:
        return 15.0
    return 0.0


async def get_owned_listing(listing_id: str, restaurant: User) -> FoodListing:
    listing = await FoodListing.get(listing_id)
    if not listing or listing.restaurant.ref.id != restaurant.id:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return listing


async def update_discount(
    listing_id: str, data: FoodListingDiscountUpdate, restaurant: User
) -> FoodListingRead:
    if not 0 <= data.discount_percentage <= 100:
        raise HTTPException(status_code=400, detail="Discount must be between 0 and 100.")
    listing = await get_owned_listing(listing_id, restaurant)
    listing.discount_percentage = data.discount_percentage
    listing.updated_at = datetime.now(timezone.utc)
    await listing.save()
    return _to_food_listing_read(listing, str(restaurant.id))


async def update_status(
    listing_id: str, data: FoodListingStatusUpdate, restaurant: User
) -> FoodListingRead:
    listing = await get_owned_listing(listing_id, restaurant)
    allowed_transitions = {
        ListingStatus.AVAILABLE: {ListingStatus.RESERVED, ListingStatus.EXPIRED},
        ListingStatus.RESERVED: {ListingStatus.SOLD_DONATED, ListingStatus.COMPLETED, ListingStatus.AVAILABLE},
        ListingStatus.SOLD_DONATED: {ListingStatus.COMPLETED},
        ListingStatus.COMPLETED: set(),
        ListingStatus.EXPIRED: set(),
    }
    if data.status != listing.status and data.status not in allowed_transitions[listing.status]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move a listing from {listing.status.value} to {data.status.value}.",
        )
    listing.status = data.status
    listing.updated_at = datetime.now(timezone.utc)
    await listing.save()
    return _to_food_listing_read(listing, str(restaurant.id))


async def expire_listings(listings: list[FoodListing] | None = None) -> int:
    if listings is None:
        listings = await FoodListing.find(
            FoodListing.status == ListingStatus.AVAILABLE
        ).to_list()
    expired = 0
    now = datetime.now(timezone.utc)
    for listing in listings:
        expiry = listing.expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if listing.status == ListingStatus.AVAILABLE and expiry <= now:
            listing.status = ListingStatus.EXPIRED
            listing.updated_at = now
            await listing.save()
            expired += 1
    return expired


async def claim_listing(listing_id: str, quantity: int, user: User) -> dict:
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1.")
    if user.role == UserRole.NGO and user.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="NGO accounts must be verified before claiming donations.")

    listing = await FoodListing.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if listing.approval_status != ListingApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="This listing is awaiting administrator approval.")
    if listing.status != ListingStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="This listing is no longer available.")
    if listing.get_remaining_shelf_life_hours() <= 0:
        await expire_listings([listing])
        raise HTTPException(status_code=400, detail="This listing has expired.")
    if quantity > listing.available_quantity:
        raise HTTPException(status_code=400, detail=f"Only {listing.available_quantity} {listing.unit} available.")
    if user.role == UserRole.CONSUMER and listing.listing_type != ListingType.SALE:
        raise HTTPException(status_code=400, detail="Consumers can purchase sale listings only.")
    if user.role == UserRole.NGO and listing.listing_type != ListingType.DONATION:
        raise HTTPException(status_code=400, detail="NGOs can claim donation listings only.")

    listing.available_quantity -= quantity
    if listing.available_quantity == 0:
        listing.status = ListingStatus.RESERVED
    listing.updated_at = datetime.now(timezone.utc)
    await listing.save()

    transaction = Transaction(
        food_listing=listing,
        claimed_by=user,
        type=TransactionType.SALE if user.role == UserRole.CONSUMER else TransactionType.DONATION,
        quantity=quantity,
        total_amount=quantity * listing.get_discounted_price() if user.role == UserRole.CONSUMER else 0.0,
        status=TransactionStatus.RESERVED,
    )
    await transaction.insert()
    return {
        "transaction_id": str(transaction.id),
        "listing_id": str(listing.id),
        "quantity": quantity,
        "status": transaction.status,
        "total_amount": transaction.total_amount,
        "message": "Food reserved successfully. Collect it at the pickup location.",
    }