from datetime import datetime, timezone
from typing import List, Optional

from beanie import Document, Link
from pydantic import BaseModel, Field

from app.models.enums import ListingApprovalStatus, ListingStatus, ListingType
from app.models.user import User


class PickupSlot(BaseModel):
    """Embedded sub-document — lives inside FoodListing.pickup_slots"""
    start_time: datetime
    end_time: datetime
    capacity: int
    booked_count: int = 0


class FoodListing(Document):
    restaurant: Link[User]
    food_name: str
    description: str
    category: str

    listing_type: ListingType = ListingType.SALE

    quantity: int
    available_quantity: int
    unit: str

    original_price: float
    discount_percentage: float = 0.0

    expiry_date: datetime

    pickup_location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    status: ListingStatus = ListingStatus.AVAILABLE
    approval_status: ListingApprovalStatus = ListingApprovalStatus.PENDING

    pickup_slots: List[PickupSlot] = []

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "food_listings"

    def get_remaining_shelf_life_hours(self) -> float:
        """Hours left before this listing expires (0 if already expired)."""
        expiry_date = self.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        delta = expiry_date - datetime.now(timezone.utc)
        return max(delta.total_seconds() / 3600, 0.0)

    def get_discounted_price(self) -> float:
        return round(
            self.original_price * (1 - self.discount_percentage / 100),
            2
        )