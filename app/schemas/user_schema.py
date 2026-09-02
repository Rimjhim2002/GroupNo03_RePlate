from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole, VerificationStatus


class UserRegister(BaseModel):
    name:str
    email:EmailStr
    password:str
    phone:str
    role: UserRole
    business_name:Optional[str] =None
    business_address:Optional[str] =None
    organization_name: Optional[str] =None
    organization_address:Optional[str] =None


class UserLogin(BaseModel):
    email:EmailStr
    password:str


class UserRead(BaseModel):
    id:str
    name:str
    email:EmailStr
    phone:str
    role:UserRole
    verification_status:VerificationStatus
    business_name:Optional[str] =None
    organization_name: Optional[str] =None


class SessionResponse(BaseModel):
    session_token:str
    user:UserRead
class LocationUpdate(BaseModel):
    latitude: float
    longitude: float