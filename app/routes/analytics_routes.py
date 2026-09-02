from fastapi import APIRouter, Depends

from app.controllers import analytics_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.schemas.analytics_schema import FoodWasteAnalyticsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/restaurant", response_model=FoodWasteAnalyticsResponse)
async def get_restaurant_waste_analytics(
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await analytics_controller.get_restaurant_waste_analytics(current_user)
