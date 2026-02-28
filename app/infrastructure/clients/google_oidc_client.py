from __future__ import annotations

from google.auth.transport import requests
from google.oauth2 import id_token

from app.application.dto.auth import GoogleIdentityInfo
from app.application.ports.google_oauth_port import GoogleOauthPort
from app.domain.exceptions import GoogleTokenValidationError


class GoogleOidcClient(GoogleOauthPort):
    def __init__(self, *, client_id: str):
        self._client_id = client_id

    def verify_id_token(self, *, id_token: str) -> GoogleIdentityInfo:
        try:
            payload = id_token_verify(token=id_token, audience=self._client_id)
        except Exception as exc:  # pragma: no cover - depends on external validation errors
            raise GoogleTokenValidationError("Invalid Google id_token.") from exc

        email = payload.get("email")
        subject = payload.get("sub")
        if not email or not subject:
            raise GoogleTokenValidationError("Google id_token missing required claims.")

        email_verified_raw = payload.get("email_verified", False)
        email_verified = bool(email_verified_raw)
        if isinstance(email_verified_raw, str):
            email_verified = email_verified_raw.lower() == "true"

        name = payload.get("name") if isinstance(payload.get("name"), str) else None
        return GoogleIdentityInfo(
            subject=str(subject),
            email=str(email),
            email_verified=email_verified,
            name=name,
        )


def id_token_verify(*, token: str, audience: str) -> dict:
    request = requests.Request()
    return id_token.verify_oauth2_token(token, request, audience)
