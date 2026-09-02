from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationRead(BaseModel):
    id: str
    title: str
    type: NotificationType
    message: str
    is_read: bool
    sent_at: Optional[datetime] = None
    created_at: datetime


class MarkReadResponse(BaseModel):
    id: str
    is_read: bool