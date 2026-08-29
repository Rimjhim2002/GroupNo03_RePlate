import math
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from app.controllers.food_listing_controller import claim_listing
from app.models.enums import ListingStatus
from app.models.food_listing import FoodListing
from app.models.transaction import Transaction
from app.models.user import User
from app.services.availability_service import join_waitlist as join_waitlist_entry


def _to_km(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    delta_lat = lat2_r - lat1_r
    delta_lon = lon2_r - lon1_r
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _matches_category(value: str, requested: str) -> bool:
    value_normalized = value.strip().lower()
    requested_normalized = requested.strip().lower()
    return (
        requested_normalized in value_normalized
        or value_normalized in requested_normalized
        or SequenceMatcher(None, value_normalized, requested_normalized).ratio() >= 0.75
    )


def _matches_location(value: str, requested: str) -> bool:
    return value.strip().casefold() == requested.strip().casefold()


async def _build_listing_summary(
    listing: FoodListing,
    consumer_lat: float | None = None,
    consumer_lon: float | None = None,
) -> dict[str, Any]:
    restaurant = await listing.restaurant.fetch()
    distance_km = None
    if (
        consumer_lat is not None
        and consumer_lon is not None
        and listing.latitude is not None
        and listing.longitude is not None
    ):
        distance_km = _haversine_km(consumer_lat, consumer_lon, listing.latitude, listing.longitude)

    return {
        "id": str(listing.id),
        "restaurant_id": str(listing.restaurant.ref.id),
        "restaurant_name": restaurant.business_name or restaurant.name,
        "food_name": listing.food_name,
        "description": listing.description,
        "category": listing.category,
        "listing_type": listing.listing_type.value,
        "quantity": listing.quantity,
        "available_quantity": listing.available_quantity,
        "unit": listing.unit,
        "original_price": listing.original_price,
        "discount_percentage": listing.discount_percentage,
        "discounted_price": round(listing.original_price * (1 - listing.discount_percentage / 100), 2),
        "expiry_date": listing.expiry_date,
        "expiry_hours_left": round(listing.get_remaining_shelf_life_hours(), 2),
        "pickup_location": listing.pickup_location,
        "status": listing.status.value,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        "distance_km": _to_km(distance_km),
    }


async def get_nearby_food(
    consumer: User,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 5.0,
    category: str | None = None,
    location: str | None = None,
    food_name: str | None = None,
) -> list[dict[str, Any]]:
    lookup_lat = latitude if latitude is not None else consumer.latitude
    lookup_lon = longitude if longitude is not None else consumer.longitude

    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
    ).to_list()

    nearby: list[dict[str, Any]] = []
    for listing in listings:
        requested_food_name = food_name or category
        if requested_food_name and listing.food_name.strip().casefold() != requested_food_name.strip().casefold():
            continue
        if location and not _matches_location(listing.pickup_location, location):
            continue

        distance_km = None
        if (
            lookup_lat is not None
            and lookup_lon is not None
            and listing.latitude is not None
            and listing.longitude is not None
        ):
            distance_km = _haversine_km(lookup_lat, lookup_lon, listing.latitude, listing.longitude)
            if distance_km > radius_km:
                continue
        summary = await _build_listing_summary(listing, lookup_lat, lookup_lon)
        nearby.append(summary)

    nearby.sort(
        key=lambda item: item["distance_km"] if item["distance_km"] is not None else float("inf")
    )
    return nearby


async def search_food_listings(
    consumer: User,
    search_term: str | None = None,
    category: str | None = None,
    max_price: float | None = None,
    restaurant: str | None = None,
    radius_km: float | None = None,
    expiry_hours: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    location: str | None = None,
    food_name: str | None = None,
) -> list[dict[str, Any]]:
    lookup_lat = latitude if latitude is not None else consumer.latitude
    lookup_lon = longitude if longitude is not None else consumer.longitude

    listings = await FoodListing.find(
        FoodListing.status == ListingStatus.AVAILABLE,
    ).to_list()

    results: list[dict[str, Any]] = []
    for listing in listings:
        requested_food_name = food_name or category
        if requested_food_name and not _matches_category(listing.food_name, requested_food_name):
            continue
        if location and location.lower() not in listing.pickup_location.lower():
            continue

        if search_term:
            haystack = " ".join(
                [
                    listing.food_name,
                    listing.description,
                    listing.category,
                    listing.pickup_location,
                ]
            ).lower()
            if search_term.lower() not in haystack:
                continue

        if max_price is not None and listing.get_discounted_price() > max_price:
            continue

        if restaurant:
            restaurant_user = await listing.restaurant.fetch()
            restaurant_name = restaurant_user.business_name or restaurant_user.name
            if restaurant.lower() not in restaurant_name.lower():
                continue

        if expiry_hours is not None and listing.get_remaining_shelf_life_hours() > expiry_hours:
            continue

        if radius_km is not None:
            if (
                lookup_lat is not None
                and lookup_lon is not None
                and listing.latitude is not None
                and listing.longitude is not None
            ):
                distance_km = _haversine_km(lookup_lat, lookup_lon, listing.latitude, listing.longitude)
                if distance_km > radius_km:
                    continue

        result = await _build_listing_summary(listing, lookup_lat, lookup_lon)
        results.append(result)

    results.sort(
        key=lambda item: (
            item["distance_km"] is None,
            item["distance_km"] if item["distance_km"] is not None else float("inf"),
        )
    )
    return results


async def reserve_food_listing(consumer: User, listing_id: str, quantity: int) -> dict[str, Any]:
    return await claim_listing(listing_id, quantity, consumer)


async def join_waitlist(consumer: User, food_listing_id: str):
    return await join_waitlist_entry(str(consumer.id), food_listing_id)


async def get_transaction_history(consumer: User) -> list[dict[str, Any]]:
    transactions = await Transaction.find(
        Transaction.claimed_by.id == consumer.id,
    ).sort(-Transaction.reserved_at).to_list()

    records: list[dict[str, Any]] = []
    for transaction in transactions:
        listing = await transaction.food_listing.fetch()
        records.append(
            {
                "transaction_id": str(transaction.id),
                "listing_id": str(listing.id),
                "food_name": listing.food_name,
                "category": listing.category,
                "restaurant_name": (await listing.restaurant.fetch()).business_name or (await listing.restaurant.fetch()).name,
                "quantity": transaction.quantity,
                "total_amount": transaction.total_amount,
                "type": transaction.type.value,
                "status": transaction.status.value,
                "reserved_at": transaction.reserved_at,
                "completed_at": transaction.completed_at,
                "pickup_slot_start": transaction.pickup_slot_start,
                "pickup_slot_end": transaction.pickup_slot_end,
            }
        )
    return records
