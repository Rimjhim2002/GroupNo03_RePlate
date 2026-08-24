from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FoodListing(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None

    food_name: str = Field(
        min_length=1,
        max_length=100
    )

    quantity: int = Field(
        gt=0
    )

    category: str

    expiry_time: datetime

    original_price: float = Field(
        gt=0
    )

    discounted_price: float = Field(
        gt=0
    )

    pickup_location: str

    restaurant_id: str

    status: str = "available"

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
