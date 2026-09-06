from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.controllers import consumer_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.services import consumer_service

router = APIRouter(prefix="/consumer", tags=["consumer"])
feature_router = APIRouter(prefix="/api/consumer", tags=["consumer-api"])


@router.get("/search")
async def search_food_listings(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    max_distance_km: Optional[float] = Query(default=None),
    location: Optional[str] = Query(default=None),
    max_expiry_hours: Optional[float] = Query(default=None),
    current_user: User = Depends(require_role(UserRole.CONSUMER, UserRole.RESTAURANT, UserRole.NGO, UserRole.ADMINISTRATOR)),
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


@feature_router.get("/nearby-food")
@feature_router.get("/nearby")
@feature_router.get("/listings/nearby")
async def nearby_food(
    radius_km: float = Query(default=5.0),
    food_name: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    try:
        return await consumer_service.get_nearby_food(
            current_user,
            radius_km=radius_km,
            food_name=food_name,
            location=location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@feature_router.get("/filter")
@feature_router.get("/search")
@feature_router.get("/listings/search")
@feature_router.get("/listings/filter")
async def feature_search_food_listings(
    q: Optional[str] = Query(default=None),
    food_name: Optional[str] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    restaurant: Optional[str] = Query(default=None),
    radius_km: Optional[float] = Query(default=None),
    expiry_hours: Optional[float] = Query(default=None),
    location: Optional[str] = Query(default=None),
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    try:
        return await consumer_service.search_food_listings(
            current_user,
            search_term=q,
            food_name=food_name,
            max_price=max_price,
            restaurant=restaurant,
            radius_km=radius_km,
            expiry_hours=expiry_hours,
            location=location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@feature_router.post("/reserve/{listing_id}")
@feature_router.post("/reservations/{listing_id}")
@feature_router.post("/listings/{listing_id}/reserve")
async def feature_reserve_listing(
    request: Request,
    listing_id: str,
    quantity: int = Query(default=1),
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        pass
    quantity_value = int(payload.get("quantity", quantity)) if isinstance(payload, dict) else int(quantity)
    try:
        return await consumer_service.reserve_food_listing(current_user, listing_id, quantity_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@feature_router.post("/waitlist/{food_listing_id}")
@feature_router.post("/listings/{food_listing_id}/waitlist")
async def feature_waitlist_listing(
    food_listing_id: str,
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    try:
        return await consumer_service.join_waitlist(current_user, food_listing_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@feature_router.get("/transactions")
@feature_router.get("/history")
@feature_router.get("/reservations/history")
async def feature_transaction_history(
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    return await consumer_service.get_transaction_history(current_user)


@feature_router.post("/orders/{transaction_id}/complete")
@feature_router.post("/transactions/{transaction_id}/complete")
async def feature_complete_order(
    transaction_id: str,
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    try:
        transaction = await consumer_service.mark_order_completed(transaction_id, current_user)
        return {"transaction_id": str(transaction.id), "status": transaction.status}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
