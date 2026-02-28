from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol, TypeVar

from app.domain.entities.user import AuthIdentity, AuthProvider, AuthSession, User


TAuthResult = TypeVar("TAuthResult")


class AuthPort(Protocol):
    def execute_in_transaction(self, fn: Callable[[AuthPort], TAuthResult]) -> TAuthResult:
        ...

    def get_user_by_id(self, *, user_id: str) -> User | None:
        ...

    def get_user_by_email(self, *, email: str) -> User | None:
        ...

    def get_user_by_stripe_customer_id(self, *, stripe_customer_id: str) -> User | None:
        ...

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
        ...

    def update_user_email_verified(self, *, user_id: str, email_verified: bool) -> None:
        ...

    def update_user_stripe_customer_id(self, *, user_id: str, stripe_customer_id: str) -> None:
        ...

    def create_identity(
        self,
        *,
        identity_id: str,
        user_id: str,
        provider: AuthProvider,
        provider_subject: str | None,
        password_hash: str | None,
        created_at: datetime,
    ) -> AuthIdentity:
        ...

    def get_identity_for_user_provider(
        self,
        *,
        user_id: str,
        provider: AuthProvider,
    ) -> AuthIdentity | None:
        ...

    def get_identity_by_provider_subject(
        self,
        *,
        provider: AuthProvider,
        provider_subject: str,
    ) -> AuthIdentity | None:
        ...

    def update_identity_provider_subject(self, *, identity_id: str, provider_subject: str) -> None:
        ...

    def update_identity_password_hash(self, *, identity_id: str, password_hash: str) -> None:
        ...

    def get_local_identity_by_email(self, *, email: str) -> tuple[User, AuthIdentity] | None:
        ...

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
        ...

    def get_session_by_refresh_token_hash(self, *, refresh_token_hash: str) -> AuthSession | None:
        ...

    def revoke_session(self, *, session_id: str, revoked_at: datetime) -> None:
        ...
