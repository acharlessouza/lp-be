from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from app.application.dto.password_reset import ForgotPasswordInput, ResetPasswordInput
from app.application.use_cases.forgot_password import ForgotPasswordUseCase
from app.application.use_cases.reset_password import ResetPasswordUseCase
from app.domain.entities.password_reset import PasswordResetToken
from app.domain.entities.user import AuthIdentity, AuthSession, User
from app.domain.exceptions import PasswordResetTokenInvalidError


class FakeAuthPort:
    def __init__(self):
        self.users: dict[str, User] = {}
        self.identities: dict[str, AuthIdentity] = {}
        self.sessions: dict[str, AuthSession] = {}
        self.reset_tokens: dict[str, PasswordResetToken] = {}

    def execute_in_transaction(self, fn):
        return fn(self)

    def get_user_by_id(self, *, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_user_by_email(self, *, email: str) -> User | None:
        email_l = email.lower()
        for user in self.users.values():
            if user.email.lower() == email_l:
                return user
        return None

    def get_user_by_stripe_customer_id(self, *, stripe_customer_id: str):
        _ = stripe_customer_id
        return None

    def create_user(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        email_verified: bool,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> User:
        user = User(
            id=user_id,
            name=name,
            email=email,
            email_verified=email_verified,
            is_active=is_active,
            stripe_customer_id=None,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.users[user.id] = user
        return user

    def update_user_email_verified(self, *, user_id: str, email_verified: bool) -> None:
        user = self.users[user_id]
        self.users[user_id] = replace(user, email_verified=email_verified)

    def update_user_stripe_customer_id(self, *, user_id: str, stripe_customer_id: str) -> None:
        user = self.users[user_id]
        self.users[user_id] = replace(user, stripe_customer_id=stripe_customer_id)

    def create_identity(
        self,
        *,
        identity_id: str,
        user_id: str,
        provider: str,
        provider_subject: str | None,
        password_hash: str | None,
        created_at: datetime,
    ) -> AuthIdentity:
        identity = AuthIdentity(
            id=identity_id,
            user_id=user_id,
            provider=provider,
            provider_subject=provider_subject,
            password_hash=password_hash,
            created_at=created_at,
        )
        self.identities[identity.id] = identity
        return identity

    def get_identity_for_user_provider(self, *, user_id: str, provider: str) -> AuthIdentity | None:
        for identity in self.identities.values():
            if identity.user_id == user_id and identity.provider == provider:
                return identity
        return None

    def get_identity_by_provider_subject(self, *, provider: str, provider_subject: str):
        _ = (provider, provider_subject)
        return None

    def update_identity_provider_subject(self, *, identity_id: str, provider_subject: str) -> None:
        identity = self.identities[identity_id]
        self.identities[identity_id] = replace(identity, provider_subject=provider_subject)

    def update_identity_password_hash(self, *, identity_id: str, password_hash: str) -> None:
        identity = self.identities[identity_id]
        self.identities[identity_id] = replace(identity, password_hash=password_hash)

    def get_local_identity_by_email(self, *, email: str):
        _ = email
        return None

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        revoked_at: datetime | None,
        user_agent: str | None,
        ip: str | None,
        created_at: datetime,
    ) -> AuthSession:
        session = AuthSession(
            id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            revoked_at=revoked_at,
            user_agent=user_agent,
            ip=ip,
            created_at=created_at,
        )
        self.sessions[session.id] = session
        return session

    def get_session_by_refresh_token_hash(self, *, refresh_token_hash: str):
        _ = refresh_token_hash
        return None

    def revoke_session(self, *, session_id: str, revoked_at: datetime) -> None:
        session = self.sessions[session_id]
        self.sessions[session_id] = replace(session, revoked_at=revoked_at)

    def revoke_sessions_for_user(self, *, user_id: str, revoked_at: datetime) -> None:
        for session_id, session in list(self.sessions.items()):
            if session.user_id == user_id and session.revoked_at is None:
                self.sessions[session_id] = replace(session, revoked_at=revoked_at)

    def create_password_reset_token(
        self,
        *,
        token_id: str,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        used_at: datetime | None,
        created_at: datetime,
        requested_ip: str | None,
        user_agent: str | None,
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            id=token_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=used_at,
            created_at=created_at,
            requested_ip=requested_ip,
            user_agent=user_agent,
        )
        self.reset_tokens[token.id] = token
        return token

    def get_password_reset_token_by_hash(self, *, token_hash: str) -> PasswordResetToken | None:
        for token in self.reset_tokens.values():
            if token.token_hash == token_hash:
                return token
        return None

    def mark_password_reset_token_used(self, *, token_id: str, used_at: datetime) -> None:
        token = self.reset_tokens[token_id]
        self.reset_tokens[token_id] = replace(token, used_at=used_at)

    def invalidate_password_reset_tokens_for_user(self, *, user_id: str, used_at: datetime) -> None:
        for token_id, token in list(self.reset_tokens.items()):
            if token.user_id == user_id and token.used_at is None:
                self.reset_tokens[token_id] = replace(token, used_at=used_at)

    def count_recent_password_reset_requests(self, *, user_id: str, since: datetime) -> int:
        return sum(1 for token in self.reset_tokens.values() if token.user_id == user_id and token.created_at >= since)


class FakeTokenPort:
    def __init__(self):
        self._seq = 0

    def create_access_token(self, *, user_id: str, now: datetime):
        _ = (user_id, now)
        raise NotImplementedError

    def decode_access_token(self, *, token: str):
        _ = token
        raise NotImplementedError

    def generate_refresh_token(self) -> str:
        self._seq += 1
        return f"reset-token-{self._seq}"

    def hash_refresh_token(self, *, refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    def refresh_token_expires_at(self, *, now: datetime):
        _ = now
        raise NotImplementedError


class FakePasswordHasher:
    def hash(self, plain_password: str) -> str:
        return f"hash::{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hash::{plain_password}"

    def verify_and_update(self, plain_password: str, password_hash: str):
        return self.verify(plain_password, password_hash), None


class FakeEmailSender:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send_password_reset_email(self, *, to_email: str, reset_link: str) -> None:
        self.sent.append((to_email, reset_link))


def _make_user(auth_port: FakeAuthPort, user_id: str = "u1", email: str = "user@example.com") -> User:
    now = datetime.now(timezone.utc)
    return auth_port.create_user(
        user_id=user_id,
        name="User",
        email=email,
        email_verified=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_forgot_password_always_returns_success_for_non_existing_email():
    auth_port = FakeAuthPort()
    use_case = ForgotPasswordUseCase(
        auth_port=auth_port,
        token_port=FakeTokenPort(),
        email_sender=FakeEmailSender(),
        frontend_base_url="http://localhost:3000",
    )

    output = use_case.execute(
        ForgotPasswordInput(email="missing@example.com", user_agent="pytest", ip="127.0.0.1")
    )

    assert output.message == "If the email exists, we sent instructions."


def test_reset_password_with_valid_token_updates_password_and_marks_used():
    auth_port = FakeAuthPort()
    user = _make_user(auth_port)
    identity = auth_port.create_identity(
        identity_id="i1",
        user_id=user.id,
        provider="local",
        provider_subject=None,
        password_hash="hash::oldpass",
        created_at=datetime.now(timezone.utc),
    )
    token_port = FakeTokenPort()
    raw_token = token_port.generate_refresh_token()
    token_hash = token_port.hash_refresh_token(refresh_token=raw_token)
    auth_port.create_password_reset_token(
        token_id="t1",
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used_at=None,
        created_at=datetime.now(timezone.utc),
        requested_ip=None,
        user_agent=None,
    )

    use_case = ResetPasswordUseCase(
        auth_port=auth_port,
        token_port=token_port,
        password_hasher=FakePasswordHasher(),
    )

    output = use_case.execute(ResetPasswordInput(token=raw_token, new_password="new-password-123"))

    assert output.message == "Password updated"
    updated_identity = auth_port.identities[identity.id]
    assert updated_identity.password_hash == "hash::new-password-123"
    assert auth_port.reset_tokens["t1"].used_at is not None


def test_reset_password_invalid_or_expired_or_used_token_returns_400_error():
    auth_port = FakeAuthPort()
    user = _make_user(auth_port)
    token_port = FakeTokenPort()

    valid_raw = token_port.generate_refresh_token()
    valid_hash = token_port.hash_refresh_token(refresh_token=valid_raw)
    auth_port.create_password_reset_token(
        token_id="used",
        user_id=user.id,
        token_hash=valid_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        used_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        requested_ip=None,
        user_agent=None,
    )

    expired_raw = token_port.generate_refresh_token()
    expired_hash = token_port.hash_refresh_token(refresh_token=expired_raw)
    auth_port.create_password_reset_token(
        token_id="expired",
        user_id=user.id,
        token_hash=expired_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        used_at=None,
        created_at=datetime.now(timezone.utc),
        requested_ip=None,
        user_agent=None,
    )

    use_case = ResetPasswordUseCase(
        auth_port=auth_port,
        token_port=token_port,
        password_hasher=FakePasswordHasher(),
    )

    with pytest.raises(PasswordResetTokenInvalidError):
        use_case.execute(ResetPasswordInput(token="totally-invalid", new_password="new-password-123"))

    with pytest.raises(PasswordResetTokenInvalidError):
        use_case.execute(ResetPasswordInput(token=expired_raw, new_password="new-password-123"))

    with pytest.raises(PasswordResetTokenInvalidError):
        use_case.execute(ResetPasswordInput(token=valid_raw, new_password="new-password-123"))
