from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification_schema import MarkReadResponse, NotificationRead

import math


from app.models.user import UserRole
from app.models.food_listing import FoodListing
def _to_notification_read(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=str(notification.id),
        title=notification.title,
        type=notification.type,
        message=notification.message,
        is_read=notification.is_read,
        sent_at=notification.sent_at,
        created_at=notification.created_at,
    )

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
async def notify_nearby_users_of_new_listing(
    listing: FoodListing,
    restaurant: User,
    radius_km: float = 10.0,
) -> int:
    if listing.latitude is None or listing.longitude is None:
        return 0

    target_role = UserRole.NGO if listing.listing_type.value == "donation" else UserRole.CONSUMER

    role_matches = await User.find(User.role == target_role).to_list()
    candidates = [u for u in role_matches if u.latitude is not None and u.longitude is not None]

    notified_count = 0
    for user in candidates:
        distance = _haversine_km(listing.latitude, listing.longitude, user.latitude, user.longitude)
        if distance <= radius_km:
            await create_notification(
                recipient=user,
                title="New food available nearby",
                type=NotificationType.DONATION_AVAILABLE if target_role == UserRole.NGO else NotificationType.NEW_LISTING_NEARBY,
                message=f"{restaurant.business_name or restaurant.name} just listed '{listing.food_name}' near you.",
            )
            notified_count += 1

    return notified_count
async def create_notification(
    recipient: User,
    title: str,
    type: NotificationType,
    message: str,
) -> Notification:
    notification = Notification(
        recipient=recipient,
        title=title,
        type=type,
        message=message,
        sent_at=datetime.now(timezone.utc),
    )
    await notification.insert()
    return notification


async def list_my_notifications(user: User) -> list[NotificationRead]:
    notifications = await Notification.find(
        Notification.recipient.id == user.id
    ).sort("-created_at").to_list()
    return [_to_notification_read(n) for n in notifications]


async def mark_as_read(notification_id: str, user: User) -> MarkReadResponse:
    notification = await Notification.get(notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")

    recipient_id = notification.recipient.ref.id if hasattr(notification.recipient, "ref") else notification.recipient.id
    if str(recipient_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This notification isn't yours.")

    notification.is_read = True
    await notification.save()
    return MarkReadResponse(id=str(notification.id), is_read=True)