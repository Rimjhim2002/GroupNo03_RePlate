from datetime import datetime,timezone
from beanie import Document,Link
from pydantic import Field
from app.models.enums import ReportFormat, ReportType
from app.models.monthly_statistics import MonthlyStatistics
class Report(Document):
    report_type:ReportType
    format:ReportFormat
    data:Link[MonthlyStatistics]
    generated_at: datetime =Field(default_factory=lambda:datetime.now(timezone.utc))



    class Settings:
        name = "reports"