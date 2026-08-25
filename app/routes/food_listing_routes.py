from fastapi import APIRouter, Depends

from app.controllers import food_listing_controller
from app.core.rbac import require_role
from app.models.user import User, UserRole
from app.schemas.food_listing_schema import FoodListingCreate, FoodListingRead

router = APIRouter(prefix="/listings", tags=["food_listings"])


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