import unittest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from app.database import init_db
from app.models.enums import (
    ListingApprovalStatus,
    ListingStatus,
    ListingType,
    NotificationType,
    ReportFormat,
    TransactionStatus,
    TransactionType,
)
from app.models.food_listing import FoodListing
from app.models.notification import Notification
from app.models.rating import Rating
from app.models.report import Report
from app.models.monthly_statistics import MonthlyStatistics
from app.models.transaction import Transaction
from app.models.user import User, UserRole, VerificationStatus

from app.controllers.notification_controller import (
    _haversine_km,
    create_notification,
    notify_nearby_users_of_new_listing,
    mark_as_read,
)
from app.controllers.dashboard_controller import get_restaurant_dashboard
from app.controllers.analytics_controller import get_restaurant_waste_analytics
from app.controllers.rating_controller import submit_rating, get_user_ratings
from app.controllers.report_controller import (
    generate_monthly_impact_report,
    export_report_csv,
)
from app.schemas.rating_schema import RatingCreate
from app.schemas.report_schema import MonthlyReportGenerateRequest


class TestMember4Features(unittest.IsolatedAsyncioTestCase):
    """
    Unit test suite covering the 10 core methods of Member 4's features:
    1. _haversine_km
    2. create_notification
    3. notify_nearby_users_of_new_listing
    4. mark_as_read
    5. get_restaurant_dashboard
    6. get_restaurant_waste_analytics
    7. submit_rating
    8. get_user_ratings
    9. generate_monthly_impact_report
    10. export_report_csv
    """

    async def asyncSetUp(self):
        await init_db()
        self.ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.restaurant = User(
            name=f"Test Chef {self.ts}",
            email=f"chef_{self.ts}@test.com",
            phone="01711000001",
            role=UserRole.RESTAURANT,
            password_hash="hashed",
            business_name=f"Green Bistro {self.ts}",
            verification_status=VerificationStatus.VERIFIED,
            latitude=23.7461,
            longitude=90.3742,  # Dhanmondi, Dhaka
        )
        await self.restaurant.insert()

        self.consumer = User(
            name=f"Test Consumer {self.ts}",
            email=f"consumer_{self.ts}@test.com",
            phone="01711000002",
            role=UserRole.CONSUMER,
            password_hash="hashed",
            latitude=23.7510,
            longitude=90.3800,  # ~0.8 km away
        )
        await self.consumer.insert()

        self.far_consumer = User(
            name=f"Far Consumer {self.ts}",
            email=f"far_{self.ts}@test.com",
            phone="01711000003",
            role=UserRole.CONSUMER,
            password_hash="hashed",
            latitude=24.5000,
            longitude=91.5000,  # ~140 km away
        )
        await self.far_consumer.insert()

    async def asyncTearDown(self):
        await Notification.find(Notification.recipient.id == self.consumer.id).delete()
        await Notification.find(Notification.recipient.id == self.restaurant.id).delete()
        await Rating.find(Rating.from_user.id == self.consumer.id).delete()
        await Report.find(Report.restaurant.id == self.restaurant.id).delete()
        await MonthlyStatistics.find(MonthlyStatistics.restaurant.id == self.restaurant.id).delete()
        await FoodListing.find(FoodListing.restaurant.id == self.restaurant.id).delete()
        await self.restaurant.delete()
        await self.consumer.delete()
        await self.far_consumer.delete()

    # ---------------------------------------------------------
    # METHOD 1: _haversine_km (notification_controller.py)
    # ---------------------------------------------------------
    def test_01_haversine_km(self):
        """Method 1: Tests accurate spherical distance calculation."""
        dist_same = _haversine_km(23.7461, 90.3742, 23.7461, 90.3742)
        self.assertEqual(dist_same, 0.0)

        dist = _haversine_km(23.7461, 90.3742, 23.7925, 90.4078)
        self.assertGreater(dist, 5.0)
        self.assertLess(dist, 8.5)

    # ---------------------------------------------------------
    # METHOD 2: create_notification (notification_controller.py)
    # ---------------------------------------------------------
    async def test_02_create_notification(self):
        """Method 2: Tests notification creation with timestamp and unread state."""
        notif = await create_notification(
            recipient=self.consumer,
            title="Surplus Alert",
            type=NotificationType.NEW_LISTING_NEARBY,
            message="Fresh bread available at 50% discount.",
        )
        self.assertIsNotNone(notif.id)
        self.assertEqual(notif.title, "Surplus Alert")
        self.assertEqual(notif.type, NotificationType.NEW_LISTING_NEARBY)
        self.assertFalse(notif.is_read)
        self.assertIsNotNone(notif.sent_at)

    # ---------------------------------------------------------
    # METHOD 3: notify_nearby_users_of_new_listing (notification_controller.py)
    # ---------------------------------------------------------
    async def test_03_notify_nearby_users_of_new_listing(self):
        """Method 3: Tests proximity-based notification dispatch within radius."""
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Fresh Pastries",
            description="Baked this morning",
            category="Bakery",
            listing_type=ListingType.SALE,
            quantity=10,
            available_quantity=10,
            unit="pcs",
            original_price=10.0,
            discount_percentage=50.0,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=8),
            pickup_location="Dhanmondi",
            latitude=23.7461,
            longitude=90.3742,
            status=ListingStatus.AVAILABLE,
            approval_status=ListingApprovalStatus.APPROVED,
        )
        await listing.insert()

        notified = await notify_nearby_users_of_new_listing(listing, self.restaurant, radius_km=5.0)
        self.assertGreaterEqual(notified, 1)

        user_notifs = await Notification.find(
            Notification.recipient.id == self.consumer.id,
            Notification.type == NotificationType.NEW_LISTING_NEARBY,
        ).to_list()
        self.assertGreaterEqual(len(user_notifs), 1)

        far_notifs = await Notification.find(
            Notification.recipient.id == self.far_consumer.id,
            Notification.message == f"{self.restaurant.business_name} just listed 'Fresh Pastries' near you.",
        ).to_list()
        self.assertEqual(len(far_notifs), 0)

    # ---------------------------------------------------------
    # METHOD 4: mark_as_read (notification_controller.py)
    # ---------------------------------------------------------
    async def test_04_mark_as_read(self):
        """Method 4: Tests marking notification as read and ownership authorization."""
        notif = await create_notification(
            recipient=self.consumer,
            title="Surplus Alert",
            type=NotificationType.NEW_LISTING_NEARBY,
            message="Your listing is nearby.",
        )
        res = await mark_as_read(str(notif.id), self.consumer)
        self.assertTrue(res.is_read)

        updated_notif = await Notification.get(notif.id)
        self.assertTrue(updated_notif.is_read)

        with self.assertRaises(HTTPException) as ctx:
            await mark_as_read(str(notif.id), self.restaurant)
        self.assertEqual(ctx.exception.status_code, 403)

    # ---------------------------------------------------------
    # METHOD 5: get_restaurant_dashboard (dashboard_controller.py)
    # ---------------------------------------------------------
    async def test_05_get_restaurant_dashboard(self):
        """Method 5: Tests sustainability dashboard calculations and metrics."""
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Organic Rice Bowl",
            description="Wholesome grain bowl",
            category="Prepared Meals",
            listing_type=ListingType.SALE,
            quantity=20,
            available_quantity=5,
            unit="bowls",
            original_price=12.0,
            discount_percentage=50.0,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=6),
            pickup_location="Counter 1",
            status=ListingStatus.AVAILABLE,
            approval_status=ListingApprovalStatus.APPROVED,
        )
        await listing.insert()

        tx = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=15,
            total_amount=90.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx.insert()

        dash = await get_restaurant_dashboard(self.restaurant)

        self.assertEqual(dash["food_saved_count"], 15)
        self.assertEqual(dash["revenue_recovered"], 90.0)
        self.assertEqual(dash["total_food_listed"], 20)
        self.assertEqual(dash["waste_reduced_percentage"], 75.0)
        self.assertEqual(dash["waste_value_avoided"], 180.0)

        await tx.delete()

    # ---------------------------------------------------------
    # METHOD 6: get_restaurant_waste_analytics (analytics_controller.py)
    # ---------------------------------------------------------
    async def test_06_get_restaurant_waste_analytics(self):
        """Method 6: Tests category breakdown, trend points, CO2 avoided, and automated insights."""
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Fresh Vegetable Soup",
            description="Warm hearty vegetable soup",
            category="Soups",
            listing_type=ListingType.SALE,
            quantity=10,
            available_quantity=2,
            unit="bowls",
            original_price=5.0,
            discount_percentage=20.0,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=4),
            pickup_location="Main Desk",
            status=ListingStatus.AVAILABLE,
            approval_status=ListingApprovalStatus.APPROVED,
        )
        await listing.insert()

        tx = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=8,
            total_amount=32.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx.insert()

        analytics = await get_restaurant_waste_analytics(self.restaurant)

        self.assertEqual(analytics.summary.total_rescued_units, 8)
        self.assertEqual(analytics.summary.co2_avoided_kg, 20.0)
        self.assertEqual(analytics.summary.total_revenue_recovered, 32.0)

        soup_cat = next((c for c in analytics.categories if c.category == "Soups"), None)
        self.assertIsNotNone(soup_cat)
        self.assertEqual(soup_cat.rescued_units, 8)
        self.assertEqual(soup_cat.rescue_rate_percentage, 80.0)

        self.assertGreater(len(analytics.insights), 0)
        self.assertTrue(any("CO2e" in s or "rescued" in s.lower() for s in analytics.insights))

        await tx.delete()

    # ---------------------------------------------------------
    # METHOD 7: submit_rating (rating_controller.py)
    # ---------------------------------------------------------
    async def test_07_submit_rating(self):
        """Method 7: Tests rating submission, completion verification, duplicate prevention, and alert trigger."""
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Gourmet Sandwich",
            description="Toasted club sandwich",
            category="Bakery",
            listing_type=ListingType.SALE,
            quantity=5,
            available_quantity=0,
            unit="items",
            original_price=8.0,
            discount_percentage=25.0,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=2),
            pickup_location="Pickup Point",
            status=ListingStatus.COMPLETED,
            approval_status=ListingApprovalStatus.APPROVED,
        )
        await listing.insert()

        tx = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=5,
            total_amount=30.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx.insert()

        dto = RatingCreate(
            transaction_id=str(tx.id),
            stars=5,
            review="Excellent food quality and packaging!",
        )
        res = await submit_rating(dto, self.consumer)
        self.assertEqual(res.stars, 5)
        self.assertEqual(res.from_user_id, str(self.consumer.id))
        self.assertEqual(res.to_user_id, str(self.restaurant.id))

        notif = await Notification.find_one(
            Notification.recipient.id == self.restaurant.id,
            Notification.type == NotificationType.RATING_RECEIVED,
        )
        self.assertIsNotNone(notif)
        self.assertIn("⭐⭐⭐⭐⭐", notif.message)

        with self.assertRaises(HTTPException) as ctx:
            await submit_rating(dto, self.consumer)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already submitted", ctx.exception.detail)

        await tx.delete()

    # ---------------------------------------------------------
    # METHOD 8: get_user_ratings (rating_controller.py)
    # ---------------------------------------------------------
    async def test_08_get_user_ratings(self):
        """Method 8: Tests aggregation of stars, breakdown counts, and overall average."""
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Rating Target Item",
            description="Sample item",
            category="Snacks",
            listing_type=ListingType.SALE,
            quantity=5,
            available_quantity=0,
            unit="units",
            original_price=5.0,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=1),
            pickup_location="Pickup Counter",
            status=ListingStatus.COMPLETED,
            approval_status=ListingApprovalStatus.APPROVED,
        )
        await listing.insert()

        tx1 = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=2,
            total_amount=10.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx1.insert()

        tx2 = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=3,
            total_amount=15.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx2.insert()

        r1 = Rating(
            from_user=self.consumer,
            to_user=self.restaurant,
            transaction=tx1,
            stars=5,
            review="Top notch!",
            created_at=datetime.now(timezone.utc),
        )
        await r1.insert()

        r2 = Rating(
            from_user=self.consumer,
            to_user=self.restaurant,
            transaction=tx2,
            stars=4,
            review="Very good surplus quality.",
            created_at=datetime.now(timezone.utc),
        )
        await r2.insert()

        summary = await get_user_ratings(str(self.restaurant.id))

        self.assertEqual(summary.total_ratings, 2)
        self.assertEqual(summary.average_stars, 4.5)
        self.assertEqual(summary.star_breakdown[5], 1)
        self.assertEqual(summary.star_breakdown[4], 1)
        self.assertEqual(summary.star_breakdown[1], 0)

        await r1.delete()
        await r2.delete()
        await tx1.delete()
        await tx2.delete()

    # ---------------------------------------------------------
    # METHOD 9: generate_monthly_impact_report (report_controller.py)
    # ---------------------------------------------------------
    async def test_09_generate_monthly_impact_report(self):
        """Method 9: Tests monthly statistics aggregation, CO2 computation, and report creation."""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        listing = FoodListing(
            restaurant=self.restaurant,
            food_name="Pasta Box",
            description="Italian pasta ready to eat",
            category="Italian",
            listing_type=ListingType.SALE,
            quantity=10,
            available_quantity=0,
            unit="boxes",
            original_price=15.0,
            discount_percentage=33.3,
            expiry_date=datetime.now(timezone.utc) + timedelta(hours=3),
            pickup_location="Front Counter",
            status=ListingStatus.COMPLETED,
            approval_status=ListingApprovalStatus.APPROVED,
            created_at=datetime.now(timezone.utc),
        )
        await listing.insert()

        tx = Transaction(
            food_listing=listing,
            claimed_by=self.consumer,
            type=TransactionType.SALE,
            quantity=10,
            total_amount=100.0,
            status=TransactionStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        await tx.insert()

        req = MonthlyReportGenerateRequest(month=current_month, format=ReportFormat.CSV)
        report_read = await generate_monthly_impact_report(req, self.restaurant)

        self.assertEqual(report_read.month, current_month)
        self.assertEqual(report_read.statistics.total_meals_saved, 10)
        self.assertEqual(report_read.statistics.total_revenue_recovered, 100.0)
        self.assertEqual(report_read.statistics.co2_avoided_kg, 25.0)
        self.assertEqual(report_read.statistics.total_waste_reduced, 100.0)

        stat_doc = await MonthlyStatistics.find_one(
            MonthlyStatistics.restaurant.id == self.restaurant.id,
            MonthlyStatistics.month == current_month,
        )
        self.assertIsNotNone(stat_doc)
        self.assertEqual(stat_doc.total_meals_saved, 10)

        await tx.delete()

    # ---------------------------------------------------------
    # METHOD 10: export_report_csv (report_controller.py)
    # ---------------------------------------------------------
    async def test_10_export_report_csv(self):
        """Method 10: Tests CSV report download, media type, headers, and access control."""
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        req = MonthlyReportGenerateRequest(month=current_month, format=ReportFormat.CSV)
        report_read = await generate_monthly_impact_report(req, self.restaurant)

        csv_response = await export_report_csv(report_read.id, self.restaurant)
        self.assertEqual(csv_response.media_type, "text/csv")
        self.assertIn("attachment; filename=RePlate_Impact_Report", csv_response.headers["Content-Disposition"])
        self.assertIn("RePlate Monthly Impact Report", csv_response.body.decode("utf-8"))
        self.assertIn("CO2e Emissions Avoided", csv_response.body.decode("utf-8"))

        with self.assertRaises(HTTPException) as ctx:
            await export_report_csv(report_read.id, self.consumer)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
