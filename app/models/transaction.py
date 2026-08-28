from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Link
from pydantic import Field

from app.models.food_listing import FoodListing
from app.models.user import User


class TransactionType(str, Enum):
    SALE = "sale"
    DONATION = "donation"


class TransactionStatus(str, Enum):
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Transaction(Document):
    food_listing: Link[FoodListing]
    claimed_by: Link[User]

    type: TransactionType
    quantity: int
    total_amount: float = 0.0

    pickup_slot_start: Optional[datetime] = None
    pickup_slot_end: Optional[datetime] = None

    status: TransactionStatus = TransactionStatus.RESERVED

    reserved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    class Settings:
        name = "transactions"