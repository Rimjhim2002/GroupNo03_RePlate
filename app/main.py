import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routes import auth_routes
from app.routes import auth_routes, dashboard_routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.routes import auth_routes, dashboard_routes, food_listing_routes, consumer_routes
from app.routes import lifecycle_routes  # <-- NEW: your router
from app.services.expiry_monitor import monitor_expiry
@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db()
    monitor_task = asyncio.create_task(monitor_expiry())
    try:
        yield
    finally:
        monitor_task.cancel()
        await asyncio.gather(monitor_task, return_exceptions=True)
 
 
app = FastAPI(title="RePlate API",lifespan=lifespan)
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
app.include_router(lifecycle_routes.router)  # <-- NEW: registers your 5 features' endpoints
 
@app.get("/")
async def serve_login_page():
    return FileResponse("app/views/login.html")
@app.get("/listings-view")
async def serve_listings_page():
    return FileResponse("app/views/listings.html")
 
 
@app.get("/marketplace")
async def serve_marketplace_page():
    return FileResponse("app/views/marketplace.html")
 
# ---------- NEW: your 4 pages ----------
@app.get("/recommendations-view")
async def serve_recommendations_page():
    return FileResponse("app/views/recommendations.html")
 
@app.get("/ngo-donations-view")
async def serve_ngo_donations_page():
    return FileResponse("app/views/ngo-donations.html")
 
@app.get("/pickup-slots-view")
async def serve_pickup_slots_page():
    return FileResponse("app/views/pickup-slots.html")

@app.get("/consumer-discovery-view")
async def serve_consumer_discovery_page():
    return FileResponse("app/views/consumer-discovery.html")