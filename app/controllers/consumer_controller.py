from __future__ import annotations

from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status

from app.models.enums import ListingApprovalStatus, ListingStatus, ListingType
from app.models.food_listing import FoodListing
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User, UserRole
from app.models.waitlist import Waitlist, WaitlistStatus


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _discounted_price(listing: FoodListing) -> float:
    return round(
        float(listing.original_price) * (1 - float(listing.discount_percentage) / 100),
        2,
    )


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * (2 * atan2(sqrt(a), sqrt(1 - a)))


def filter_listings_for_consumer(
    listings: Iterable[Any],
    search_term: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    user_lat: Optional[float] = None,
    user_lon: Optional[float] = None,
    location_term: Optional[str] = None,
    max_expiry_hours: Optional[float] = None,
):
    term = (search_term or "").strip().lower()
    location = (location_term or "").strip().lower()
    filtered = []
    for listing in listings:
        if getattr(listing, "status", None) != ListingStatus.AVAILABLE:
            continue

        if category and getattr(listing, "category", "").lower() != category.lower():
            continue

        price = _discounted_price(listing)
        if max_price is not None and price > max_price:
            continue

        remaining_hours = listing.get_remaining_shelf_life_hours() if hasattr(listing, "get_remaining_shelf_life_hours") else 0
        if max_expiry_hours is not None and remaining_hours > float(max_expiry_hours):
            continue

        has_additional_filters = (
            category is not None
            or max_price is not None
            or max_distance_km is not None
            or location_term is not None
            or max_expiry_hours is not None
        )

        if term:
            food_name = str(getattr(listing, "food_name", "")).lower()
            if has_additional_filters:
                haystack = " ".join(
                    [
                        getattr(listing, "food_name", ""),
                        getattr(listing, "description", ""),
                        getattr(listing, "category", ""),
                        getattr(listing, "pickup_location", ""),
                        getattr(listing, "restaurant_name", ""),
                    ]
                ).lower()
                if term not in haystack:
                    continue
            elif term not in food_name:
                continue

        if location and location not in " ".join(
            [
                getattr(listing, "food_name", ""),
                getattr(listing, "description", ""),
                getattr(listing, "category", ""),
                getattr(listing, "pickup_location", ""),
                getattr(listing, "restaurant_name", ""),
            ]
        ).lower():
            continue

        if (
            max_distance_km is not None
            and user_lat is not None
            and user_lon is not None
            and getattr(listing, "latitude", None) is not None
            and getattr(listing, "longitude", None) is not None
        ):
            distance = _distance_km(
                user_lat,
                user_lon,
                float(listing.latitude),
                float(listing.longitude),
            )
            if distance > float(max_distance_km):
                continue

        filtered.append(listing)

    filtered.sort(
        key=lambda item: (
            getattr(item, "expiry_date", datetime.now(timezone.utc)),
            _discounted_price(item),
        )
    )
    return filtered


async def search_consumer_listings(
    user: User,
    search_term: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    location_term: Optional[str] = None,
    max_expiry_hours: Optional[float] = None,
):
    from beanie.operators import In
    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
        In(FoodListing.approval_status, [ListingApprovalStatus.APPROVED, None]),
        FoodListing.listing_type == ListingType.SALE,
    ).sort(+FoodListing.expiry_date).to_list()

    filtered = filter_listings_for_consumer(
        listings,
        search_term=search_term,
        category=category,
        max_price=max_price,
        max_distance_km=max_distance_km,
        user_lat=user.latitude,
        user_lon=user.longitude,
        location_term=location_term,
        max_expiry_hours=max_expiry_hours,
    )

    response = []
    for listing in filtered:
        restaurant = None
        restaurant_id = None
        if getattr(listing, "restaurant", None):
            restaurant_id = str(
                listing.restaurant.ref.id
                if hasattr(listing.restaurant, "ref")
                else getattr(listing.restaurant, "id", None)
            )
            try:
                restaurant = (
                    await listing.restaurant.fetch()
                    if hasattr(listing.restaurant, "fetch")
                    else listing.restaurant
                )
            except Exception:
                restaurant = None
        response.append(
            {
                "id": str(listing.id),
                "restaurant_id": restaurant_id,
                "restaurant_name": getattr(restaurant, "business_name", None) or getattr(restaurant, "name", None),
                "food_name": listing.food_name,
                "description": listing.description,
                "category": listing.category,
                "quantity": listing.quantity,
                "available_quantity": listing.available_quantity,
                "unit": listing.unit,
                "original_price": float(listing.original_price),
                "discount_percentage": float(listing.discount_percentage),
                "discounted_price": _discounted_price(listing),
                "expiry_date": listing.expiry_date,
                "pickup_location": listing.pickup_location,
                "status": _value(listing.status),
                "distance_km": round(
                    _distance_km(
                        float(user.latitude),
                        float(user.longitude),
                        float(listing.latitude),
                        float(listing.longitude),
                    ),
                    1,
                )
                if user.latitude is not None
                and user.longitude is not None
                and listing.latitude is not None
                and listing.longitude is not None
                else None,
                "remaining_hours": round(listing.get_remaining_shelf_life_hours(), 1),
            }
        )

    return response


