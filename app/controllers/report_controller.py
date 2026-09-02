from datetime import datetime, timezone
import io
import csv
from typing import Any, Optional
from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse, Response

from app.models.enums import ListingStatus, ReportFormat, ReportType
from app.models.food_listing import FoodListing
from app.models.monthly_statistics import MonthlyStatistics
from app.models.report import Report
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.report_schema import (
    MonthlyReportGenerateRequest,
    MonthlyStatisticsRead,
    ReportRead,
)


def _get_id(doc_or_ref: Any) -> str:
    if hasattr(doc_or_ref, "ref"):
        return str(doc_or_ref.ref.id)
    if hasattr(doc_or_ref, "id"):
        return str(doc_or_ref.id)
    return str(doc_or_ref)


def _matches_month(dt: Optional[datetime], target_month_str: str) -> bool:
    if not dt:
        return False
    return dt.strftime("%Y-%m") == target_month_str


async def generate_monthly_impact_report(
    data: MonthlyReportGenerateRequest,
    restaurant: User,
) -> ReportRead:
    now = datetime.now(timezone.utc)
    target_month = data.month.strip() if (data.month and data.month.strip()) else now.strftime("%Y-%m")

    # 1. Fetch restaurant listings
    listings = await FoodListing.find(FoodListing.restaurant.id == restaurant.id).to_list()
    listing_map = {str(l.id): l for l in listings}
    listing_ids = set(listing_map.keys())

    # Filter listings created in target month
    monthly_listings = [l for l in listings if _matches_month(l.created_at, target_month)]
    total_food_listed = sum(l.quantity for l in monthly_listings)
    total_food_expired = sum(
        l.available_quantity for l in monthly_listings if l.status == ListingStatus.EXPIRED
    )

    # 2. Fetch completed transactions for this restaurant's listings in target month
    all_transactions = await Transaction.find_all().to_list()
    monthly_completed_txs = [
        t for t in all_transactions
        if _get_id(t.food_listing) in listing_ids
        and getattr(t.status, "value", t.status) == "completed"
        and _matches_month(t.completed_at or t.reserved_at, target_month)
    ]

    completed_sales = [
        t for t in monthly_completed_txs
        if getattr(t.type, "value", t.type) == "sale"
    ]
    completed_donations = [
        t for t in monthly_completed_txs
        if getattr(t.type, "value", t.type) == "donation"
    ]

    total_meals_saved = sum(t.quantity for t in monthly_completed_txs)
    total_meals_donated = sum(t.quantity for t in completed_donations)
    total_revenue_recovered = round(sum(float(t.total_amount) for t in completed_sales), 2)
    waste_reduced_pct = (
        round((total_meals_saved / total_food_listed) * 100, 1)
        if total_food_listed > 0
        else (100.0 if total_meals_saved > 0 else 0.0)
    )
    co2_avoided_kg = round(total_meals_saved * 2.5, 1)

    # 3. Create or update MonthlyStatistics document
    stats = await MonthlyStatistics.find_one(
        MonthlyStatistics.restaurant.id == restaurant.id,
        MonthlyStatistics.month == target_month,
    )
    if not stats:
        stats = MonthlyStatistics(
            restaurant=restaurant,
            month=target_month,
            total_meals_saved=total_meals_saved,
            total_meals_donated=total_meals_donated,
            total_revenue_recovered=total_revenue_recovered,
            total_waste_reduced=waste_reduced_pct,
            total_food_listed=total_food_listed,
            total_food_expired=total_food_expired,
            co2_avoided_kg=co2_avoided_kg,
            generated_at=now,
        )
        await stats.insert()
    else:
        stats.total_meals_saved = total_meals_saved
        stats.total_meals_donated = total_meals_donated
        stats.total_revenue_recovered = total_revenue_recovered
        stats.total_waste_reduced = waste_reduced_pct
        stats.total_food_listed = total_food_listed
        stats.total_food_expired = total_food_expired
        stats.co2_avoided_kg = co2_avoided_kg
        stats.generated_at = now
        await stats.save()

    # 4. Generate CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["RePlate Monthly Impact Report", target_month])
    writer.writerow(["Restaurant", restaurant.business_name or restaurant.name])
    writer.writerow(["Generated At", now.isoformat()])
    writer.writerow([])
    writer.writerow(["Metric", "Value", "Unit"])
    writer.writerow(["Total Food Listed", total_food_listed, "Units"])
    writer.writerow(["Total Meals Saved", total_meals_saved, "Units"])
    writer.writerow(["Meals Donated to NGOs", total_meals_donated, "Units"])
    writer.writerow(["Revenue Recovered", f"${total_revenue_recovered:.2f}", "USD"])
    writer.writerow(["Waste Reduced Percentage", f"{waste_reduced_pct:.1f}%", "%"])
    writer.writerow(["CO2e Emissions Avoided", f"{co2_avoided_kg:.1f}", "kg CO2e"])
    writer.writerow(["Total Food Expired / Lost", total_food_expired, "Units"])
    csv_text = output.getvalue()

    # 5. Create Report record
    report = Report(
        restaurant=restaurant,
        report_type=ReportType.IMPACT_REPORT,
        format=data.format,
        month=target_month,
        data=stats,
        content=csv_text,
        generated_at=now,
    )
    await report.insert()

    stats_read = MonthlyStatisticsRead(
        id=str(stats.id),
        month=stats.month,
        restaurant_name=restaurant.business_name or restaurant.name,
        total_meals_saved=stats.total_meals_saved,
        total_meals_donated=stats.total_meals_donated,
        total_revenue_recovered=stats.total_revenue_recovered,
        total_waste_reduced=stats.total_waste_reduced,
        total_food_listed=stats.total_food_listed,
        total_food_expired=stats.total_food_expired,
        co2_avoided_kg=stats.co2_avoided_kg,
        generated_at=stats.generated_at,
    )

    return ReportRead(
        id=str(report.id),
        report_type=report.report_type,
        format=report.format,
        month=report.month,
        restaurant_name=restaurant.business_name or restaurant.name,
        statistics=stats_read,
        generated_at=report.generated_at,
    )


