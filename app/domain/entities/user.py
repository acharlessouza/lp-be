from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


AuthProvider = Literal["local", "google"]


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    email_verified: bool
    is_active: bool
    stripe_customer_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AuthIdentity:
    id: str
    user_id: str
    provider: AuthProvider
    provider_subject: str | None
    password_hash: str | None
    created_at: datetime


@dataclass(frozen=True)
class AuthSession:
    id: str
    user_id: str
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    user_agent: str | None
    ip: str | None
    created_at: datetime
