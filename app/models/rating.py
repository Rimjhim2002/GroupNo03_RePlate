from datetime import datetime,timezone
from beanie import Document,Link
from pydantic import Field
from app.models.transaction import Transaction
from app.models.user import User

class Rating(Document):
    from_user:Link[User]
    to_user:Link[User]
    transaction:Link[Transaction]
    stars: int =Field(ge=1, le=5)
    review:str
    created_at: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name ="ratings"