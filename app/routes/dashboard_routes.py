from fastapi import APIRouter,Depends

from app.controllers import dashboard_controller
from app.core.rbac import require_role
from app.models.user import User,UserRole
from app.schemas.dashboard_schema import (
    AdminDashboardResponse,
    ConsumerDashboardResponse,
    NGODashboardResponse,
    RestaurantDashboardResponse,
)

router =APIRouter(prefix="/dashboard", tags=["dashboard"])
@router.get("/restaurant",response_model=RestaurantDashboardResponse)
async def restaurant_dashboard(
    current_user: User =Depends(require_role(UserRole.RESTAURANT)),
):
    return await dashboard_controller.get_restaurant_dashboard(current_user)


@router.get("/consumer", response_model=ConsumerDashboardResponse)
async def consumer_dashboard(
    current_user: User =Depends(require_role(UserRole.CONSUMER)),
):
    return await dashboard_controller.get_consumer_dashboard(current_user)


@router.get("/ngo", response_model=NGODashboardResponse)
async def ngo_dashboard(
    current_user: User = Depends(require_role(UserRole.NGO)),
):
    return await dashboard_controller.get_ngo_dashboard(current_user)


@router.get("/admin", response_model=AdminDashboardResponse)
async def admin_dashboard(
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR)),
):
    return await dashboard_controller.get_admin_dashboard(current_user)