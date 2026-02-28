from __future__ import annotations

from uuid import uuid4

from app.application.dto.auth import RegisterUserInput, RegisterUserOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.password_hasher_port import PasswordHasherPort
from app.domain.exceptions import EmailAlreadyExistsError

from .auth_common import build_auth_user_output, normalize_email, utcnow


class RegisterUserUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        password_hasher: PasswordHasherPort,
    ):
        self._auth_port = auth_port
        self._password_hasher = password_hasher

    def execute(self, command: RegisterUserInput) -> RegisterUserOutput:
        name = command.name.strip()
        email = normalize_email(command.email)
        password = command.password

        if not name:
            raise ValueError("name is required.")
        if not email:
            raise ValueError("email is required.")
        if len(password) < 8:
            raise ValueError("password must have at least 8 characters.")

        password_hash = self._password_hasher.hash(password)

        def _tx(auth_port: AuthPort) -> RegisterUserOutput:
            if auth_port.get_user_by_email(email=email) is not None:
                raise EmailAlreadyExistsError("Email already in use.")

            now = utcnow()
            user = auth_port.create_user(
                user_id=str(uuid4()),
                name=name,
                email=email,
                email_verified=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            auth_port.create_identity(
                identity_id=str(uuid4()),
                user_id=user.id,
                provider="local",
                provider_subject=None,
                password_hash=password_hash,
                created_at=now,
            )
            return RegisterUserOutput(user=build_auth_user_output(user))

        return self._auth_port.execute_in_transaction(_tx)
