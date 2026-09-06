import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.controllers.food_listing_controller import expire_listings
from app.models.enums import ListingStatus, NotificationType
from app.models.food_listing import FoodListing
from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def send_expiry_alerts() -> int:
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=24)
    listings = await FoodListing.find(
        {
            "status": ListingStatus.AVAILABLE.value,
            "expiry_date": {"$gt": now, "$lte": cutoff},
        }
    ).to_list()
    created = 0
    for listing in listings:
        message = f"Listing '{listing.food_name}' ({listing.id}) expires within 24 hours."
        existing = await Notification.find_one({"message": message})
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
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Expiry monitor failed")
        await asyncio.sleep(60)