import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.controllers.food_listing_controller import (
    claim_listing,
    expire_listings,
    get_owned_listing,
    suggested_discount_percentage,
)
from app.models.enums import (
    ListingApprovalStatus,
    ListingStatus,
    ListingType,
)
from app.models.user import UserRole


class Member1FoodManagementTests(unittest.IsolatedAsyncioTestCase):
    def listing_with_hours(self, hours):
        return SimpleNamespace(get_remaining_shelf_life_hours=lambda: hours)

    def test_discount_increases_as_expiry_approaches(self):
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(48)), 15.0)
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(24)), 30.0)
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(6)), 50.0)

    def test_expired_listing_receives_full_discount(self):
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(0)), 100.0)
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(-2)), 100.0)

    def test_long_shelf_life_gets_small_discount(self):
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(72)), 0.0)

    def test_discount_is_capped_for_urgent_food(self):
        self.assertEqual(suggested_discount_percentage(self.listing_with_hours(1)), 50.0)

    async def test_expiry_processing_marks_only_expired_listings(self):
        expired = SimpleNamespace(
            status=ListingStatus.AVAILABLE,
            expiry_date=datetime.now(timezone.utc) - timedelta(minutes=1),
            save=AsyncMock(),
        )
        active = SimpleNamespace(
            status=ListingStatus.AVAILABLE,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=1),
            save=AsyncMock(),
        )

        expired_count = await expire_listings([expired, active])

        self.assertEqual(expired_count, 1)
        self.assertEqual(expired.status, ListingStatus.EXPIRED)
        expired.save.assert_awaited_once()
        active.save.assert_not_awaited()

    async def test_expiry_processing_ignores_reserved_listings(self):
        reserved = SimpleNamespace(
            status=ListingStatus.RESERVED,
            expiry_date=datetime.now(timezone.utc) - timedelta(minutes=1),
            save=AsyncMock(),
        )

        expired_count = await expire_listings([reserved])

        self.assertEqual(expired_count, 0)
        reserved.save.assert_not_awaited()

    async def test_owned_listing_rejects_missing_listing(self):
        restaurant = SimpleNamespace(id="restaurant-1")

        with patch(
            "app.controllers.food_listing_controller.FoodListing.get",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_owned_listing("listing-1", restaurant)

        self.assertEqual(context.exception.status_code, 404)

    async def test_owned_listing_rejects_another_restaurants_listing(self):
        restaurant = SimpleNamespace(id="restaurant-1")
        listing = SimpleNamespace(restaurant=SimpleNamespace(ref=SimpleNamespace(id="restaurant-2")))

        with patch(
            "app.controllers.food_listing_controller.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            with self.assertRaises(HTTPException) as context:
                await get_owned_listing("listing-1", restaurant)

        self.assertEqual(context.exception.status_code, 404)

    async def test_claim_rejects_invalid_quantity(self):
        with self.assertRaises(HTTPException) as context:
            await claim_listing("listing-1", 0, SimpleNamespace(role=UserRole.CONSUMER))

        self.assertEqual(context.exception.status_code, 400)

    async def test_claim_rejects_quantity_above_available_stock(self):
        listing = SimpleNamespace(
            approval_status=ListingApprovalStatus.APPROVED,
            status=ListingStatus.AVAILABLE,
            available_quantity=1,
            unit="item",
            listing_type=ListingType.SALE,
            get_remaining_shelf_life_hours=lambda: 4,
        )
        consumer = SimpleNamespace(role=UserRole.CONSUMER)

        with patch(
            "app.controllers.food_listing_controller.FoodListing.get",
            new=AsyncMock(return_value=listing),
        ):
            with self.assertRaises(HTTPException) as context:
                await claim_listing("listing-1", 2, consumer)

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
