import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.food_listing import PickupSlot
from app.models.enums import ListingStatus
from app.models.user import UserRole, VerificationStatus
from app.services.availability_service import get_live_availability
from app.services.ngo_service import claim_donation
from app.services.pickup_service import book_pickup_slot, get_available_slots
from app.services.prioritization_service import compute_priority_score


class Member3LifecycleNgoTests(unittest.IsolatedAsyncioTestCase):
    def test_priority_score_increases_for_food_near_expiry(self):
        fresh_listing = SimpleNamespace(get_remaining_shelf_life_hours=lambda: 48)
        urgent_listing = SimpleNamespace(get_remaining_shelf_life_hours=lambda: 2)

        self.assertEqual(compute_priority_score(fresh_listing), 52.0)
        self.assertEqual(compute_priority_score(urgent_listing), 98.0)

    def test_expired_food_receives_maximum_priority(self):
        expired_listing = SimpleNamespace(get_remaining_shelf_life_hours=lambda: -1)
        self.assertEqual(compute_priority_score(expired_listing), 100.0)

    async def test_live_availability_returns_current_quantity_and_status(self):
        listing = SimpleNamespace(
            id="listing-1",
            available_quantity=3,
            status="available",
            updated_at="now",
        )

        with patch(
            "app.services.availability_service.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            result = await get_live_availability("listing-1")

        self.assertEqual(result["food_listing_id"], "listing-1")
        self.assertEqual(result["available_quantity"], 3)
        self.assertEqual(result["status"], "available")

    async def test_full_pickup_slots_are_hidden_and_cannot_be_booked(self):
        full_slot = PickupSlot(start_time="2026-09-06T10:00:00", end_time="2026-09-06T11:00:00", capacity=1, booked_count=1)
        listing = SimpleNamespace(pickup_slots=[full_slot], save=AsyncMock())

        with patch(
            "app.services.pickup_service.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            available = await get_available_slots("listing-1")
            with self.assertRaisesRegex(ValueError, "slot is full"):
                await book_pickup_slot("listing-1", 0)

        self.assertEqual(available, [])
        listing.save.assert_not_awaited()

    async def test_available_pickup_slot_can_be_booked(self):
        slot = PickupSlot(start_time="2026-09-06T10:00:00", end_time="2026-09-06T11:00:00", capacity=2)
        listing = SimpleNamespace(pickup_slots=[slot], save=AsyncMock())

        with patch(
            "app.services.pickup_service.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            result = await book_pickup_slot("listing-1", 0)

        self.assertIs(result, slot)
        self.assertEqual(slot.booked_count, 1)
        listing.save.assert_awaited_once()

    async def test_invalid_pickup_slot_index_is_rejected(self):
        listing = SimpleNamespace(pickup_slots=[], save=AsyncMock())

        with patch(
            "app.services.pickup_service.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            with self.assertRaisesRegex(ValueError, "Invalid slot index"):
                await book_pickup_slot("listing-1", 0)

        listing.save.assert_not_awaited()

    async def test_live_availability_rejects_missing_listing(self):
        with patch(
            "app.services.availability_service.FoodListing.get",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaisesRegex(ValueError, "Food listing not found"):
                await get_live_availability("missing")

    async def test_unverified_ngo_cannot_claim_donation(self):
        ngo = SimpleNamespace(role=UserRole.NGO, verification_status=VerificationStatus.PENDING)

        with self.assertRaisesRegex(ValueError, "must be verified"):
            await claim_donation(ngo, "listing-1", 1)

    async def test_non_ngo_cannot_claim_donation(self):
        consumer = SimpleNamespace(
            role=UserRole.CONSUMER,
            verification_status=VerificationStatus.VERIFIED,
        )

        with self.assertRaisesRegex(ValueError, "Only NGO"):
            await claim_donation(consumer, "listing-1", 1)

    async def test_donation_claim_requires_positive_quantity(self):
        ngo = SimpleNamespace(role=UserRole.NGO, verification_status=VerificationStatus.VERIFIED)

        with self.assertRaisesRegex(ValueError, "at least 1"):
            await claim_donation(ngo, "listing-1", 0)


if __name__ == "__main__":
    unittest.main()
