from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.controllers import consumer_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole

router = APIRouter(prefix="/consumer", tags=["consumer"])


@router.get("/search")
async def search_food_listings(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    max_distance_km: Optional[float] = Query(default=None),
    location: Optional[str] = Query(default=None),
    max_expiry_hours: Optional[float] = Query(default=None),
    current_user: User = Depends(require_role(UserRole.CONSUMER, UserRole.RESTAURANT, UserRole.NGO)),
):
    return await consumer_controller.search_consumer_listings(
        current_user,
        search_term=search,
        category=category,
        max_price=max_price,
        max_distance_km=max_distance_km,
        location_term=location,
        max_expiry_hours=max_expiry_hours,
    )


@router.post("/listings/{listing_id}/reserve")
async def reserve_food_listing(
    listing_id: str,
    quantity: int = 1,
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    return await consumer_controller.reserve_listing_for_consumer(listing_id, quantity, current_user)


@router.post("/listings/{listing_id}/waitlist")
async def waitlist_food_listing(
    listing_id: str,
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    return await consumer_controller.join_waitlist_for_consumer(listing_id, current_user)


@router.get("/history")
async def consumer_history(
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    return await consumer_controller.get_consumer_history(current_user)
