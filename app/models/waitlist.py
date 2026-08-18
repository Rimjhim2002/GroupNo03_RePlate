from datetime import datetime,timezone
from typing import Optional
from beanie import Document,Link
from pydantic import Field
from app.models.enums import WaitlistStatus
from app.models.food_listing import FoodListing
from app.models.user import User


class Waitlist(Document):
    consumer:Link[User]
    food_listing:Link[FoodListing]
    position:int
    status: WaitlistStatus =WaitlistStatus.WAITING
    joined_at: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))
    notified_at: Optional[datetime] =None

    class Settings:
        name ="waitlists"