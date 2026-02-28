from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.application.dto.auth import AccessTokenPayload
from app.application.ports.token_port import TokenPort


class JwtTokenService(TokenPort):
    def __init__(
        self,
        *,
        jwt_secret: str,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
    ):
        self._jwt_secret = jwt_secret
        self._access_ttl_minutes = access_ttl_minutes
        self._refresh_ttl_days = refresh_ttl_days

    def create_access_token(self, *, user_id: str, now: datetime) -> tuple[str, datetime]:
        exp = now + timedelta(minutes=self._access_ttl_minutes)
        payload = {
            "sub": user_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = jwt.encode(payload, self._jwt_secret, algorithm="HS256")
        return token, exp

    def decode_access_token(self, *, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid access token.") from exc

        if payload.get("type") != "access":
            raise ValueError("Invalid token type.")

        user_id = payload.get("sub")
        if not user_id or not isinstance(user_id, str):
            raise ValueError("Invalid token subject.")

        return AccessTokenPayload(user_id=user_id)

    def generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_refresh_token(self, *, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    def refresh_token_expires_at(self, *, now: datetime) -> datetime:
        return now + timedelta(days=self._refresh_ttl_days)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
