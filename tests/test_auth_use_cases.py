from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from app.application.dto.auth import LoginGoogleInput, LoginLocalInput, RegisterUserInput
from app.application.dto.auth import GoogleIdentityInfo
from app.application.use_cases.login_google import LoginGoogleUseCase
from app.application.use_cases.login_local import LoginLocalUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.entities.user import AuthIdentity, AuthSession, User


class FakeAuthPort:
    def __init__(self):
        self.users: dict[str, User] = {}
        self.identities: dict[str, AuthIdentity] = {}
        self.sessions: dict[str, AuthSession] = {}

    def get_user_by_id(self, *, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_user_by_email(self, *, email: str) -> User | None:
        email_l = email.lower()
        for user in self.users.values():
            if user.email.lower() == email_l:
                return user
        return None

    def get_user_by_stripe_customer_id(self, *, stripe_customer_id: str) -> User | None:
        for user in self.users.values():
            if user.stripe_customer_id == stripe_customer_id:
                return user
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

    def get_identity_by_provider_subject(self, *, provider: str, provider_subject: str) -> AuthIdentity | None:
        for identity in self.identities.values():
            if identity.provider == provider and identity.provider_subject == provider_subject:
                return identity
        return None

    def update_identity_provider_subject(self, *, identity_id: str, provider_subject: str) -> None:
        identity = self.identities[identity_id]
        self.identities[identity_id] = replace(identity, provider_subject=provider_subject)

    def get_local_identity_by_email(self, *, email: str) -> tuple[User, AuthIdentity] | None:
        user = self.get_user_by_email(email=email)
        if user is None:
            return None
        for identity in self.identities.values():
            if identity.user_id == user.id and identity.provider == "local":
                return user, identity
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

    def get_session_by_refresh_token_hash(self, *, refresh_token_hash: str) -> AuthSession | None:
        for session in self.sessions.values():
            if session.refresh_token_hash == refresh_token_hash:
                return session
        return None

    def revoke_session(self, *, session_id: str, revoked_at: datetime) -> None:
        session = self.sessions[session_id]
        self.sessions[session_id] = replace(session, revoked_at=revoked_at)


class FakePasswordHasher:
    def hash(self, plain_password: str) -> str:
        return f"hashed::{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{plain_password}"


class FakeTokenPort:
    def create_access_token(self, *, user_id: str, now: datetime) -> tuple[str, datetime]:
        return f"access-{user_id}", now + timedelta(minutes=15)

    def decode_access_token(self, *, token: str):
        _ = token
        raise NotImplementedError

    def generate_refresh_token(self) -> str:
        return "refresh-token"

    def hash_refresh_token(self, *, refresh_token: str) -> str:
        return f"hash::{refresh_token}"

    def refresh_token_expires_at(self, *, now: datetime) -> datetime:
        return now + timedelta(days=30)


class FakeGoogleOauthPort:
    def verify_id_token(self, *, id_token: str) -> GoogleIdentityInfo:
        assert id_token == "token-google"
        return GoogleIdentityInfo(
            subject="google-sub-1",
            email="user@example.com",
            email_verified=True,
            name="Google User",
        )


def test_register_user_creates_local_identity():
    auth_port = FakeAuthPort()
    use_case = RegisterUserUseCase(auth_port=auth_port, password_hasher=FakePasswordHasher())

    output = use_case.execute(
        RegisterUserInput(
            name="User",
            email="user@example.com",
            password="12345678",
        )
    )

    assert output.user.email == "user@example.com"
    local_identity = auth_port.get_identity_for_user_provider(user_id=output.user.id, provider="local")
    assert local_identity is not None
    assert local_identity.password_hash == "hashed::12345678"


def test_login_local_returns_tokens_and_creates_session():
    auth_port = FakeAuthPort()
    register_use_case = RegisterUserUseCase(auth_port=auth_port, password_hasher=FakePasswordHasher())
    register_output = register_use_case.execute(
        RegisterUserInput(name="User", email="user@example.com", password="12345678")
    )

    login_use_case = LoginLocalUseCase(
        auth_port=auth_port,
        password_hasher=FakePasswordHasher(),
        token_port=FakeTokenPort(),
    )
    output = login_use_case.execute(
        LoginLocalInput(
            email="user@example.com",
            password="12345678",
            user_agent="pytest",
            ip="127.0.0.1",
        )
    )

    assert output.user.id == register_output.user.id
    assert output.access_token.startswith("access-")
    assert output.refresh_token == "refresh-token"
    assert len(auth_port.sessions) == 1


def test_login_google_links_existing_user_by_email_and_creates_google_identity():
    auth_port = FakeAuthPort()
    register_use_case = RegisterUserUseCase(auth_port=auth_port, password_hasher=FakePasswordHasher())
    register_output = register_use_case.execute(
        RegisterUserInput(name="User", email="user@example.com", password="12345678")
    )

    use_case = LoginGoogleUseCase(
        auth_port=auth_port,
        google_oauth_port=FakeGoogleOauthPort(),
        token_port=FakeTokenPort(),
    )

    output = use_case.execute(
        LoginGoogleInput(
            id_token="token-google",
            user_agent="pytest",
            ip="127.0.0.1",
        )
    )

    assert output.user.id == register_output.user.id
    google_identity = auth_port.get_identity_for_user_provider(
        user_id=register_output.user.id,
        provider="google",
    )
    assert google_identity is not None
    assert google_identity.provider_subject == "google-sub-1"
