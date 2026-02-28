from __future__ import annotations

from uuid import uuid4

from app.application.dto.auth import AuthTokensOutput, LoginGoogleInput
from app.application.ports.auth_port import AuthPort
from app.application.ports.google_oauth_port import GoogleOauthPort
from app.application.ports.token_port import TokenPort
from app.domain.exceptions import UserInactiveError

from .auth_common import issue_tokens, normalize_email, utcnow


class LoginGoogleUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        google_oauth_port: GoogleOauthPort,
        token_port: TokenPort,
    ):
        self._auth_port = auth_port
        self._google_oauth_port = google_oauth_port
        self._token_port = token_port

    def execute(self, command: LoginGoogleInput) -> AuthTokensOutput:
        google_identity = self._google_oauth_port.verify_id_token(id_token=command.id_token)
        email = normalize_email(google_identity.email)
        now = utcnow()

        identity = self._auth_port.get_identity_by_provider_subject(
            provider="google",
            provider_subject=google_identity.subject,
        )
        if identity is not None:
            user = self._auth_port.get_user_by_id(user_id=identity.user_id)
            if user is None:
                raise ValueError("User linked to Google identity was not found.")
        else:
            user = self._auth_port.get_user_by_email(email=email)
            if user is None:
                user_name = google_identity.name.strip() if google_identity.name else email.split("@")[0]
                user = self._auth_port.create_user(
                    user_id=str(uuid4()),
                    name=user_name,
                    email=email,
                    email_verified=google_identity.email_verified,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            google_identity_existing = self._auth_port.get_identity_for_user_provider(
                user_id=user.id,
                provider="google",
            )
            if google_identity_existing is None:
                self._auth_port.create_identity(
                    identity_id=str(uuid4()),
                    user_id=user.id,
                    provider="google",
                    provider_subject=google_identity.subject,
                    password_hash=None,
                    created_at=now,
                )
            elif google_identity_existing.provider_subject != google_identity.subject:
                self._auth_port.update_identity_provider_subject(
                    identity_id=google_identity_existing.id,
                    provider_subject=google_identity.subject,
                )

        if google_identity.email_verified and not user.email_verified:
            self._auth_port.update_user_email_verified(user_id=user.id, email_verified=True)
            user = self._auth_port.get_user_by_id(user_id=user.id) or user

        if not user.is_active:
            raise UserInactiveError("User is inactive.")

        return issue_tokens(
            user=user,
            auth_port=self._auth_port,
            token_port=self._token_port,
            user_agent=command.user_agent,
            ip=command.ip,
        )
