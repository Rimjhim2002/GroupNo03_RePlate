from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RatingCreate(BaseModel):
    transaction_id: str
    stars: int = Field(ge=1, le=5, description="Star rating from 1 to 5")
    review: str = Field(min_length=1, max_length=1000, description="Written feedback review")


class RatingRead(BaseModel):
    id: str
    from_user_id: str
    from_user_name: str
    to_user_id: str
    to_user_name: str
    transaction_id: str
    stars: int
    review: str
    created_at: datetime


class UserRatingSummary(BaseModel):
    user_id: str
    user_name: str
    role: str
    average_stars: float
    total_ratings: int
    star_breakdown: Dict[int, int]
    ratings: List[RatingRead]
