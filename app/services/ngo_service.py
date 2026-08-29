from datetime import datetime, timezone

from app.models.user import User, UserRole, VerificationStatus
from app.models.food_listing import FoodListing, ListingApprovalStatus, ListingStatus, ListingType
from app.models.transaction import Transaction, TransactionType, TransactionStatus


async def browse_available_donations() -> list[FoodListing]:
    """NGOs browse listings that are still available, soonest-to-expire first.
    TODO: add a geo/distance filter once location-based query support is added."""
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
        FoodListing.approval_status == ListingApprovalStatus.APPROVED,
        FoodListing.listing_type == ListingType.DONATION,
    ).sort(+FoodListing.expiry_date).to_list()
    return listings


async def claim_donation(ngo: User, food_listing_id: str, quantity: int) -> Transaction:
    """A verified NGO claims (part of) a surplus food listing for donation."""
    if ngo.role != UserRole.NGO:
        raise ValueError("Only NGO accounts can claim donations")
    if ngo.verification_status != VerificationStatus.VERIFIED:
        raise ValueError("NGO account must be verified before claiming donations")
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    if food_listing.approval_status != ListingApprovalStatus.APPROVED:
        raise ValueError("This listing is awaiting administrator approval")
    if food_listing.status != ListingStatus.AVAILABLE:
        raise ValueError("This listing is no longer available")
    if food_listing.listing_type != ListingType.DONATION:
        raise ValueError("This listing is not marked for donation")
    if quantity > food_listing.available_quantity:
        raise ValueError("Requested quantity exceeds available quantity")

    food_listing.available_quantity -= quantity
    if food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.RESERVED
    food_listing.updated_at = datetime.now(timezone.utc)
    await food_listing.save()

    transaction = Transaction(
        food_listing=food_listing,
        claimed_by=ngo,
        type=TransactionType.DONATION,
        quantity=quantity,
        total_amount=0.0,
        status=TransactionStatus.CONFIRMED,
    )
    await transaction.insert()
    return transaction


async def get_ngo_claims(ngo: User) -> list[Transaction]:
    """Lets an NGO track the progress of all its claimed donations."""
    return await Transaction.find(
        Transaction.claimed_by.id == ngo.id,
        Transaction.type == TransactionType.DONATION,
    ).sort(-Transaction.reserved_at).to_list()


async def mark_donation_completed(transaction_id: str) -> Transaction:
    """Called once the NGO has physically picked up and distributed the food."""
    transaction = await Transaction.get(transaction_id)
    if transaction is None:
        raise ValueError("Transaction not found")

    transaction.status = TransactionStatus.COMPLETED
    transaction.completed_at = datetime.now(timezone.utc)
    await transaction.save()

    food_listing = await FoodListing.get(transaction.food_listing.ref.id)
    if food_listing and food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.SOLD_DONATED
        await food_listing.save()

    return transaction