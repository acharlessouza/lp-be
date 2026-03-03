from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from app.application.dto.password_reset import ForgotPasswordInput, ForgotPasswordOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.email_sender_port import EmailSenderPort
from app.application.ports.token_port import TokenPort

from .auth_common import normalize_email, utcnow


GENERIC_FORGOT_MESSAGE = "If the email exists, we sent instructions."


class ForgotPasswordUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        token_port: TokenPort,
        email_sender: EmailSenderPort,
        frontend_base_url: str,
        token_ttl_minutes: int = 30,
        max_requests_per_hour: int = 3,
    ):
        self._auth_port = auth_port
        self._token_port = token_port
        self._email_sender = email_sender
        self._frontend_base_url = frontend_base_url.rstrip("/")
        self._token_ttl_minutes = token_ttl_minutes
        self._max_requests_per_hour = max_requests_per_hour

    def execute(self, command: ForgotPasswordInput) -> ForgotPasswordOutput:
        email = normalize_email(command.email)
        user = self._auth_port.get_user_by_email(email=email)
        if user is None:
            return ForgotPasswordOutput(message=GENERIC_FORGOT_MESSAGE)

        now = utcnow()
        requests_last_hour = self._auth_port.count_recent_password_reset_requests(
            user_id=user.id,
            since=now - timedelta(hours=1),
        )
        if requests_last_hour >= self._max_requests_per_hour:
            return ForgotPasswordOutput(message=GENERIC_FORGOT_MESSAGE)

        raw_token = self._token_port.generate_refresh_token()
        token_hash = self._token_port.hash_refresh_token(refresh_token=raw_token)
        expires_at = now + timedelta(minutes=self._token_ttl_minutes)

        def _tx(auth_port: AuthPort) -> None:
            auth_port.invalidate_password_reset_tokens_for_user(user_id=user.id, used_at=now)
            auth_port.create_password_reset_token(
                token_id=str(uuid4()),
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                used_at=None,
                created_at=now,
                requested_ip=command.ip,
                user_agent=command.user_agent,
            )

        self._auth_port.execute_in_transaction(_tx)

        reset_link = f"{self._frontend_base_url}/reset-password?token={raw_token}"
        self._email_sender.send_password_reset_email(to_email=user.email, reset_link=reset_link)
        return ForgotPasswordOutput(message=GENERIC_FORGOT_MESSAGE)
