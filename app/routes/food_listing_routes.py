from fastapi import APIRouter, Depends

from app.controllers import food_listing_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.schemas.food_listing_schema import (
    FoodListingCreate,
    FoodListingClaim,
    FoodListingDiscountUpdate,
    FoodListingRead,
    FoodListingStatusUpdate,
)

router = APIRouter(prefix="/listings", tags=["food_listings"])


@router.get("/available", response_model=list[FoodListingRead])
async def get_available_listings():
    return await food_listing_controller.list_available_listings()


@router.post("/{listing_id}/claim")
async def claim_listing(
    listing_id: str,
    data: FoodListingClaim,
    current_user: User = Depends(require_role(UserRole.CONSUMER, UserRole.NGO)),
):
    return await food_listing_controller.claim_listing(listing_id, data.quantity, current_user)


@router.post("/", response_model=FoodListingRead)
async def create_listing(
    data: FoodListingCreate,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await food_listing_controller.create_listing(data,current_user)
@router.get("/mine", response_model=list[FoodListingRead])
async def get_my_listings(
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await food_listing_controller.list_my_listings(current_user)


@router.patch("/{listing_id}/discount", response_model=FoodListingRead)
async def update_discount(
    listing_id: str,
    data: FoodListingDiscountUpdate,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await food_listing_controller.update_discount(listing_id, data, current_user)


@router.get("/{listing_id}/discount-suggestion")
async def discount_suggestion(
    listing_id: str,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    listing = await food_listing_controller.get_owned_listing(listing_id, current_user)
    suggested = food_listing_controller.suggested_discount_percentage(listing)
    return {"discount_percentage": suggested, "remaining_shelf_life_hours": listing.get_remaining_shelf_life_hours()}


@router.patch("/{listing_id}/status", response_model=FoodListingRead)
async def update_status(
    listing_id: str,
    data: FoodListingStatusUpdate,
    current_user: User = Depends(require_role(UserRole.RESTAURANT)),
):
    return await food_listing_controller.update_status(listing_id, data, current_user)