from datetime import datetime
 
from app.models.user import User
from app.models.food_listing import FoodListing, ListingStatus
from app.models.transaction import Transaction, TransactionType, TransactionStatus
 
 
async def browse_available_donations() -> list[FoodListing]:
    """NGOs browse listings that are still available, soonest-to-expire first.
    TODO: add a geo/distance filter once location-based query support is added."""
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE
    ).sort(+FoodListing.expiry_time).to_list()
    return listings
 
 
async def claim_donation(ngo: User, food_listing_id: str, quantity: int) -> Transaction:
    """A verified NGO claims (part of) a surplus food listing for donation."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    if food_listing.status != ListingStatus.AVAILABLE:
        raise ValueError("This listing is no longer available")
    if quantity > food_listing.available_quantity:
        raise ValueError("Requested quantity exceeds available quantity")
 
    food_listing.available_quantity -= quantity
    if food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.RESERVED
    food_listing.updated_at = datetime.utcnow()
    await food_listing.save()
 
    transaction = Transaction(
        food_listing_id=str(food_listing.id),
        user_id=str(ngo.id),
        transaction_type=TransactionType.DONATION,
        quantity=quantity,
        status=TransactionStatus.CONFIRMED,
    )
    await transaction.insert()
    return transaction
 
 
async def get_ngo_claims(ngo: User) -> list[Transaction]:
    """Lets an NGO track the progress of all its claimed donations."""
    return await Transaction.find(
        Transaction.user_id == str(ngo.id),
        Transaction.transaction_type == TransactionType.DONATION,
    ).sort(-Transaction.date_reserved).to_list()
 
 
async def mark_donation_completed(transaction_id: str) -> Transaction:
    """Called once the NGO has physically picked up and distributed the food."""
    transaction = await Transaction.get(transaction_id)
    if transaction is None:
        raise ValueError("Transaction not found")
 
    transaction.status = TransactionStatus.COMPLETED
    transaction.date_completed = datetime.utcnow()
    await transaction.save()
 
    food_listing = await FoodListing.get(transaction.food_listing_id)
    if food_listing and food_listing.available_quantity == 0:
        food_listing.status = ListingStatus.COMPLETED
        await food_listing.save()
 
    return transaction