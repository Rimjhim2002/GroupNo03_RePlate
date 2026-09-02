from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.models.enums import ListingStatus
from app.models.food_listing import FoodListing
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analytics_schema import (
    CategoryDistributionItem,
    FoodWasteAnalyticsResponse,
    TrendDataPoint,
    WasteSummaryInsight,
)


def _get_ref_id(doc_or_ref: Any) -> str:
    if hasattr(doc_or_ref, "ref"):
        return str(doc_or_ref.ref.id)
    if hasattr(doc_or_ref, "id"):
        return str(doc_or_ref.id)
    return str(doc_or_ref)


async def get_restaurant_waste_analytics(restaurant: User) -> FoodWasteAnalyticsResponse:
    listings = await FoodListing.find(FoodListing.restaurant.id == restaurant.id).to_list()
    listing_map = {str(l.id): l for l in listings}
    listing_ids = set(listing_map.keys())

    all_transactions = await Transaction.find_all().to_list()
    restaurant_transactions = [
        t for t in all_transactions
        if _get_ref_id(t.food_listing) in listing_ids
    ]

    completed_txs = [
        t for t in restaurant_transactions
        if getattr(t.status, "value", t.status) == "completed"
    ]
    completed_sales = [
        t for t in completed_txs
        if getattr(t.type, "value", t.type) == "sale"
    ]
    completed_donations = [
        t for t in completed_txs
        if getattr(t.type, "value", t.type) == "donation"
    ]

    # 1. Category Distribution Breakdown
    cat_listed = defaultdict(int)
    cat_rescued = defaultdict(int)
    cat_wasted = defaultdict(int)
    cat_revenue = defaultdict(float)

    for l in listings:
        category = l.category or "Other"
        cat_listed[category] += int(l.quantity)
        if l.status == ListingStatus.EXPIRED:
            cat_wasted[category] += int(l.available_quantity)

    for t in completed_txs:
        lid = _get_ref_id(t.food_listing)
        if lid in listing_map:
            category = listing_map[lid].category or "Other"
            cat_rescued[category] += int(t.quantity)
            if getattr(t.type, "value", t.type) == "sale":
                cat_revenue[category] += float(t.total_amount)

    all_categories = sorted(list(cat_listed.keys()))
    category_items: list[CategoryDistributionItem] = []
    for cat in all_categories:
        tot = cat_listed[cat]
        resc = cat_rescued[cat]
        wast = cat_wasted[cat]
        rate = round((resc / tot * 100), 1) if tot > 0 else 0.0
        category_items.append(
            CategoryDistributionItem(
                category=cat,
                total_listed=tot,
                rescued_units=resc,
                wasted_units=wast,
                rescue_rate_percentage=rate,
                revenue_recovered=round(cat_revenue[cat], 2),
            )
        )

    # 2. Time-series / Monthly Trends
    period_sales = defaultdict(int)
    period_donations = defaultdict(int)
    period_revenue = defaultdict(float)
    period_expired = defaultdict(int)

    for t in completed_sales:
        dt = t.completed_at or t.reserved_at or datetime.now(timezone.utc)
        label = dt.strftime("%b %Y")
        period_sales[label] += int(t.quantity)
        period_revenue[label] += float(t.total_amount)

    for t in completed_donations:
        dt = t.completed_at or t.reserved_at or datetime.now(timezone.utc)
        label = dt.strftime("%b %Y")
        period_donations[label] += int(t.quantity)

    for l in listings:
        if l.status == ListingStatus.EXPIRED:
            dt = l.expiry_date or l.created_at or datetime.now(timezone.utc)
            label = dt.strftime("%b %Y")
            period_expired[label] += int(l.available_quantity)

    all_periods = sorted(
        list(set(list(period_sales.keys()) + list(period_donations.keys()) + list(period_expired.keys())))
    )
    if not all_periods:
        all_periods = [datetime.now(timezone.utc).strftime("%b %Y")]

    trend_items: list[TrendDataPoint] = []
    for p in all_periods:
        trend_items.append(
            TrendDataPoint(
                period_label=p,
                sale_units=period_sales[p],
                donation_units=period_donations[p],
                expired_units=period_expired[p],
                revenue_recovered=round(period_revenue[p], 2),
            )
        )

    # 3. Overall Waste Summary
    total_surplus_listed = sum(l.quantity for l in listings)
    total_rescued_units = sum(t.quantity for t in completed_txs)
    total_wasted_units = sum(l.available_quantity for l in listings if l.status == ListingStatus.EXPIRED)
    overall_rescue_rate = (
        round((total_rescued_units / total_surplus_listed * 100), 1)
        if total_surplus_listed > 0
        else 0.0
    )
    total_revenue_recovered = round(sum(float(t.total_amount) for t in completed_sales), 2)
    potential_revenue_lost = round(
        sum(
            float(l.original_price) * float(l.available_quantity)
            for l in listings
            if l.status == ListingStatus.EXPIRED
        ),
        2,
    )
    co2_avoided_kg = round(total_rescued_units * 2.5, 1)

    summary = WasteSummaryInsight(
        total_surplus_listed=total_surplus_listed,
        total_rescued_units=total_rescued_units,
        total_wasted_units=total_wasted_units,
        overall_rescue_rate=overall_rescue_rate,
        total_revenue_recovered=total_revenue_recovered,
        potential_revenue_lost=potential_revenue_lost,
        co2_avoided_kg=co2_avoided_kg,
    )

    # 4. Automated Actionable Insights
    insights: list[str] = []
    if total_surplus_listed == 0:
        insights.append("No surplus food listed yet. Create your first surplus listing to start tracking analytics.")
    else:
        if overall_rescue_rate >= 75.0:
            insights.append(
                f"Outstanding efficiency! You successfully rescued {overall_rescue_rate}% of your surplus inventory."
            )
        elif overall_rescue_rate >= 50.0:
            insights.append(
                f"Solid performance: {overall_rescue_rate}% of surplus food was rescued. Expanding donation windows can push this above 75%."
            )
        else:
            insights.append(
                f"High waste alert: {overall_rescue_rate}% rescue rate. Consider higher early discount percentages or automatic conversion to NGO donations."
            )

        # Category specific insights
        if category_items:
            best_cat = max(category_items, key=lambda c: c.rescue_rate_percentage)
            worst_cat = min(category_items, key=lambda c: c.rescue_rate_percentage)
            if best_cat.rescue_rate_percentage > 70.0 and best_cat.total_listed > 0:
                insights.append(
                    f"Top Rescued Category: '{best_cat.category}' has a high rescue rate of {best_cat.rescue_rate_percentage}%."
                )
            if worst_cat.wasted_units > 0 and worst_cat.category != best_cat.category:
                insights.append(
                    f"Action Required: '{worst_cat.category}' had {worst_cat.wasted_units} units expire. Try scheduling earlier pickup windows for this category."
                )

        donation_total = sum(t.quantity for t in completed_donations)
        if donation_total > 0:
            insights.append(
                f"Community Impact: {donation_total} meals were redistributed to verified charity partners and NGOs."
            )

        if co2_avoided_kg > 0:
            insights.append(
                f"Environmental Benefit: Rescuing {total_rescued_units} meals prevented ~{co2_avoided_kg} kg of CO2e emissions from landfill decomposition."
            )

    return FoodWasteAnalyticsResponse(
        restaurant_id=str(restaurant.id),
        restaurant_name=restaurant.business_name or restaurant.name,
        summary=summary,
        categories=category_items,
        trends=trend_items,
        insights=insights,
    )
