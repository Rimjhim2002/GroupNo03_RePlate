from datetime import datetime,timezone
from beanie import Document,Link
from pydantic import Field
from app.models.enums import RecommendationType
from app.models.food_listing import FoodListing
class FoodRecommendation(Document):
    food_listing:Link[FoodListing]
    recommendation_type:RecommendationType
    suggested_discount:float
    priority_score:int
    confidence_score:float
    reason:str
    generated_at: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "food_recommendations"