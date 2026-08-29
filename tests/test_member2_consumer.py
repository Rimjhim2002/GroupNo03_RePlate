import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.transaction import TransactionStatus, TransactionType
from app.services.consumer_service import (
    _haversine_km,
    _matches_location,
    join_waitlist,
    mark_order_completed,
    reserve_food_listing,
)


class Member2ConsumerTests(unittest.IsolatedAsyncioTestCase):
    def make_transaction(self, status=TransactionStatus.RESERVED, transaction_type=TransactionType.SALE):
        return SimpleNamespace(
            id="transaction-1",
            claimed_by=SimpleNamespace(ref=SimpleNamespace(id="consumer-1")),
            type=transaction_type,
            status=status,
            completed_at=None,
            save=AsyncMock(),
        )

    async def test_consumer_can_complete_reserved_order(self):
        transaction = self.make_transaction()

        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=transaction),
        ):
            result = await mark_order_completed("transaction-1", SimpleNamespace(id="consumer-1"))

        self.assertIs(result, transaction)
        self.assertEqual(transaction.status, TransactionStatus.COMPLETED)
        self.assertIsInstance(transaction.completed_at, datetime)
        transaction.save.assert_awaited_once()

    async def test_consumer_cannot_complete_another_users_order(self):
        transaction = self.make_transaction()

        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=transaction),
        ):
            with self.assertRaisesRegex(ValueError, "your own orders"):
                await mark_order_completed("transaction-1", SimpleNamespace(id="consumer-2"))

        transaction.save.assert_not_awaited()

    async def test_completed_order_is_idempotent(self):
        transaction = self.make_transaction(status=TransactionStatus.COMPLETED)

        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=transaction),
        ):
            result = await mark_order_completed("transaction-1", SimpleNamespace(id="consumer-1"))

        self.assertIs(result, transaction)
        transaction.save.assert_not_awaited()

    async def test_consumer_cannot_complete_donation_transaction(self):
        transaction = self.make_transaction(transaction_type=TransactionType.DONATION)

        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=transaction),
        ):
            with self.assertRaisesRegex(ValueError, "not a consumer order"):
                await mark_order_completed("transaction-1", SimpleNamespace(id="consumer-1"))

        transaction.save.assert_not_awaited()

    async def test_consumer_cannot_complete_cancelled_order(self):
        transaction = self.make_transaction(status=TransactionStatus.CANCELLED)

        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=transaction),
        ):
            with self.assertRaisesRegex(ValueError, "Cancelled orders"):
                await mark_order_completed("transaction-1", SimpleNamespace(id="consumer-1"))

        transaction.save.assert_not_awaited()

    async def test_missing_transaction_is_rejected(self):
        with patch(
            "app.services.consumer_service.Transaction.get",
            new=AsyncMock(return_value=None),
        ):
            with self.assertRaisesRegex(ValueError, "Transaction not found"):
                await mark_order_completed("missing", SimpleNamespace(id="consumer-1"))

    async def test_reservation_delegates_to_listing_claim_flow(self):
        consumer = SimpleNamespace(id="consumer-1")
        expected = {"transaction_id": "transaction-1", "status": TransactionStatus.RESERVED}

        with patch(
            "app.services.consumer_service.claim_listing",
            new=AsyncMock(return_value=expected),
        ) as claim_listing:
            result = await reserve_food_listing(consumer, "listing-1", 2)

        self.assertEqual(result, expected)
        claim_listing.assert_awaited_once_with("listing-1", 2, consumer)

    async def test_waitlist_delegates_with_consumer_id(self):
        consumer = SimpleNamespace(id="consumer-1")
        expected = {"position": 1}

        with patch(
            "app.services.consumer_service.join_waitlist_entry",
            new=AsyncMock(return_value=expected),
        ) as waitlist_entry:
            result = await join_waitlist(consumer, "listing-1")

        self.assertEqual(result, expected)
        waitlist_entry.assert_awaited_once_with("consumer-1", "listing-1")

    def test_nearby_distance_calculation_is_reasonable(self):
        distance = _haversine_km(23.7461, 90.3742, 23.7510, 90.3800)
        self.assertGreater(distance, 0.0)
        self.assertLess(distance, 1.0)

    def test_location_matching_is_case_insensitive(self):
        self.assertTrue(_matches_location("Dhanmondi", "dHaNmoNdI"))
        self.assertFalse(_matches_location("Dhanmondi", "Gulshan"))


if __name__ == "__main__":
    unittest.main()
