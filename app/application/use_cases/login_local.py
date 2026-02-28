from __future__ import annotations

from app.application.dto.auth import AuthTokensOutput, LoginLocalInput
from app.application.ports.auth_port import AuthPort
from app.application.ports.password_hasher_port import PasswordHasherPort
from app.application.ports.token_port import TokenPort
from app.domain.exceptions import InvalidCredentialsError, UserInactiveError

from .auth_common import issue_tokens, normalize_email


class LoginLocalUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        password_hasher: PasswordHasherPort,
        token_port: TokenPort,
    ):
        self._auth_port = auth_port
        self._password_hasher = password_hasher
        self._token_port = token_port

    def execute(self, command: LoginLocalInput) -> AuthTokensOutput:
        email = normalize_email(command.email)
        result = self._auth_port.get_local_identity_by_email(email=email)
        if result is None:
            raise InvalidCredentialsError("Invalid credentials.")

        user, identity = result
        if not identity.password_hash:
            raise InvalidCredentialsError("Invalid credentials.")

        if not self._password_hasher.verify(command.password, identity.password_hash):
            raise InvalidCredentialsError("Invalid credentials.")

        if not user.is_active:
            raise UserInactiveError("User is inactive.")

        return issue_tokens(
            user=user,
            auth_port=self._auth_port,
            token_port=self._token_port,
            user_agent=command.user_agent,
            ip=command.ip,
        )
