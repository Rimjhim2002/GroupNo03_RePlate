from datetime import datetime,timezone

from fastapi import Depends,HTTPException,status
from fastapi.security import APIKeyHeader

from app.models.session import Session
from app.models.user import User

session_scheme = APIKeyHeader(name="Authorization", auto_error=True)


async def get_current_user(token: str = Depends(session_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in again.",
    )

    session = await Session.find_one(Session.token == token)
    if session is None:
        raise credentials_exception

    if session.expires_at.tzinfo is None:
        session_expires_at = session.expires_at.replace(tzinfo=timezone.utc)
    else:
        session_expires_at = session.expires_at

    if session_expires_at < datetime.now(timezone.utc):
        await session.delete()
        raise credentials_exception

    user = await session.user.fetch()
    if user is None:
        raise credentials_exception

    return user