from datetime import datetime
 
from app.models.food_listing import FoodListing, PickupSlot
 
 
async def add_pickup_slot(food_listing_id: str, start_time: datetime, end_time: datetime, capacity: int) -> FoodListing:
    """Restaurant defines a pickup window for a listing."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    if capacity <= 0:
        raise ValueError("capacity must be greater than 0")
 
    food_listing.pickup_slots.append(
        PickupSlot(start_time=start_time, end_time=end_time, capacity=capacity)
    )
    await food_listing.save()
    return food_listing
 
 
async def get_available_slots(food_listing_id: str) -> list[PickupSlot]:
    """Slots a consumer/NGO can still pick from during reservation."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    return [slot for slot in food_listing.pickup_slots if slot.booked_count < slot.capacity]
 
 
async def book_pickup_slot(food_listing_id: str, slot_index: int) -> PickupSlot:
    """Consumer/NGO selects a preferred pickup window during reservation or donation collection."""
    food_listing = await FoodListing.get(food_listing_id)
    if food_listing is None:
        raise ValueError("Food listing not found")
    if slot_index < 0 or slot_index >= len(food_listing.pickup_slots):
        raise ValueError("Invalid slot index")
 
    slot = food_listing.pickup_slots[slot_index]
    if slot.booked_count >= slot.capacity:
        raise ValueError("This pickup slot is full")
 
    slot.booked_count += 1
    await food_listing.save()
    return slot