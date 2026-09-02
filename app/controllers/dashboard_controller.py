from app.controllers.food_listing_controller import (
    list_pending_listings,
    review_listing as review_food_listing,
)
from app.models.enums import ListingApprovalStatus, ListingStatus
from app.models.food_listing import FoodListing
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User, VerificationStatus


async def get_restaurant_dashboard(user: User) -> dict:
    listings = await FoodListing.find(FoodListing.restaurant.id == user.id).to_list()
    listing_map = {l.id: l for l in listings}
    listing_id_set = set(listing_map.keys())

    transactions = await Transaction.find_all().to_list()
    restaurant_transactions = [
        t for t in transactions
        if (t.food_listing.ref.id if hasattr(t.food_listing, "ref") else getattr(t.food_listing, "id", None)) in listing_id_set
    ]

    total_food_listed = sum(l.quantity for l in listings)
    completed_txs = [
        t for t in restaurant_transactions
        if getattr(t.status, "value", t.status) == "completed"
    ]
    completed_sales = [
        t for t in completed_txs
        if getattr(t.type, "value", t.type) == "sale"
    ]
    completed_donations = [
        t for t in completed_txs
        if getattr(t.type, "value", t.type) == "donation"
    ]

    food_saved_count = sum(t.quantity for t in completed_txs)
    meals_donated = sum(t.quantity for t in completed_donations)
    revenue_recovered = round(sum(float(t.total_amount) for t in completed_sales), 2)
    waste_reduced_percentage = (
        round((food_saved_count / total_food_listed) * 100, 1)
        if total_food_listed > 0
        else 0.0
    )

    waste_value_avoided = round(
        sum(
            listing_map[
                t.food_listing.ref.id if hasattr(t.food_listing, "ref") else t.food_listing.id
            ].original_price * t.quantity
            for t in completed_txs
            if (t.food_listing.ref.id if hasattr(t.food_listing, "ref") else t.food_listing.id) in listing_map
        ),
        2,
    )

    return {
        "user_id": str(user.id),
        "business_name": user.business_name or user.name,
        "active_listings": sum(1 for l in listings if l.status == ListingStatus.AVAILABLE),
        "active_reservations": sum(1 for t in restaurant_transactions if getattr(t.status, "value", t.status) == "reserved"),
        "completed_transactions": len(completed_txs),
        "total_food_listed": total_food_listed,
        "food_saved_count": food_saved_count,
        "meals_donated": meals_donated,
        "revenue_recovered": revenue_recovered,
        "waste_reduced_percentage": waste_reduced_percentage,
        "waste_value_avoided": waste_value_avoided,
    }


async def get_consumer_dashboard(user: User) -> dict:
    transactions = await Transaction.find(
        Transaction.claimed_by.id == user.id,
        Transaction.type == TransactionType.SALE,
    ).to_list()
    active_transactions = [transaction for transaction in transactions if transaction.status == TransactionStatus.RESERVED]
    completed_transactions = [transaction for transaction in transactions if transaction.status == TransactionStatus.COMPLETED]
    return {
        "user_id": str(user.id),
        "active_reservations": len(active_transactions),
        "completed_transactions": len(completed_transactions),
        "meals_received": sum(transaction.quantity for transaction in completed_transactions),
        "money_saved": round(sum(float(transaction.total_amount) for transaction in completed_transactions), 2),
    }


async def get_ngo_dashboard(user: User) -> dict:
    transactions = await Transaction.find(
        Transaction.claimed_by.id == user.id,
        Transaction.type == TransactionType.DONATION,
    ).to_list()
    active_statuses = {TransactionStatus.RESERVED, TransactionStatus.CONFIRMED}
    active_transactions = [transaction for transaction in transactions if transaction.status in active_statuses]
    completed_transactions = [transaction for transaction in transactions if transaction.status == TransactionStatus.COMPLETED]
    return {
        "user_id": str(user.id),
        "organization_name": user.organization_name or user.name,
        "active_reservations": len(active_transactions),
        "completed_transactions": len(completed_transactions),
        "meals_claimed": sum(transaction.quantity for transaction in transactions),
        "donations_fulfilled": sum(transaction.quantity for transaction in completed_transactions),
    }


async def get_admin_dashboard(user: User) -> dict:
    total_users = await User.find_all().count()
    pending = await User.find(User.verification_status == "pending").count()
    pending_listings = await FoodListing.find(FoodListing.approval_status == ListingApprovalStatus.PENDING).count()
    return {
        "user_id": str(user.id),
        "total_users": total_users,
        "pending_verifications": pending,
        "pending_listings": pending_listings,
    }


async def get_pending_listings():
    return await list_pending_listings()


async def review_listing(listing_id: str, approved: bool):
    return await review_food_listing(listing_id, approved)


async def get_pending_users() -> list[dict]:
    users = await User.find(User.verification_status == VerificationStatus.PENDING).to_list()
    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": str(user.email),
            "role": user.role.value,
            "business_name": user.business_name,
            "organization_name": user.organization_name,
        }
        for user in users
    ]


async def review_user(user_id: str, approved: bool) -> dict:
    user = await User.get(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found.")
    user.verification_status = (
        VerificationStatus.VERIFIED if approved else VerificationStatus.REJECTED
    )
    await user.save()
    return {"id": str(user.id), "verification_status": user.verification_status}