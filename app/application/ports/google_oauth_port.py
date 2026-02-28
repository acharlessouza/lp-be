from __future__ import annotations

from typing import Protocol

from app.application.dto.auth import GoogleIdentityInfo


class GoogleOauthPort(Protocol):
    def verify_id_token(self, *, id_token: str) -> GoogleIdentityInfo:
        ...
