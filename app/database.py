from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.food_listing import FoodListing
from app.models.food_recommendation import FoodRecommendation
from app.models.monthly_statistics import MonthlyStatistics
from app.models.notification import Notification
from app.models.rating import Rating
from app.models.report import Report
from app.models.transaction import Transaction
from app.models.user import User
from app.models.waitlist import Waitlist
from app.models.session import Session
DOCUMENT_MODELS = [
    User,
    Session,
    FoodListing,
    Transaction,
    Waitlist,
    Notification,
    Rating,
    FoodRecommendation,
    MonthlyStatistics,
    Report
]

async def init_db():
    client = AsyncIOMotorClient(settings.mongo_uri)
    db = client[settings.mongo_db_name]
    await init_beanie(database=db,document_models=DOCUMENT_MODELS)