async def list_restaurant_reports(restaurant: User) -> list[ReportRead]:
    reports = await Report.find(Report.restaurant.id == restaurant.id).sort("-generated_at").to_list()
    result = []
    for r in reports:
        stats = await MonthlyStatistics.get(_get_id(r.data))
        if not stats:
            continue
        stats_read = MonthlyStatisticsRead(
            id=str(stats.id),
            month=stats.month,
            restaurant_name=restaurant.business_name or restaurant.name,
            total_meals_saved=stats.total_meals_saved,
            total_meals_donated=stats.total_meals_donated,
            total_revenue_recovered=stats.total_revenue_recovered,
            total_waste_reduced=stats.total_waste_reduced,
            total_food_listed=stats.total_food_listed,
            total_food_expired=stats.total_food_expired,
            co2_avoided_kg=stats.co2_avoided_kg,
            generated_at=stats.generated_at,
        )
        result.append(
            ReportRead(
                id=str(r.id),
                report_type=r.report_type,
                format=r.format,
                month=r.month,
                restaurant_name=restaurant.business_name or restaurant.name,
                statistics=stats_read,
                generated_at=r.generated_at,
            )
        )
    return result


async def export_report_csv(report_id: str, user: User) -> Response:
    report = await Report.get(report_id)
    if not report or _get_id(report.restaurant) != str(user.id):
        raise HTTPException(status_code=404, detail="Report not found.")

    content = report.content or "No content"
    filename = f"RePlate_Impact_Report_{report.month or 'month'}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def export_report_print_view(report_id: str, user: User) -> HTMLResponse:
    report = await Report.get(report_id)
    if not report or _get_id(report.restaurant) != str(user.id):
        raise HTTPException(status_code=404, detail="Report not found.")

    stats = await MonthlyStatistics.get(_get_id(report.data))
    if not stats:
        raise HTTPException(status_code=404, detail="Report data not found.")

    rest_name = user.business_name or user.name

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RePlate Impact Certificate — {report.month}</title>
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #f8fafc; color: #0f172a; padding: 40px; }}
  .cert-card {{ max-width: 750px; margin: 0 auto; background: #fff; border: 2px solid #0B2545; border-radius: 16px; padding: 48px; box-shadow: 0 10px 30px rgba(0,0,0,0.06); position: relative; }}
  .cert-badge {{ display: inline-block; background: #10B981; color: #fff; font-weight: 700; font-size: 11px; padding: 4px 12px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .cert-title {{ font-size: 28px; font-weight: 800; color: #0B2545; margin-top: 12px; }}
  .cert-sub {{ font-size: 14px; color: #64748b; margin-top: 4px; margin-bottom: 30px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 30px; }}
  .box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; }}
  .box-label {{ font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; }}
  .box-val {{ font-size: 24px; font-weight: 700; color: #0B2545; margin-top: 4px; }}
  .foot {{ border-top: 1.5px dashed #cbd5e1; padding-top: 20px; display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; }}
  .print-btn {{ display: block; margin: 20px auto 0; padding: 10px 24px; background: #1D4ED8; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }}
  @media print {{ .print-btn {{ display: none; }} body {{ padding: 0; background: #fff; }} .cert-card {{ border: none; box-shadow: none; }} }}
</style>
</head>
<body>
<div class="cert-card">
  <div class="cert-badge">Official Sustainability Audit</div>
  <div class="cert-title">Monthly Environmental & Operational Impact Certificate</div>
  <div class="cert-sub">Presented to <strong>{rest_name}</strong> for performance in <strong>{report.month}</strong></div>

  <div class="grid">
    <div class="box"><div class="box-label">Total Meals Rescued</div><div class="box-val">{stats.total_meals_saved} meals</div></div>
    <div class="box"><div class="box-label">Meals Donated to NGOs</div><div class="box-val">{stats.total_meals_donated} donations</div></div>
    <div class="box"><div class="box-label">Revenue Recovered</div><div class="box-val">${stats.total_revenue_recovered:.2f}</div></div>
    <div class="box"><div class="box-label">Waste Reduction Rate</div><div class="box-val">{stats.total_waste_reduced:.1f}%</div></div>
    <div class="box"><div class="box-label">Avoided Landfill Emissions</div><div class="box-val">{stats.co2_avoided_kg:.1f} kg CO₂e</div></div>
    <div class="box"><div class="box-label">Surplus Inventory Listed</div><div class="box-val">{stats.total_food_listed} units</div></div>
  </div>

  <div class="foot">
    <span>Platform: RePlate Smart Food Lifecycle</span>
    <span>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</span>
  </div>
</div>
<button class="print-btn" onclick="window.print()">🖨️ Print Certificate / Save as PDF</button>
</body>
</html>"""
    return HTMLResponse(content=html_content)
