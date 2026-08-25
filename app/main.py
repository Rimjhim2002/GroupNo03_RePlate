from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db
from app.routes import auth_routes
from app.routes import auth_routes, dashboard_routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.routes import auth_routes, dashboard_routes, food_listing_routes
@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db()
    yield


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

@app.get("/")
async def serve_login_page():
    return FileResponse("app/views/login.html")
@app.get("/listings-view")
async def serve_listings_page():
    return FileResponse("app/views/listings.html")