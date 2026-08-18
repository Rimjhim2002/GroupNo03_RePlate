from fastapi import APIRouter,Depends
from app.controllers import auth_controller
from app.core.dependencies import get_current_user,session_scheme
from app.models.user import User
from app.schemas.user_schema import SessionResponse, UserLogin, UserRead, UserRegister
router =APIRouter(prefix="/auth",tags=["auth"])
@router.post("/register",response_model=SessionResponse)
async def register(data:UserRegister):
    return await auth_controller.register_user(data)

@router.post("/login",response_model=SessionResponse)
async def login(data:UserLogin):
    return await auth_controller.login_user(data)

@router.post("/logout")
async def logout(token: str =Depends(session_scheme)):
    await auth_controller.logout_user(token)
    return {"message": "Logged out successfully."}

@router.get("/me",response_model=UserRead)
async def get_me(current_user: User =Depends(get_current_user)):
    return UserRead(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        verification_status=current_user.verification_status,
        business_name=current_user.business_name,
        organization_name=current_user.organization_name,
    )