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
    transactions = await Transaction.find_all().to_list()
    restaurant_listing_ids = {listing.id for listing in listings}
    restaurant_transactions = [
        transaction
        for transaction in transactions
        if transaction.food_listing.ref.id in restaurant_listing_ids
    ]
    return {
        "user_id": str(user.id),
        "business_name": user.business_name,
        "active_listings": sum(l.status == ListingStatus.AVAILABLE for l in listings),
        "active_reservations": sum(t.status.value == "reserved" for t in restaurant_transactions),
        "completed_transactions": sum(t.status.value == "completed" for t in restaurant_transactions),
        "revenue_recovered": round(sum(t.total_amount for t in restaurant_transactions if t.status.value == "completed"), 2),
        "waste_value_avoided": round(sum(l.original_price * l.quantity for l in listings if l.status != ListingStatus.EXPIRED), 2),
        "meals_donated": sum(t.quantity for t in restaurant_transactions if t.type.value == "donation" and t.status.value == "completed")
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
        "user_id":str(user.id),
        "organization_name":user.organization_name,
        "active_reservations": len(active_transactions),
        "completed_transactions": len(completed_transactions),
        "meals_claimed": sum(transaction.quantity for transaction in transactions),
        "donations_fulfilled": sum(transaction.quantity for transaction in completed_transactions),
    }

async def get_admin_dashboard(user: User) -> dict:
    total_users = await User.find_all().count()
    pending =await User.find(User.verification_status == "pending").count()
    pending_listings = await FoodListing.find(FoodListing.approval_status == ListingApprovalStatus.PENDING).count()
    return {
        "user_id":str(user.id),
        "total_users":total_users,
        "pending_verifications":pending
        ,"pending_listings": pending_listings
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