from datetime import datetime, timezone
from enum import Enum

from beanie import Document, Link
from pydantic import Field

from app.models.food_listing import FoodListing


class RecommendationType(str, Enum):
    DISCOUNT_SALE = "discount_sale"
    DONATE = "donate"
    URGENT_DONATE = "urgent_donate"


class FoodRecommendation(Document):
    food_listing: Link[FoodListing]
    recommendation_type: RecommendationType
    suggested_discount: float = 0.0
    priority_score: float
    confidence_score: float
    reason: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "food_recommendations"