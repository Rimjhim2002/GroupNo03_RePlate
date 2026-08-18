from datetime import datetime,timezone
from beanie import Document
from pydantic import Field
class MonthlyStatistics(Document):
    month:str
    total_revenue_recovered:float =0.0
    total_waste_reduced: float =0.0
    total_meals_saved: int =0
    generated_at: datetime =Field(default_factory=lambda:datetime.now(timezone.utc))

    class Settings:
        name ="monthly_statistics"