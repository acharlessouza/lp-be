from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.api.deps import require_feature
from app.application.dto.entitlements import UserEntitlementsOutput
from app.domain.entities.user import User


class FakeEntitlementsUseCaseDenied:
    def execute(self, *, user_id: str) -> UserEntitlementsOutput:
        _ = user_id
        return UserEntitlementsOutput(
            user_id="user-1",
            plan_code="free",
            boolean_features={"charts_advanced": False},
            limits={"api_calls": 100},
        )


class FakeEntitlementsUseCaseAllowed:
    def execute(self, *, user_id: str) -> UserEntitlementsOutput:
        _ = user_id
        return UserEntitlementsOutput(
            user_id="user-1",
            plan_code="pro",
            boolean_features={"charts_advanced": True},
            limits={"api_calls": 10000},
        )


def _fake_user() -> User:
    return User(
        id="user-1",
        name="Alice",
        email="alice@example.com",
        email_verified=True,
        is_active=True,
        stripe_customer_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_require_feature_blocks_when_feature_missing():
    dependency = require_feature("charts_advanced")

    with pytest.raises(HTTPException) as exc_info:
        dependency(
            user=_fake_user(),
            entitlements_use_case=FakeEntitlementsUseCaseDenied(),
        )

    assert exc_info.value.status_code == 403


def test_require_feature_allows_when_feature_enabled():
    dependency = require_feature("charts_advanced")

    user = dependency(
        user=_fake_user(),
        entitlements_use_case=FakeEntitlementsUseCaseAllowed(),
    )

    assert user.id == "user-1"
