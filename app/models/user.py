from datetime import datetime,timezone
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import EmailStr,Field


class UserRole(str,Enum):
    RESTAURANT ="restaurant"
    CONSUMER ="consumer"
    NGO ="ngo"
    ADMINISTRATOR ="administrator"


class VerificationStatus(str,Enum):
    PENDING ="pending"
    VERIFIED ="verified"
    REJECTED ="rejected"

class User(Document):
    name:str
    email:EmailStr
    password_hash:str
    phone:str
    role:UserRole
    verification_status: VerificationStatus =VerificationStatus.PENDING
    latitude: Optional[float] =None
    longitude: Optional[float] =None
    created_at: datetime =Field(default_factory=lambda: datetime.now(timezone.utc))

    # Restaurant-only
    business_name: Optional[str] =None
    business_address: Optional[str] =None

    # NGO-only
    organization_name: Optional[str] =None
    organization_address: Optional[str] =None

    class Settings:
        name ="users"