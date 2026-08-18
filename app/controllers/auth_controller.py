from fastapi import HTTPException,status

from app.core.security import hash_password, verify_password
from app.models.session import Session
from app.models.user import User,UserRole
from app.schemas.user_schema import SessionResponse, UserLogin, UserRead, UserRegister


def _to_user_read(user: User) -> UserRead:
    return UserRead(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        verification_status=user.verification_status,
        business_name=user.business_name,
        organization_name=user.organization_name,
    )


async def register_user(data: UserRegister) -> SessionResponse:
    existing =await User.find_one(User.email == data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    if data.role ==UserRole.RESTAURANT and not data.business_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="business_name is required for restaurant accounts."
        )
    if data.role == UserRole.NGO and not data.organization_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_name is required for NGO accounts."
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=data.role,
        business_name=data.business_name,
        business_address=data.business_address,
        organization_name=data.organization_name,
        organization_address=data.organization_address,
    )
    await user.insert()
    session = Session(user=user)
    await session.insert()

    return SessionResponse(session_token=session.token, user=_to_user_read(user))


async def login_user(data: UserLogin) -> SessionResponse:
    user = await User.find_one(User.email == data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    session = Session(user=user)
    await session.insert()
    return SessionResponse(session_token=session.token,user=_to_user_read(user))


async def logout_user(token: str) -> None:
    session = await Session.find_one(Session.token == token)
    if session:
        await session.delete()