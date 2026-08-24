from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_database
from routes.food_listing import router as food_listing_router


app = FastAPI(
    title="RePlate API",
    description="Smart Food Lifecycle Management Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_database()


app.include_router(food_listing_router)


@app.get("/")
async def root():
    return {"message": "Welcome to RePlate API"}
