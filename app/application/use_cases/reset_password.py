from __future__ import annotations

from uuid import uuid4

from app.application.dto.password_reset import ResetPasswordInput, ResetPasswordOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.password_hasher_port import PasswordHasherPort
from app.application.ports.token_port import TokenPort
from app.domain.exceptions import PasswordResetTokenInvalidError

from .auth_common import utcnow


class ResetPasswordUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        token_port: TokenPort,
        password_hasher: PasswordHasherPort,
    ):
        self._auth_port = auth_port
        self._token_port = token_port
        self._password_hasher = password_hasher

    def execute(self, command: ResetPasswordInput) -> ResetPasswordOutput:
        token = command.token.strip()
        new_password = command.new_password
        if not token:
            raise PasswordResetTokenInvalidError("Invalid reset token.")
        if len(new_password) < 8:
            raise ValueError("new_password must have at least 8 characters.")

        now = utcnow()
        token_hash = self._token_port.hash_refresh_token(refresh_token=token)
        password_reset_token = self._auth_port.get_password_reset_token_by_hash(token_hash=token_hash)
        if password_reset_token is None:
            raise PasswordResetTokenInvalidError("Invalid reset token.")
        if password_reset_token.used_at is not None:
            raise PasswordResetTokenInvalidError("Reset token already used.")
        if password_reset_token.expires_at <= now:
            raise PasswordResetTokenInvalidError("Reset token expired.")

        user = self._auth_port.get_user_by_id(user_id=password_reset_token.user_id)
        if user is None:
            raise PasswordResetTokenInvalidError("Invalid reset token.")

        password_hash = self._password_hasher.hash(new_password)

        def _tx(auth_port: AuthPort) -> None:
            auth_port.mark_password_reset_token_used(token_id=password_reset_token.id, used_at=now)

            local_identity = auth_port.get_identity_for_user_provider(
                user_id=user.id,
                provider="local",
            )
            if local_identity is None:
                auth_port.create_identity(
                    identity_id=str(uuid4()),
                    user_id=user.id,
                    provider="local",
                    provider_subject=None,
                    password_hash=password_hash,
                    created_at=now,
                )
            else:
                auth_port.update_identity_password_hash(
                    identity_id=local_identity.id,
                    password_hash=password_hash,
                )

            auth_port.revoke_sessions_for_user(user_id=user.id, revoked_at=now)

        self._auth_port.execute_in_transaction(_tx)
        return ResetPasswordOutput(message="Password updated")
