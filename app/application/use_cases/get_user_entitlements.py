from __future__ import annotations

from app.application.dto.entitlements import UserEntitlementsOutput
from app.application.ports.entitlements_port import EntitlementsPort
from app.domain.exceptions import PlanNotFoundError
from app.domain.services.entitlements import build_user_entitlements


class GetUserEntitlementsUseCase:
    def __init__(self, *, entitlements_port: EntitlementsPort):
        self._entitlements_port = entitlements_port

    def execute(self, *, user_id: str) -> UserEntitlementsOutput:
        subscription = self._entitlements_port.get_effective_subscription_for_user(user_id=user_id)

        if subscription is None:
            plan = self._entitlements_port.get_plan_by_code(code="free")
            if plan is None:
                raise PlanNotFoundError("Default plan 'free' not found.")
        else:
            plan_price = self._entitlements_port.get_plan_price_by_id(plan_price_id=subscription.plan_price_id)
            if plan_price is None:
                raise PlanNotFoundError("Plan price from active subscription was not found.")
            plan = self._entitlements_port.get_plan_by_id(plan_id=plan_price.plan_id)
            if plan is None:
                raise PlanNotFoundError("Plan from active subscription was not found.")

        grants = self._entitlements_port.list_plan_feature_grants(plan_id=plan.id)
        entitlements = build_user_entitlements(user_id=user_id, plan_code=plan.code, grants=grants)

        return UserEntitlementsOutput(
            user_id=entitlements.user_id,
            plan_code=entitlements.plan_code,
            boolean_features=entitlements.boolean_features,
            limits=entitlements.limits,
        )
