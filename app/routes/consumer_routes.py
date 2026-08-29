from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.services import consumer_service

router = APIRouter(prefix="/api/consumer", tags=["consumer"])


@router.get("/nearby-food")
@router.get("/nearby")
@router.get("/listings/nearby")
async def nearby_food(
    radius_km: float = Query(default=5.0),
    food_name: str | None = Query(default=None),
    location: str | None = Query(default=None),
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


@router.get("/search")
@router.get("/filter")
@router.get("/listings/search")
@router.get("/listings/filter")
async def search_food_listings(
    q: str | None = Query(default=None, alias="q"),
    food_name: str | None = Query(default=None),
    max_price: float | None = Query(default=None),
    restaurant: str | None = Query(default=None),
    radius_km: float | None = Query(default=None),
    expiry_hours: float | None = Query(default=None),
    location: str | None = Query(default=None),
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


@router.post("/reserve/{listing_id}")
@router.post("/reservations/{listing_id}")
@router.post("/listings/{listing_id}/reserve")
async def reserve_listing(
    request: Request,
    listing_id: str,
    quantity: int = Query(default=1),
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    payload = {}
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    quantity_value = int(payload.get("quantity", quantity)) if isinstance(payload, dict) else int(quantity)
    try:
        return await consumer_service.reserve_food_listing(current_user, listing_id, quantity_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/waitlist/{food_listing_id}")
@router.post("/listings/{food_listing_id}/waitlist")
async def waitlist_listing(
    food_listing_id: str,
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    try:
        return await consumer_service.join_waitlist(current_user, food_listing_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/transactions")
@router.get("/history")
@router.get("/reservations/history")
async def transaction_history(
    current_user: User = Depends(require_role(UserRole.CONSUMER)),
):
    return await consumer_service.get_transaction_history(current_user)
