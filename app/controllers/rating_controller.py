from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, status

from app.controllers.notification_controller import create_notification
from app.models.enums import NotificationType, TransactionStatus
from app.models.food_listing import FoodListing
from app.models.rating import Rating
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.rating_schema import RatingCreate, RatingRead, UserRatingSummary


def _get_id(doc_or_ref: Any) -> str:
    if hasattr(doc_or_ref, "ref"):
        return str(doc_or_ref.ref.id)
    if hasattr(doc_or_ref, "id"):
        return str(doc_or_ref.id)
    return str(doc_or_ref)


async def submit_rating(data: RatingCreate, current_user: User) -> RatingRead:
    transaction = await Transaction.get(data.transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )

    # 1. Ensure transaction is completed
    tx_status = getattr(transaction.status, "value", transaction.status)
    if tx_status != TransactionStatus.COMPLETED.value and tx_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only rate and review completed transactions."
        )

    # 2. Fetch listing & users
    listing = await FoodListing.get(_get_id(transaction.food_listing))
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food listing associated with this transaction was not found."
        )

    restaurant_user = await User.get(_get_id(listing.restaurant))
    buyer_user = await User.get(_get_id(transaction.claimed_by))

    if not restaurant_user or not buyer_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Users associated with this transaction could not be resolved."
        )

    current_uid = str(current_user.id)
    buyer_uid = str(buyer_user.id)
    rest_uid = str(restaurant_user.id)

    # 3. Determine recipient and verify participation
    if current_uid == buyer_uid:
        to_user = restaurant_user
    elif current_uid == rest_uid:
        to_user = buyer_user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this transaction."
        )

    # 4. Check for duplicate review
    existing_rating = await Rating.find_one(
        Rating.transaction.id == transaction.id,
        Rating.from_user.id == current_user.id,
    )
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted feedback for this transaction."
        )

    # 5. Create and save rating
    rating = Rating(
        from_user=current_user,
        to_user=to_user,
        transaction=transaction,
        stars=data.stars,
        review=data.review.strip(),
        created_at=datetime.now(timezone.utc),
    )
    await rating.insert()

    # 6. Send RATING_RECEIVED notification to to_user
    sender_name = current_user.name
    star_emojis = "⭐" * data.stars
    await create_notification(
        recipient=to_user,
        title="New Rating & Feedback Received",
        type=NotificationType.RATING_RECEIVED,
        message=f"{sender_name} rated you {data.stars}/5 stars ({star_emojis}): \"{data.review.strip()}\"",
    )

    return RatingRead(
        id=str(rating.id),
        from_user_id=str(current_user.id),
        from_user_name=current_user.name,
        to_user_id=str(to_user.id),
        to_user_name=to_user.business_name or to_user.organization_name or to_user.name,
        transaction_id=str(transaction.id),
        stars=rating.stars,
        review=rating.review,
        created_at=rating.created_at,
    )


async def get_user_ratings(target_user_id: str) -> UserRatingSummary:
    user = await User.get(target_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    ratings = await Rating.find(Rating.to_user.id == user.id).sort("-created_at").to_list()

    star_breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_stars = 0
    read_items: list[RatingRead] = []

    for r in ratings:
        from_u = await User.get(_get_id(r.from_user))
        star_breakdown[r.stars] = star_breakdown.get(r.stars, 0) + 1
        total_stars += r.stars
        read_items.append(
            RatingRead(
                id=str(r.id),
                from_user_id=_get_id(r.from_user),
                from_user_name=from_u.name if from_u else "Verified User",
                to_user_id=str(user.id),
                to_user_name=user.business_name or user.organization_name or user.name,
                transaction_id=_get_id(r.transaction),
                stars=r.stars,
                review=r.review,
                created_at=r.created_at,
            )
        )

    total_count = len(ratings)
    avg_stars = round(total_stars / total_count, 1) if total_count > 0 else 0.0

    return UserRatingSummary(
        user_id=str(user.id),
        user_name=user.business_name or user.organization_name or user.name,
        role=user.role.value,
        average_stars=avg_stars,
        total_ratings=total_count,
        star_breakdown=star_breakdown,
        ratings=read_items,
    )


async def get_my_submitted_ratings(current_user: User) -> list[RatingRead]:
    ratings = await Rating.find(Rating.from_user.id == current_user.id).sort("-created_at").to_list()
    read_items: list[RatingRead] = []
    for r in ratings:
        to_u = await User.get(_get_id(r.to_user))
        read_items.append(
            RatingRead(
                id=str(r.id),
                from_user_id=str(current_user.id),
                from_user_name=current_user.name,
                to_user_id=_get_id(r.to_user),
                to_user_name=to_u.business_name or to_u.organization_name or to_u.name if to_u else "User",
                transaction_id=_get_id(r.transaction),
                stars=r.stars,
                review=r.review,
                created_at=r.created_at,
            )
        )
    return read_items
