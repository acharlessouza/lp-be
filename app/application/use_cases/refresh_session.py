from __future__ import annotations

from app.application.dto.auth import AuthTokensOutput, RefreshSessionInput
from app.application.ports.auth_port import AuthPort
from app.application.ports.token_port import TokenPort
from app.domain.exceptions import RefreshSessionInvalidError, UserInactiveError

from .auth_common import issue_tokens, utcnow


class RefreshSessionUseCase:
    def __init__(self, *, auth_port: AuthPort, token_port: TokenPort):
        self._auth_port = auth_port
        self._token_port = token_port

    def execute(self, command: RefreshSessionInput) -> AuthTokensOutput:
        token = command.refresh_token.strip()
        if not token:
            raise RefreshSessionInvalidError("Missing refresh token.")

        now = utcnow()
        refresh_hash = self._token_port.hash_refresh_token(refresh_token=token)
        session = self._auth_port.get_session_by_refresh_token_hash(refresh_token_hash=refresh_hash)
        if session is None:
            raise RefreshSessionInvalidError("Invalid refresh session.")
        if session.revoked_at is not None:
            raise RefreshSessionInvalidError("Refresh session already revoked.")
        if session.expires_at <= now:
            raise RefreshSessionInvalidError("Refresh session expired.")

        user = self._auth_port.get_user_by_id(user_id=session.user_id)
        if user is None:
            raise RefreshSessionInvalidError("User not found for refresh session.")
        if not user.is_active:
            raise UserInactiveError("User is inactive.")

        self._auth_port.revoke_session(session_id=session.id, revoked_at=now)
        return issue_tokens(
            user=user,
            auth_port=self._auth_port,
            token_port=self._token_port,
            user_agent=command.user_agent,
            ip=command.ip,
        )
