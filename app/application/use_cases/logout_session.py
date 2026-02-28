from __future__ import annotations

from app.application.dto.auth import LogoutInput
from app.application.ports.auth_port import AuthPort
from app.application.ports.token_port import TokenPort

from .auth_common import utcnow


class LogoutSessionUseCase:
    def __init__(self, *, auth_port: AuthPort, token_port: TokenPort):
        self._auth_port = auth_port
        self._token_port = token_port

    def execute(self, command: LogoutInput) -> None:
        token = command.refresh_token.strip()
        if not token:
            return
        refresh_hash = self._token_port.hash_refresh_token(refresh_token=token)
        session = self._auth_port.get_session_by_refresh_token_hash(refresh_token_hash=refresh_hash)
        if session is None or session.revoked_at is not None:
            return
        self._auth_port.revoke_session(session_id=session.id, revoked_at=utcnow())
