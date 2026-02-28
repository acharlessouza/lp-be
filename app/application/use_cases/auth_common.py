from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.application.dto.auth import AuthTokensOutput, AuthUserOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.token_port import TokenPort
from app.domain.entities.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_auth_user_output(user: User) -> AuthUserOutput:
    return AuthUserOutput(
        id=user.id,
        name=user.name,
        email=user.email,
        email_verified=user.email_verified,
        is_active=user.is_active,
    )


def issue_tokens(
    *,
    user: User,
    auth_port: AuthPort,
    token_port: TokenPort,
    user_agent: str | None,
    ip: str | None,
) -> AuthTokensOutput:
    now = utcnow()
    access_token, access_expires_at = token_port.create_access_token(user_id=user.id, now=now)
    refresh_token = token_port.generate_refresh_token()
    refresh_hash = token_port.hash_refresh_token(refresh_token=refresh_token)
    refresh_expires_at = token_port.refresh_token_expires_at(now=now)
    auth_port.create_session(
        session_id=str(uuid4()),
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        expires_at=refresh_expires_at,
        revoked_at=None,
        user_agent=user_agent,
        ip=ip,
        created_at=now,
    )
    return AuthTokensOutput(
        user=build_auth_user_output(user),
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )
