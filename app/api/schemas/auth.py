from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=256)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=1)


class AuthUserResponse(BaseModel):
    id: str
    name: str
    email: str
    email_verified: bool
    is_active: bool


class RegisterResponse(BaseModel):
    user: AuthUserResponse


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    user: AuthUserResponse


class LogoutResponse(BaseModel):
    ok: bool
