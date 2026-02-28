from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.application.dto.auth import AccessTokenPayload


class TokenPort(Protocol):
    def create_access_token(self, *, user_id: str, now: datetime) -> tuple[str, datetime]:
        ...

    def decode_access_token(self, *, token: str) -> AccessTokenPayload:
        ...

    def generate_refresh_token(self) -> str:
        ...

    def hash_refresh_token(self, *, refresh_token: str) -> str:
        ...

    def refresh_token_expires_at(self, *, now: datetime) -> datetime:
        ...
