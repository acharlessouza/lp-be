from __future__ import annotations

from datetime import datetime, timezone

from app.application.dto.entitlements import UserEntitlementsOutput
from app.application.use_cases.get_me import GetMeUseCase
from app.domain.entities.user import User


class FakeGetUserEntitlementsUseCase:
    def execute(self, *, user_id: str) -> UserEntitlementsOutput:
        return UserEntitlementsOutput(
            user_id=user_id,
            plan_code="free",
            boolean_features={"charts_advanced": False, "export_csv": False},
            limits={"api_calls": 100},
        )


def test_get_me_returns_user_and_features():
    fake_user = User(
        id="user-1",
        name="Alice",
        email="alice@example.com",
        email_verified=True,
        is_active=True,
        stripe_customer_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    use_case = GetMeUseCase(get_user_entitlements_use_case=FakeGetUserEntitlementsUseCase())

    output = use_case.execute(user=fake_user)

    assert output.user_id == "user-1"
    assert output.plan_code == "free"
    assert output.boolean_features["charts_advanced"] is False
    assert output.limits["api_calls"] == 100
