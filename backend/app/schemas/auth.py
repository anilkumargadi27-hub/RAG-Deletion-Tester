from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    token: Optional[str] = None # For programmatic / CLI tests

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "member" # admin, auditor, member
