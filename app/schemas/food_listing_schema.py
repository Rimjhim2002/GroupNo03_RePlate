from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.enums import ListingStatus, ListingType


class FoodListingCreate(BaseModel):
    food_name:str
    description: str
    category: str
    listing_type: ListingType =ListingType.SALE
    quantity:int
    unit:str
    original_price:float
    discount_percentage: float =0.0
    expiry_date:datetime
    pickup_location: str
    latitude: Optional[float] =None
    longitude: Optional[float] =None


class FoodListingRead(BaseModel):
    id:str
    restaurant_id:str
    food_name:str
    description:str
    category:str
    listing_type:ListingType
    quantity:int
    available_quantity:int
    unit:str
    original_price:float
    discount_percentage:float
    discounted_price:float
    expiry_date:datetime
    pickup_location:str
    status:ListingStatus
    created_at:datetime