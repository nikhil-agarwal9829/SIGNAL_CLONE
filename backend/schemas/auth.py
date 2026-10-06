from pydantic import BaseModel
from typing import Optional

class PhoneRequest(BaseModel):
    phone: str

class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str

class ProfileCreateRequest(BaseModel):
    display_name: str
    avatar_url: Optional[str] = None
    about: Optional[str] = None

class SessionResponse(BaseModel):
    message: str
    is_new_user: bool
