from typing import Optional
from pydantic import BaseModel
class RestaurantDashboardResponse(BaseModel):
    user_id: str
    business_name: Optional[str] = None
    active_listings: int
    active_reservations: int
    completed_transactions: int
    food_saved_count: int = 0
    meals_donated: int = 0
    revenue_recovered: float = 0.0
    waste_reduced_percentage: float = 0.0
    waste_value_avoided: float = 0.0
    total_food_listed: int = 0
class ConsumerDashboardResponse(BaseModel):
    user_id:str
    active_reservations:int
    completed_transactions:int
    meals_received:int
    money_saved:float
class NGODashboardResponse(BaseModel):
    user_id:str
    organization_name: Optional[str] =None
    active_reservations:int
    completed_transactions:int
    meals_claimed:int
    donations_fulfilled:int
class AdminDashboardResponse(BaseModel):
    user_id:str
    total_users:int
    pending_verifications:int
    pending_listings:int = 0