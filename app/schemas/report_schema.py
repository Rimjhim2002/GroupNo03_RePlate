from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.enums import ReportFormat, ReportType


class MonthlyReportGenerateRequest(BaseModel):
    month: Optional[str] = None  # Format: "YYYY-MM", defaults to current month
    format: ReportFormat = ReportFormat.PDF


class MonthlyStatisticsRead(BaseModel):
    id: str
    month: str
    restaurant_name: str
    total_meals_saved: int
    total_meals_donated: int
    total_revenue_recovered: float
    total_waste_reduced: float
    total_food_listed: int
    total_food_expired: int
    co2_avoided_kg: float
    generated_at: datetime


class ReportRead(BaseModel):
    id: str
    report_type: ReportType
    format: ReportFormat
    month: str
    restaurant_name: str
    statistics: MonthlyStatisticsRead
    generated_at: datetime
