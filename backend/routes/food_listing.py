from datetime import datetime

from fastapi import APIRouter, HTTPException

from database import (
    create_food_listing,
    delete_food_listing_by_id,
    get_food_listing_by_id,
    list_food_listings,
    reserve_food_listing,
    update_food_listing_by_id,
)
from models.food_listing import FoodListing


router = APIRouter(
    prefix="/listings",
    tags=["Food Listings"],
)


async def generate_notifications() -> list[dict]:
    listings = await list_food_listings(status="available")
    notifications = []

    for listing in listings[:10]:
        recommendation = listing.get("recommendation", "Review listing")
        if recommendation == "Donate now":
            notifications.append({
                "id": f"notif-{listing.get('id', 'donate')}",
                "type": "donation",
                "title": "Donation reminder",
                "message": f"{listing.get('food_name')} is expiring soon and should be donated to maximize impact.",
                "created_at": datetime.utcnow().isoformat(),
            })
        elif recommendation == "Sell at discount":
            notifications.append({
                "id": f"notif-{listing.get('id', 'discount')}",
                "type": "discount",
                "title": "Discount suggestion",
                "message": f"{listing.get('food_name')} should be sold at a discount to reduce waste before expiry.",
                "created_at": datetime.utcnow().isoformat(),
            })
        else:
            notifications.append({
                "id": f"notif-{listing.get('id', 'info')}",
                "type": "info",
                "title": "Food available",
                "message": f"New surplus listing: {listing.get('food_name')} is available at {listing.get('pickup_location')}.",
                "created_at": datetime.utcnow().isoformat(),
            })

    if not notifications:
        notifications.append({
            "id": "notif-empty",
            "type": "info",
            "title": "No active alerts",
            "message": "There are no nearby listings requiring attention right now.",
            "created_at": datetime.utcnow().isoformat(),
        })

    return notifications


def _add_recommendation_to_listing(listing: dict) -> dict:
    if not listing:
        return listing

    recommendation = listing.get("recommendation")
    if recommendation:
        return listing

    # fallback if the recommendation was not added during storage
    expiry_value = listing.get("expiry_time")
    if expiry_value:
        try:
            expiry_dt = datetime.fromisoformat(str(expiry_value).replace("Z", "+00:00"))
            now = datetime.utcnow()
            hours_left = (expiry_dt - now).total_seconds() / 3600
            if hours_left <= 6:
                listing["recommendation"] = "Donate now"
                listing["recommendation_reason"] = "Food is expiring very soon; donation is the best use."
                listing["urgency"] = "high"
            elif hours_left <= 24:
                listing["recommendation"] = "Sell at discount"
                listing["recommendation_reason"] = "Expiring soon; a discounted sale will reduce waste quickly."
                listing["urgency"] = "high"
            else:
                listing["recommendation"] = "Keep for normal sale"
                listing["recommendation_reason"] = "Food is still fresh and can be sold at standard pricing."
                listing["urgency"] = "low"
        except Exception:
            listing["recommendation"] = "Review listing"
            listing["recommendation_reason"] = "Expiry data needs review."
            listing["urgency"] = "medium"
    else:
        listing["recommendation"] = "Review listing"
        listing["recommendation_reason"] = "Expiry data is missing."
        listing["urgency"] = "medium"
    return listing


@router.post("/")
async def create_listing_endpoint(listing: FoodListing):
    if listing.expiry_time <= datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Expiry time must be in the future.",
        )

    if listing.discounted_price > listing.original_price:
        raise HTTPException(
            status_code=400,
            detail="Discounted price cannot be greater than original price.",
        )

    try:
        saved_listing = await create_food_listing(listing.model_dump(exclude_none=True))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {
        "message": "Food listing created successfully",
        "listing": _add_recommendation_to_listing(saved_listing),
    }


@router.get("/")
async def get_food_listings():
    try:
        listings = await list_food_listings(status="available")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return [_add_recommendation_to_listing(listing) for listing in listings]


@router.get("/notifications")
async def get_notifications():
    try:
        return await generate_notifications()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc


@router.post("/{listing_id}/reserve")
async def reserve_listing(listing_id: str):
    try:
        reserved = await reserve_food_listing(listing_id, consumer_id="consumer_001")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {
        "message": "Food reserved successfully",
        "reservation": reserved,
    }


@router.get("/{listing_id}")
async def get_food_listing(listing_id: str):
    try:
        listing = await get_food_listing_by_id(listing_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    if not listing:
        raise HTTPException(status_code=404, detail="Food listing not found")

    return _add_recommendation_to_listing(listing)


@router.put("/{listing_id}")
async def update_food_listing(listing_id: str, updated_listing: FoodListing):
    try:
        existing_listing = await get_food_listing_by_id(listing_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    if not existing_listing:
        raise HTTPException(status_code=404, detail="Food listing not found")

    if updated_listing.expiry_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Expiry time must be in the future.")

    if updated_listing.discounted_price > updated_listing.original_price:
        raise HTTPException(status_code=400, detail="Discounted price cannot be greater than original price.")

    updates = updated_listing.model_dump(exclude_none=True)
    updates["id"] = listing_id

    try:
        saved_listing = await update_food_listing_by_id(listing_id, updates)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    return {
        "message": "Food listing updated successfully",
        "listing": _add_recommendation_to_listing(saved_listing),
    }


@router.delete("/{listing_id}")
async def delete_food_listing(listing_id: str):
    try:
        deleted = await delete_food_listing_by_id(listing_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}") from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Food listing not found")

    return {"message": "Food listing deleted successfully"}
