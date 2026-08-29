from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.models.food_listing import FoodListing, ListingStatus
from app.models.user import User
from app.models.waitlist import Waitlist, WaitlistStatus


async def decrease_available_quantity(food_listing_id: str, quantity: int) -> FoodListing:
    """Called by the reservation/checkout flow whenever a consumer or NGO takes stock."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    if quantity > food_listing.available_quantity:
        raise ValueError("Not enough quantity available")

    food_listing.available_quantity -= quantity
    if food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.RESERVED
    food_listing.updated_at = datetime.now(timezone.utc)
    await food_listing.save()
    return food_listing


async def restore_available_quantity(food_listing_id: str, quantity: int) -> FoodListing:
    """Called when a reservation/claim is cancelled — puts stock back and re-opens the listing."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")

    food_listing.available_quantity += quantity
    if food_listing.status == ListingStatus.RESERVED and food_listing.available_quantity > 0:
        food_listing.status = ListingStatus.AVAILABLE
    food_listing.updated_at = datetime.now(timezone.utc)
    await food_listing.save()

    await notify_next_in_waitlist(food_listing_id)
    return food_listing


async def get_live_availability(food_listing_id: str) -> dict:
    """Powers the real-time quantity indicator shown on the listing page."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    return {
        "food_listing_id": str(food_listing.id),
        "available_quantity": food_listing.available_quantity,
        "status": food_listing.status,
        "last_updated": food_listing.updated_at,
    }


async def join_waitlist(consumer_id: str, food_listing_id: str) -> Waitlist:
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    consumer = await User.get(consumer_id)
    if consumer is None:
        raise ValueError("User not found")

    existing_count = await Waitlist.find(
        Waitlist.food_listing.id == food_listing.id,
        Waitlist.status == WaitlistStatus.WAITING,
    ).count()

    waitlist_entry = Waitlist(
        consumer=consumer,
        food_listing=food_listing,
        position=existing_count + 1,
    )
    await waitlist_entry.insert()
    return waitlist_entry


async def notify_next_in_waitlist(food_listing_id: str) -> Waitlist | None:
    """Auto-notifies the next consumer in line when stock frees up."""
    next_entry = await Waitlist.find(
        Waitlist.food_listing.id == PydanticObjectId(food_listing_id),
        Waitlist.status == WaitlistStatus.WAITING,
    ).sort(+Waitlist.position).first_or_none()

    if next_entry is None:
        return None

    next_entry.status = WaitlistStatus.NOTIFIED
    next_entry.notified_at = datetime.now(timezone.utc)
    await next_entry.save()

    # TODO: hook this up to whoever implements the Notification module (Module 1, feature 4)
    return next_entry