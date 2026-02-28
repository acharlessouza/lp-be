from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthUserOutput:
    id: str
    name: str
    email: str
    email_verified: bool
    is_active: bool


@dataclass(frozen=True)
class RegisterUserInput:
    name: str
    email: str
    password: str


@dataclass(frozen=True)
class RegisterUserOutput:
    user: AuthUserOutput


@dataclass(frozen=True)
class LoginLocalInput:
    email: str
    password: str
    user_agent: str | None
    ip: str | None


@dataclass(frozen=True)
class LoginGoogleInput:
    id_token: str
    user_agent: str | None
    ip: str | None


@dataclass(frozen=True)
class RefreshSessionInput:
    refresh_token: str
    user_agent: str | None
    ip: str | None


@dataclass(frozen=True)
class LogoutInput:
    refresh_token: str


@dataclass(frozen=True)
class AuthTokensOutput:
    user: AuthUserOutput
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass(frozen=True)
class AccessTokenPayload:
    user_id: str


@dataclass(frozen=True)
class GoogleIdentityInfo:
    subject: str
    email: str
    email_verified: bool
    name: str | None
