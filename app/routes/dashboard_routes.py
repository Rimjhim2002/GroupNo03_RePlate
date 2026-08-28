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
from app.schemas.food_listing_schema import FoodListingRead

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


@router.get("/admin/listings/pending", response_model=list[FoodListingRead])
async def pending_listings(
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR)),
):
    return await dashboard_controller.get_pending_listings()


@router.patch("/admin/listings/{listing_id}/verify", response_model=FoodListingRead)
async def verify_listing(
    listing_id: str,
    approved: bool,
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR)),
):
    return await dashboard_controller.review_listing(listing_id, approved)


@router.get("/admin/users/pending")
async def pending_users(
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR)),
):
    return await dashboard_controller.get_pending_users()


@router.patch("/admin/users/{user_id}/verify")
async def verify_user(
    user_id: str,
    approved: bool,
    current_user: User = Depends(require_role(UserRole.ADMINISTRATOR)),
):
    return await dashboard_controller.review_user(user_id, approved)