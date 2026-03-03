from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import (
    get_forgot_password_use_case,
    get_refresh_session_use_case,
    get_reset_password_use_case,
)
from app.api.routers.auth import REFRESH_COOKIE_NAME, router as auth_router
from app.application.dto.auth import AuthTokensOutput, AuthUserOutput
from app.application.dto.password_reset import ForgotPasswordOutput, ResetPasswordOutput
from app.domain.exceptions import PasswordResetTokenInvalidError, RefreshSessionInvalidError


class FakeForgotPasswordUseCase:
    def execute(self, _command):
        return ForgotPasswordOutput(message="If the email exists, we sent instructions.")


class FakeResetPasswordUseCaseInvalid:
    def execute(self, _command):
        raise PasswordResetTokenInvalidError("Invalid reset token.")


class FakeRefreshUseCaseInvalid:
    def execute(self, _command):
        raise RefreshSessionInvalidError("Invalid refresh session.")


class FakeRefreshUseCaseValid:
    def execute(self, _command):
        now = datetime.now(timezone.utc)
        return AuthTokensOutput(
            user=AuthUserOutput(
                id="u1",
                name="User",
                email="user@example.com",
                email_verified=True,
                is_active=True,
            ),
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            access_expires_at=now + timedelta(minutes=15),
            refresh_expires_at=now + timedelta(days=30),
        )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)
    return app


def test_forgot_password_endpoint_always_200():
    app = _build_app()
    app.dependency_overrides[get_forgot_password_use_case] = lambda: FakeForgotPasswordUseCase()

    client = TestClient(app)
    response = client.post("/v1/auth/password/forgot", json={"email": "missing@example.com"})

    assert response.status_code == 200
    assert response.json()["message"] == "If the email exists, we sent instructions."


def test_password_reset_endpoint_invalid_token_returns_400():
    app = _build_app()
    app.dependency_overrides[get_reset_password_use_case] = lambda: FakeResetPasswordUseCaseInvalid()

    client = TestClient(app)
    response = client.post(
        "/v1/auth/password/reset",
        json={"token": "invalid", "new_password": "new-password-123"},
    )

    assert response.status_code == 400


def test_refresh_endpoint_invalid_token_returns_401():
    app = _build_app()
    app.dependency_overrides[get_refresh_session_use_case] = lambda: FakeRefreshUseCaseInvalid()

    client = TestClient(app)
    client.cookies.set(REFRESH_COOKIE_NAME, "invalid")
    response = client.post("/v1/auth/refresh")

    assert response.status_code == 401


def test_refresh_endpoint_valid_sets_rotated_cookie_and_returns_access_payload():
    app = _build_app()
    app.dependency_overrides[get_refresh_session_use_case] = lambda: FakeRefreshUseCaseValid()

    client = TestClient(app)
    client.cookies.set(REFRESH_COOKIE_NAME, "old-refresh-token")
    response = client.post("/v1/auth/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "new-access-token"
    assert payload["token_type"] == "bearer"
    assert "refresh_expires_at" in payload
    assert REFRESH_COOKIE_NAME in response.headers.get("set-cookie", "")
