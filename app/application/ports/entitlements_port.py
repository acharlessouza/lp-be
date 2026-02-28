from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities.feature import PlanFeatureGrant
from app.domain.entities.plan import Plan, PlanPrice
from app.domain.entities.subscription import Subscription


class EntitlementsPort(Protocol):
    def get_plan_by_code(self, *, code: str) -> Plan | None:
        ...

    def get_plan_by_id(self, *, plan_id: str) -> Plan | None:
        ...

    def get_plan_price_by_id(self, *, plan_price_id: str) -> PlanPrice | None:
        ...

    def get_plan_price_by_external_price_id(self, *, external_price_id: str) -> PlanPrice | None:
        ...

    def list_plan_feature_grants(self, *, plan_id: str) -> list[PlanFeatureGrant]:
        ...

    def get_effective_subscription_for_user(self, *, user_id: str) -> Subscription | None:
        ...

    def upsert_subscription_by_external_id(
        self,
        *,
        subscription_id: str,
        user_id: str,
        plan_price_id: str,
        status: str,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
        cancel_at_period_end: bool,
        canceled_at: datetime | None,
        now: datetime,
    ) -> Subscription:
        ...

    def cancel_subscription_by_external_id(
        self,
        *,
        subscription_id: str,
        status: str,
        canceled_at: datetime | None,
        now: datetime,
    ) -> None:
        ...
