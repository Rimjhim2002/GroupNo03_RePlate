from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Link
from pydantic import Field
from app.models.user import User


class MonthlyStatistics(Document):
    restaurant: Optional[Link[User]] = None
    month: str  # Format: "YYYY-MM" (e.g. "2026-08")
    total_meals_saved: int = 0
    total_meals_donated: int = 0
    total_revenue_recovered: float = 0.0
    total_waste_reduced: float = 0.0  # percentage
    total_food_listed: int = 0
    total_food_expired: int = 0
    co2_avoided_kg: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "monthly_statistics"