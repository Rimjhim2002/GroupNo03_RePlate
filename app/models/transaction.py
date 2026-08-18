from datetime import datetime,timezone
from typing import Optional
from beanie import Document,Link
from pydantic import Field
from app.models.enums import TransactionStatus, TransactionType
from app.models.food_listing import FoodListing
from app.models.user import User
class Transaction(Document):
    food_listing:Link[FoodListing]
    claimed_by:Link[User]
    type:TransactionType
    quantity:int
    total_amount:float =0.0
    status:TransactionStatus
    reserved_at:Optional[datetime] = None
    completed_at:Optional[datetime] = None
    cancelled_at:Optional[datetime] = None
    created_at:datetime = Field(default_factory=lambda:datetime.now(timezone.utc))
    class Settings:
        name ="transactions"