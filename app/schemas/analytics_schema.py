from typing import List, Optional
from pydantic import BaseModel


class CategoryDistributionItem(BaseModel):
    category: str
    total_listed: int
    rescued_units: int
    wasted_units: int
    rescue_rate_percentage: float
    revenue_recovered: float


class TrendDataPoint(BaseModel):
    period_label: str
    sale_units: int
    donation_units: int
    expired_units: int
    revenue_recovered: float


class WasteSummaryInsight(BaseModel):
    total_surplus_listed: int
    total_rescued_units: int
    total_wasted_units: int
    overall_rescue_rate: float
    total_revenue_recovered: float
    potential_revenue_lost: float
    co2_avoided_kg: float


class FoodWasteAnalyticsResponse(BaseModel):
    restaurant_id: str
    restaurant_name: str
    summary: WasteSummaryInsight
    categories: List[CategoryDistributionItem]
    trends: List[TrendDataPoint]
    insights: List[str]
