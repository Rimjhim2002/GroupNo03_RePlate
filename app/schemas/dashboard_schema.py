from typing import Optional
from pydantic import BaseModel
class RestaurantDashboardResponse(BaseModel):
    user_id:str
    business_name:Optional[str] =None
    active_listings:int
    active_reservations:int
    completed_transactions:int
    revenue_recovered:float
    waste_value_avoided:float
    meals_donated:int
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