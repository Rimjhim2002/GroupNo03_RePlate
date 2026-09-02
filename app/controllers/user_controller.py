from app.models.user import User
from app.schemas.user_schema import LocationUpdate, UserRead


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


async def update_location(user: User, data: LocationUpdate) -> UserRead:
    user.latitude = data.latitude
    user.longitude = data.longitude
    await user.save()
    return _to_user_read(user)