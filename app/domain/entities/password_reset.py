from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PasswordResetToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
    requested_ip: str | None
    user_agent: str | None
