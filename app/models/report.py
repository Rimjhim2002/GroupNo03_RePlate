from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Link
from pydantic import Field
from app.models.enums import ReportFormat, ReportType
from app.models.monthly_statistics import MonthlyStatistics
from app.models.user import User


class Report(Document):
    restaurant: Optional[Link[User]] = None
    report_type: ReportType = ReportType.IMPACT_REPORT
    format: ReportFormat = ReportFormat.PDF
    month: str = ""
    data: Link[MonthlyStatistics]
    content: Optional[str] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reports"