async def reserve_listing_for_consumer(listing_id: str, quantity: int, user: User) -> dict:
    if user.role != UserRole.CONSUMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only consumers can reserve food.")
    if quantity < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be at least 1.")

    listing = await FoodListing.get(listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    if listing.approval_status != ListingApprovalStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This listing is awaiting approval.")
    if listing.status != ListingStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This listing is no longer available.")
    if listing.listing_type != ListingType.SALE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This listing is not available for consumer purchase.")
    if quantity > listing.available_quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Only {listing.available_quantity} item(s) remain.")

    total_amount = round(_discounted_price(listing) * quantity, 2)
    listing.available_quantity -= quantity
    if listing.available_quantity == 0:
        listing.status = ListingStatus.RESERVED
    listing.updated_at = datetime.now(timezone.utc)
    await listing.save()

    transaction = Transaction(
        food_listing=listing,
        claimed_by=user,
        type=TransactionType.SALE,
        quantity=quantity,
        total_amount=total_amount,
        status=TransactionStatus.RESERVED,
    )
    await transaction.insert()

    return {
        "transaction_id": str(transaction.id),
        "listing_id": str(listing.id),
        "food_name": listing.food_name,
        "quantity": quantity,
        "total_amount": total_amount,
        "status": _value(transaction.status),
        "message": "Reservation created successfully.",
    }


async def join_waitlist_for_consumer(listing_id: str, user: User) -> dict:
    if user.role != UserRole.CONSUMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only consumers can join waitlists.")

    listing = await FoodListing.get(listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    if listing.approval_status != ListingApprovalStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This listing is awaiting approval.")
    if listing.listing_type != ListingType.SALE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Waitlists only apply to purchasable listings.")

    existing = await Waitlist.find(
        Waitlist.consumer.id == user.id,
        Waitlist.food_listing.id == listing.id,
        Waitlist.status == WaitlistStatus.WAITING,
    ).first_or_none()
    if existing:
        return {
            "waitlist_id": str(existing.id),
            "position": existing.position,
            "status": _value(existing.status),
            "message": "You are already on this waitlist.",
        }

    position = await Waitlist.find(
        Waitlist.food_listing.id == listing.id,
        Waitlist.status == WaitlistStatus.WAITING,
    ).count()

    waitlist_entry = Waitlist(
        consumer=user,
        food_listing=listing,
        position=position + 1,
        status=WaitlistStatus.WAITING,
    )
    await waitlist_entry.insert()

    return {
        "waitlist_id": str(waitlist_entry.id),
        "listing_id": str(listing.id),
        "position": waitlist_entry.position,
        "status": _value(waitlist_entry.status),
        "message": "You joined the waitlist successfully.",
    }


async def get_consumer_history(user: User) -> dict:
    transactions = await Transaction.find(
        Transaction.claimed_by.id == user.id,
    ).sort(-Transaction.reserved_at).to_list()

    history = []
    for transaction in transactions:
        listing = await transaction.food_listing.fetch()
        restaurant = await listing.restaurant.fetch() if listing else None
        history.append(
            {
                "transaction_id": str(transaction.id),
                "food_name": listing.food_name if listing else "Unknown item",
                "category": listing.category if listing else None,
                "restaurant_name": getattr(restaurant, "business_name", None) or getattr(restaurant, "name", None),
                "quantity": transaction.quantity,
                "type": _value(transaction.type),
                "total_amount": float(transaction.total_amount),
                "status": _value(transaction.status),
                "reserved_at": transaction.reserved_at,
                "pickup_location": listing.pickup_location if listing else None,
            }
        )

    return {
        "summary": build_consumer_history_summary(transactions),
        "transactions": history,
    }


async def get_consumer_dashboard(user: User) -> dict:
    transactions = await Transaction.find(
        Transaction.claimed_by.id == user.id,
    ).to_list()

    return {
        "user_id": str(user.id),
        "active_reservations": sum(
            1 for t in transactions if _value(t.status) == "reserved"
        ),
        "completed_transactions": sum(
            1 for t in transactions if _value(t.status) == "completed"
        ),
        "meals_received": sum(
            int(t.quantity) for t in transactions if _value(t.type) == "sale" and _value(t.status) == "completed"
        ),
        "money_saved": round(
            sum(float(t.total_amount) for t in transactions if _value(t.type) == "sale" and _value(t.status) == "completed"),
            2,
        ),
    }


def build_consumer_history_summary(transactions: Iterable[Any]) -> dict:
    total_spend = 0.0
    total_saved = 0.0
    completed_orders = 0
    active_reservations = 0
    for transaction in transactions:
        type_value = _value(transaction.type)
        status_value = _value(transaction.status)
        amount = float(getattr(transaction, "total_amount", 0) or 0)

        if type_value == "sale" and status_value == "completed":
            total_spend += amount
            total_saved += amount
            completed_orders += 1
        elif type_value == "sale" and status_value == "reserved":
            active_reservations += 1
        elif type_value == "donation" and status_value == "completed":
            completed_orders += 1

    return {
        "total_spend": round(total_spend, 2),
        "total_saved": round(total_saved, 2),
        "completed_orders": completed_orders,
        "active_reservations": active_reservations,
        "meals_received": sum(int(getattr(t, "quantity", 0) or 0) for t in transactions if _value(t.type) == "sale" and _value(t.status) == "completed"),
    }
