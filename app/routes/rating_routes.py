from fastapi import APIRouter, Depends

from app.controllers import rating_controller
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.rating_schema import RatingCreate, RatingRead, UserRatingSummary

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("/", response_model=RatingRead)
async def submit_rating(
    data: RatingCreate,
    current_user: User = Depends(get_current_user),
):
    return await rating_controller.submit_rating(data, current_user)


@router.get("/user/{user_id}", response_model=UserRatingSummary)
async def get_user_ratings(user_id: str):
    return await rating_controller.get_user_ratings(user_id)


@router.get("/mine", response_model=list[RatingRead])
async def get_my_submitted_ratings(
    current_user: User = Depends(get_current_user),
):
    return await rating_controller.get_my_submitted_ratings(current_user)
