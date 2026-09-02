from fastapi import APIRouter, Depends

from app.controllers import notification_controller
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification_schema import MarkReadResponse, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/mine", response_model=list[NotificationRead])
async def get_my_notifications(current_user: User = Depends(get_current_user)):
    return await notification_controller.list_my_notifications(current_user)


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    return await notification_controller.mark_as_read(notification_id, current_user)