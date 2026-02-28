from __future__ import annotations

from app.application.dto.me import MeOutput
from app.application.use_cases.get_user_entitlements import GetUserEntitlementsUseCase
from app.domain.entities.user import User


class GetMeUseCase:
    def __init__(self, *, get_user_entitlements_use_case: GetUserEntitlementsUseCase):
        self._get_user_entitlements_use_case = get_user_entitlements_use_case

    def execute(self, *, user: User) -> MeOutput:
        entitlements = self._get_user_entitlements_use_case.execute(user_id=user.id)
        return MeOutput(
            user_id=user.id,
            name=user.name,
            email=user.email,
            plan_code=entitlements.plan_code,
            boolean_features=entitlements.boolean_features,
            limits=entitlements.limits,
        )
