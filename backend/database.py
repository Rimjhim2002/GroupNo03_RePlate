import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "replate")

client = AsyncIOMotorClient(MONGODB_URL) if MONGODB_URL else None
mongo_db = client[DATABASE_NAME] if client else None
mongo_ready = False

_in_memory_store: Dict[str, Dict[str, Any]] = {}
_reservations_store: Dict[str, Dict[str, Any]] = {}


def _mongo_available() -> bool:
    return mongo_ready and client is not None and mongo_db is not None


def _recommendation_for_listing(listing: Dict[str, Any]) -> Dict[str, str]:
    expiry_value = listing.get("expiry_time")
    if not expiry_value:
        return {
            "recommendation": "Review listing",
            "recommendation_reason": "Expiry data is missing.",
            "urgency": "medium",
        }

    try:
        expiry_dt = datetime.fromisoformat(str(expiry_value).replace("Z", "+00:00"))
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return {
            "recommendation": "Review listing",
            "recommendation_reason": "Invalid expiry time.",
            "urgency": "medium",
        }

    now = datetime.now(timezone.utc)
    hours_left = (expiry_dt - now).total_seconds() / 3600

    original_price = float(listing.get("original_price") or 0)
    discounted_price = float(listing.get("discounted_price") or 0)
    discount_ratio = 0.0
    if original_price > 0:
        discount_ratio = (original_price - discounted_price) / original_price

    if hours_left <= 6:
        return {
            "recommendation": "Donate now",
            "recommendation_reason": "Food is expiring very soon; donation is the best use.",
            "urgency": "high",
        }
    if hours_left <= 24:
        return {
            "recommendation": "Sell at discount",
            "recommendation_reason": "Expiring soon; a discounted sale will reduce waste quickly.",
            "urgency": "high",
        }
    if hours_left <= 48 or discount_ratio >= 0.35:
        return {
            "recommendation": "Sell at discount",
            "recommendation_reason": "Short shelf life; discounting is recommended to move inventory quickly.",
            "urgency": "medium",
        }

    return {
        "recommendation": "Keep for normal sale",
        "recommendation_reason": "Food is still fresh and can be sold at standard pricing.",
        "urgency": "low",
    }


def _enrich_listing(listing: Dict[str, Any]) -> Dict[str, Any]:
    if not listing:
        return listing

    recommendation = _recommendation_for_listing(listing)
    listing["recommendation"] = recommendation["recommendation"]
    listing["recommendation_reason"] = recommendation["recommendation_reason"]
    listing["urgency"] = recommendation["urgency"]
    return listing


async def init_database() -> None:
    """Connect to MongoDB if available; otherwise keep an in-memory fallback so the API still works."""
    global mongo_ready

    if client is None:
        mongo_ready = False
        logging.warning("MONGODB_URL missing; using in-memory fallback store.")
        return

    try:
        await client.admin.command("ping")
        mongo_ready = True
        logging.info("MongoDB connection successful.")
    except Exception as exc:
        mongo_ready = False
        logging.warning("MongoDB unavailable; using in-memory fallback store. Error: %s", exc)
        return


async def create_food_listing(data: Dict[str, Any]) -> Dict[str, Any]:
    listing_id = str(uuid.uuid4())
    record = {**data, "id": listing_id}
    record = _enrich_listing(record)

    if _mongo_available():
        result = await mongo_db.food_listings.insert_one(record)
        record["id"] = str(result.inserted_id)
        return record

    _in_memory_store[listing_id] = record
    return record


async def list_food_listings(status: Optional[str] = "available") -> List[Dict[str, Any]]:
    if _mongo_available():
        query = {"status": status} if status else {}
        documents = await mongo_db.food_listings.find(query).to_list(length=None)
        return [_enrich_listing(dict(doc)) for doc in documents]

    records = list(_in_memory_store.values())
    if status is not None:
        records = [record for record in records if record.get("status") == status]
    return [_enrich_listing(record) for record in records]


async def get_food_listing_by_id(listing_id: str) -> Optional[Dict[str, Any]]:
    if _mongo_available():
        document = await mongo_db.food_listings.find_one({"id": listing_id})
        return _enrich_listing(dict(document)) if document else None

    record = _in_memory_store.get(listing_id)
    return _enrich_listing(record) if record else None


async def update_food_listing_by_id(listing_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if _mongo_available():
        result = await mongo_db.food_listings.find_one_and_update(
            {"id": listing_id},
            {"$set": _enrich_listing(updates)},
            return_document=True,
        )
        return dict(result) if result else None

    if listing_id not in _in_memory_store:
        return None

    _in_memory_store[listing_id].update(_enrich_listing(updates))
    return _in_memory_store[listing_id]


async def delete_food_listing_by_id(listing_id: str) -> bool:
    if _mongo_available():
        result = await mongo_db.food_listings.delete_one({"id": listing_id})
        return result.deleted_count > 0

    if listing_id in _in_memory_store:
        del _in_memory_store[listing_id]
        return True
    return False


async def reserve_food_listing(listing_id: str, consumer_id: str = "consumer_001") -> Dict[str, Any]:
    listing = await get_food_listing_by_id(listing_id)
    if not listing:
        raise ValueError("Food listing not found")

    if listing.get("status") != "available":
        raise ValueError("This listing is no longer available")

    reservation_id = str(uuid.uuid4())
    reservation = {
        "id": reservation_id,
        "listing_id": listing_id,
        "consumer_id": consumer_id,
        "status": "reserved",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if _mongo_available():
        # MongoDB path: update listing status to reserved and insert reservation record
        await mongo_db.food_listings.update_one({"id": listing_id}, {"$set": {"status": "reserved"}})
        await mongo_db.reservations.insert_one(reservation)
        return reservation

    _reservations_store[reservation_id] = reservation
    listing["status"] = "reserved"
    _in_memory_store[listing_id] = listing
    return reservation
