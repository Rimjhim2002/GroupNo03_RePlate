from fastapi import APIRouter, Depends, HTTPException

from app.controllers import notification_controller
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_schema import MarkReadResponse, NotificationRead
from app.models.notification import Notification
from app.models.user import UserRole

router = APIRouter(prefix="/notifications", tags=["notifications"])
feature_router = APIRouter(prefix="/api/notifications", tags=["notifications-api"])


@router.get("/mine", response_model=list[NotificationRead])
async def get_my_notifications(current_user: User = Depends(get_current_user)):
    return await notification_controller.list_my_notifications(current_user)


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    return await notification_controller.mark_as_read(notification_id, current_user)


@feature_router.get("")
async def list_feature_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.RESTAURANT:
        raise HTTPException(status_code=403, detail="Notifications are available to restaurant accounts only.")
    notifications = await Notification.find_all().sort(-Notification.created_at).to_list()
    result = []
    for notification in notifications:
        recipient = await notification.recipient.fetch()
        if recipient is None or recipient.id != current_user.id or (unread_only and notification.is_read):
            continue
        result.append({
            "id": str(notification.id),
            "title": notification.title,
            "type": notification.type.value,
            "message": notification.message,
            "is_read": notification.is_read,
            "scheduled_for": notification.scheduled_for,
            "sent_at": notification.sent_at,
            "created_at": notification.created_at,
        })
    return result


@feature_router.patch("/{notification_id}/read")
async def mark_feature_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.RESTAURANT:
        raise HTTPException(status_code=403, detail="Notifications are available to restaurant accounts only.")
    notification = await Notification.get(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    recipient = await notification.recipient.fetch()
    if recipient is None or recipient.id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.is_read = True
    await notification.save()
    return {"id": notification_id, "is_read": True}