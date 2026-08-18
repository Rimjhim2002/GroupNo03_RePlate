from datetime import datetime,timezone
from typing import Optional
from beanie import Document,Link
from pydantic import Field
from app.models.enums import NotificationType
from app.models.user import User


class Notification(Document):
    recipient:Link[User]
    title:str
    type:NotificationType
    message:str
    is_read: bool =False
    scheduled_for: Optional[datetime] =None
    sent_at: Optional[datetime] =None
    created_at: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name ="notifications"