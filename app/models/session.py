import secrets
from datetime import datetime,timedelta,timezone

from beanie import Document,Link
from pydantic import Field

from app.models.user import User

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def default_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


class Session(Document):
    token: str = Field(default_factory=generate_session_token)
    user: Link[User]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(default_factory=default_expiry)

    class Settings:
        name = "sessions"