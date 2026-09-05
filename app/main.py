import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import init_db
from app.routes import (
    auth_routes,
    dashboard_routes,
    food_listing_routes,
    consumer_routes,
    lifecycle_routes,
    notification_routes,
    analytics_routes,
    rating_routes,
    report_routes,
)
from app.services.expiry_monitor import monitor_expiry


BASE_DIR = Path(__file__).resolve().parent.parent
VIEWS_DIR = BASE_DIR / "app" / "views"


def serve_html_file(filename: str) -> FileResponse:
    file_path = (VIEWS_DIR / filename).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"HTML file not found: {file_path}")
    return FileResponse(
        path=str(file_path),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    monitor_task = asyncio.create_task(monitor_expiry())
    try:
        yield
    finally:
        monitor_task.cancel()
        await asyncio.gather(monitor_task, return_exceptions=True)


app = FastAPI(title="RePlate API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(food_listing_routes.router)
app.include_router(consumer_routes.router)
app.include_router(lifecycle_routes.router)
app.include_router(notification_routes.router)
app.include_router(analytics_routes.router)
app.include_router(rating_routes.router)
app.include_router(report_routes.router)


@app.get("/")
async def serve_login_page():
    return serve_html_file("login.html")


@app.get("/dashboard")
async def serve_dashboard_page():
    return serve_html_file("login.html")


@app.get("/listings-view")
async def serve_listings_page():
    return serve_html_file("listings.html")


@app.get("/marketplace")
async def serve_marketplace_page():
    return serve_html_file("marketplace.html")


@app.get("/consumer-search")
async def serve_consumer_search_page():
    return serve_html_file("consumer_search.html")


@app.get("/consumer-history")
async def serve_consumer_history_page():
    return serve_html_file("consumer_history.html")


@app.get("/recommendations-view")
async def serve_recommendations_page():
    return serve_html_file("recommendations.html")


@app.get("/ngo-donations-view")
async def serve_ngo_donations_page():
    return serve_html_file("ngo-donations.html")


@app.get("/pickup-slots-view")
async def serve_pickup_slots_page():
    return serve_html_file("pickup-slots.html")


@app.get("/notifications-view")
async def serve_notifications_page():
    return serve_html_file("notifications.html")


@app.get("/analytics-view")
async def serve_analytics_page():
    return serve_html_file("analytics.html")


@app.get("/ratings-view")
async def serve_ratings_page():
    return serve_html_file("ratings.html")


@app.get("/reports-view")
async def serve_reports_page():
    return serve_html_file("reports.html")
