from datetime import datetime, timezone

from app.models.user import User, UserRole, VerificationStatus
from app.models.food_listing import FoodListing, ListingApprovalStatus, ListingStatus, ListingType
from app.models.transaction import Transaction, TransactionType, TransactionStatus


async def browse_available_donations() -> list[dict]:
    """NGOs browse listings that are still available, soonest-to-expire first.
    TODO: add a geo/distance filter once location-based query support is added."""
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
        FoodListing.approval_status == ListingApprovalStatus.APPROVED,
        FoodListing.listing_type == ListingType.DONATION,
    ).sort(+FoodListing.expiry_date).to_list()
    return [
        {
            "id": str(listing.id),
            "food_name": listing.food_name,
            "description": listing.description,
            "pickup_location": listing.pickup_location,
            "available_quantity": listing.available_quantity,
            "unit": listing.unit,
            "expiry_date": listing.expiry_date,
        }
        for listing in listings
    ]


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


async def get_ngo_claims(ngo: User) -> list[dict]:
    """Lets an NGO track the progress of all its claimed donations."""
    transactions = await Transaction.find(
        Transaction.claimed_by.id == ngo.id,
        Transaction.type == TransactionType.DONATION,
    ).sort(-Transaction.reserved_at).to_list()
    claims = []
    for transaction in transactions:
        listing = await transaction.food_listing.fetch()
        if listing is None:
            continue
        claims.append(
            {
                "id": str(transaction.id),
                "food_name": listing.food_name,
                "pickup_location": listing.pickup_location,
                "quantity": transaction.quantity,
                "status": transaction.status.value,
                "ngo_pickup_confirmed": transaction.ngo_pickup_confirmed_at is not None,
                "restaurant_pickup_confirmed": transaction.restaurant_pickup_confirmed_at is not None,
                "reserved_at": transaction.reserved_at,
                "completed_at": transaction.completed_at,
            }
        )
    return claims


async def mark_donation_completed(transaction_id: str, ngo: User) -> Transaction:
    """Called once the NGO has physically picked up and distributed the food."""
    transaction = await Transaction.get(transaction_id)
    if transaction is None:
        raise ValueError("Transaction not found")
    if transaction.claimed_by.ref.id != ngo.id:
        raise ValueError("You can only confirm pickup for your own donation claims")
    if transaction.type != TransactionType.DONATION:
        raise ValueError("This transaction is not a donation claim")
    if transaction.status == TransactionStatus.COMPLETED:
        return transaction

    transaction.ngo_pickup_confirmed_at = datetime.now(timezone.utc)
    if transaction.restaurant_pickup_confirmed_at is not None:
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.now(timezone.utc)
    await transaction.save()

    food_listing = await FoodListing.get(transaction.food_listing.ref.id)
    if food_listing and transaction.status == TransactionStatus.COMPLETED and food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.SOLD_DONATED
        await food_listing.save()

    return transaction


async def get_restaurant_claims(restaurant: User) -> list[dict]:
    transactions = await Transaction.find(Transaction.type == TransactionType.DONATION).to_list()
    claims = []
    for transaction in transactions:
        listing = await transaction.food_listing.fetch()
        if listing is None or listing.restaurant.ref.id != restaurant.id:
            continue
        ngo = await transaction.claimed_by.fetch()
        claims.append(
            {
                "id": str(transaction.id),
                "food_name": listing.food_name,
                "pickup_location": listing.pickup_location,
                "quantity": transaction.quantity,
                "ngo_name": ngo.organization_name or ngo.name if ngo else "NGO",
                "status": transaction.status.value,
                "ngo_pickup_confirmed": transaction.ngo_pickup_confirmed_at is not None,
                "restaurant_pickup_confirmed": transaction.restaurant_pickup_confirmed_at is not None,
            }
        )
    return claims


async def confirm_restaurant_pickup(transaction_id: str, restaurant: User) -> Transaction:
    transaction = await Transaction.get(transaction_id)
    if transaction is None:
        raise ValueError("Transaction not found")
    listing = await transaction.food_listing.fetch()
    if listing is None or listing.restaurant.ref.id != restaurant.id:
        raise ValueError("You can only confirm pickup for your own listings")
    transaction.restaurant_pickup_confirmed_at = datetime.now(timezone.utc)
    if transaction.ngo_pickup_confirmed_at is not None:
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.now(timezone.utc)
        if listing.available_quantity == 0:
            listing.status = ListingStatus.SOLD_DONATED
            await listing.save()
    await transaction.save()
    return transaction