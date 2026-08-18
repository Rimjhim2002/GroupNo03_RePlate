from fastapi import Depends,HTTPException,status
from app.core.dependencies import get_current_user
from app.models.user import User,UserRole


def require_role(*allowed_roles:UserRole):
    """Usage: Depends(require_role(UserRole.RESTAURANT))"""

    async def role_checker(current_user: User =Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker