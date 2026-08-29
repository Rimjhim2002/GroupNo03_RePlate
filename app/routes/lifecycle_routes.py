from datetime import datetime
from typing import Optional
 
from fastapi import APIRouter, Depends, HTTPException
 
from app.models.user import User
from app.services import (
    recommendation_service,
    prioritization_service,
    ngo_service,
    availability_service,
    pickup_service,
)
 
# TODO: point this at whichever auth dependency the team actually builds
from app.core.dependencies import get_current_user
from app.core.rbac import require_role
from app.models.user import UserRole
 
router = APIRouter(prefix="/api/lifecycle", tags=["Lifecycle & NGO"])
 
 
# ---------- Smart Food Lifecycle Recommendation ----------
@router.get("/listings/{food_listing_id}/recommendation")
async def get_recommendation(food_listing_id: str):
    recommendation = await recommendation_service.get_latest_recommendation(food_listing_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="No recommendation found for this listing")
    return recommendation
 
 
@router.post("/recommendations/refresh")
async def refresh_recommendations():
    recommendations = await recommendation_service.generate_recommendations_for_all_active_listings()
    return {"generated": len(recommendations)}
 
 
# ---------- Expiry-Based Food Prioritization ----------
@router.get("/listings/prioritized")
async def prioritized_listings(restaurant_id: Optional[str] = None):
    return await prioritization_service.get_prioritized_listings(restaurant_id=restaurant_id)
 
 
@router.get("/listings/urgent")
async def urgent_listings(hours: float = 6):
    return await prioritization_service.get_urgent_listings(hours_threshold=hours)
 
 
# ---------- NGO Food Claiming ----------
@router.get("/ngo/donations")
async def browse_donations():
    return await ngo_service.browse_available_donations()
 
 
@router.post("/ngo/donations/{food_listing_id}/claim")
async def claim_donation(food_listing_id: str, quantity: int, current_user: User = Depends(get_current_user)):
    try:
        return await ngo_service.claim_donation(current_user, food_listing_id, quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
 
@router.get("/ngo/claims")
async def my_claims(current_user: User = Depends(get_current_user)):
    return await ngo_service.get_ngo_claims(current_user)
 
 
@router.post("/ngo/claims/{transaction_id}/complete")
async def complete_claim(transaction_id: str):
    try:
        return await ngo_service.mark_donation_completed(transaction_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
 
# ---------- Real-Time Food Availability Tracking ----------
@router.get("/listings/{food_listing_id}/availability")
async def live_availability(food_listing_id: str):
    try:
        return await availability_service.get_live_availability(food_listing_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
 
 
@router.post("/listings/{food_listing_id}/waitlist")
async def join_waitlist(food_listing_id: str, current_user: User = Depends(get_current_user)):
    return await availability_service.join_waitlist(str(current_user.id), food_listing_id)
 
 
# ---------- Pickup Time Slot Management ----------
@router.post("/listings/{food_listing_id}/pickup-slots")
async def add_slot(
    food_listing_id: str,
    start_time: datetime,
    end_time: datetime,
    capacity: int,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    try:
        return await pickup_service.add_pickup_slot(food_listing_id, start_time, end_time, capacity, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
 
@router.get("/listings/{food_listing_id}/pickup-slots")
async def list_slots(food_listing_id: str):
    try:
        return await pickup_service.get_available_slots(food_listing_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
 
 
@router.post("/listings/{food_listing_id}/pickup-slots/{slot_index}/book")
async def book_slot(food_listing_id: str, slot_index: int):
    try:
        return await pickup_service.book_pickup_slot(food_listing_id, slot_index)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))