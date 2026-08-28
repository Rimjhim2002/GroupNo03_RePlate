import asyncio
from datetime import datetime, timedelta, timezone

from app.controllers.food_listing_controller import expire_listings
from app.models.enums import ListingStatus, NotificationType
from app.models.food_listing import FoodListing
from app.models.notification import Notification


async def send_expiry_alerts() -> int:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=24)
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
        FoodListing.expiry_date <= cutoff,
        FoodListing.expiry_date > now,
    ).to_list()
    created = 0
    for listing in listings:
        message = f"Listing '{listing.food_name}' ({listing.id}) expires within 24 hours."
        existing = await Notification.find_one(
            Notification.type == NotificationType.EXPIRY_ALERT,
            Notification.recipient.id == listing.restaurant.ref.id,
            Notification.message == message,
        )
        if not existing:
            await Notification(
                recipient=listing.restaurant,
                title="Food listing expires soon",
                type=NotificationType.EXPIRY_ALERT,
                message=message,
                scheduled_for=listing.expiry_date,
                sent_at=now,
            ).insert()
            created += 1
    await expire_listings()
    return created


async def monitor_expiry() -> None:
    while True:
        try:
            await send_expiry_alerts()
        except Exception:
            pass
        await asyncio.sleep(60)