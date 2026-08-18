from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Link
from pydantic import Field
from app.models.enums import ListingStatus, ListingType
from app.models.user import User
class FoodListing(Document):
    restaurant:Link[User]
    food_name:str
    description:str
    category:str
    listing_type:ListingType=ListingType.SALE
    quantity:int
    available_quantity:int
    unit:str
    original_price:float
    discount_percentage:float=0.0
    expiry_date:datetime
    pickup_location:str
    latitude:Optional[float]=None
    longitude:Optional[float]=None
    status: ListingStatus=ListingStatus.AVAILABLE
    created_at: datetime=Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name ="food_listings"